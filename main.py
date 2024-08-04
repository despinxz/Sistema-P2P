import argparse
import numpy as np
import random
import socket
import sys
import threading

def read_file(name):
    """
    Função auxiliar para ler arquivos.

    :param name: Nome do arquivo.
    :return: Lista com as linhas do arquivo.
    """
    with open(name, 'r') as arq:
        lines = arq.readlines()

    return lines


def send_msg(msg_tbs, no_msg):
    """
    Função para enviar mensagens.

    :param msg_tbs: String contendo a mensagem a ser enviada.
    :param no_msg: String contendo o endereço do destinatário.
    """
    sock_dest = None
    try:
        host_msg, port_msg = no_msg.split(":")
        print(f'Encaminhando mensagem "{msg_tbs}" para {host_msg}:{port_msg}')

        sock_dest = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        sock_dest.connect((host_msg, int(port_msg)))
        sock_dest.send(msg_tbs.encode())

        ack_rcv = sock_dest.recv(4096).decode()
        if ack_rcv:
            print(f'    Envio feito com sucesso: "{msg_tbs}"')
        else:
            print(f'Erro no envio da mensagem: {msg_tbs}')

    except Exception as e:
        print(f'    Erro ao conectar!')
        ack_rcv = False

    finally:
        if sock_dest:
            sock_dest.close()

    global seqno
    seqno += 1
    return ack_rcv


def recv_msg(socket_rmt):
    """
    Lida com o recebimento de mensagens.

    :param socket_rmt: Socket do remetente.
    """
    msg_rcv = socket_rmt.recv(4096).decode()
    print(f"Mensagem recebida: \"{msg_rcv}\"")
    msg_list = msg_rcv.split()
    op = msg_list[3]

    # Envia ACK
    socket_rmt.send(f"{op}_OK".encode())
    socket_rmt.close()

    # Chama a função correspondente à operação da mensagem
    if op == "HELLO":
        hello(recv=True, msg=msg_list)
    elif op == "SEARCH":
        search(recv=True, msg=msg_list, mode=msg_list[4])
    elif op == "BYE":
        bye(recv=True, msg=msg_list)
    elif op == "VAL":
        val(msg=msg_list)


def user():
    """
    Função para o loop de inputs do usuário.

    :return:
    """
    menu = ("Escolha o comando:\n"
            "   [0] Listar vizinhos\n"
            "   [1] HELLO\n"
            "   [2] SEARCH (flooding)\n"
            "   [3] SEARCH (random walk)\n"
            "   [4] SEARCH (busca em profundidade)\n"
            "   [5] Estatisticas\n"
            "   [6] Alterar valor padrao de TTL\n"
            "   [9] Sair\n")

    while True:
        inp = input(menu)

        if inp == "0":
            listar_vizinhos()
        elif inp == "1":
            hello(send=True)
        elif inp == "2":
            search(send=True, mode="FL")
        elif inp == "3":
            search(send=True, mode="RW")
        elif inp == "4":
            search(send=True, mode="BP")
        elif inp == "5":
            stats()
        elif inp == "6":
            alt_ttl()
        elif inp == "9":
            bye(send=True)

            # Altera variável para encerrar loop de escuta de conexões
            global sock_online
            sock_online = False

            # Encerra loop de menu
            return


def listen():
    """
    Função para aceitar conexões.

    :return:
    """
    sock_host.listen()
    sock_host.settimeout(3)

    while sock_online:
        try:
            client, end = sock_host.accept()
            client_handler = threading.Thread(target=recv_msg, args=(client,))
            client_handler.start()

        except socket.timeout:
            continue


def listar_vizinhos():
    """
    Função para listar os vizinhos conhecidos.
    """
    print(f"Há {len(vizinhos)} vizinhos na tabela:")
    for i, vizinho in enumerate(vizinhos):
        host_viz, port_viz = vizinho.split(":")
        print(f'[{i}] {host_viz} {port_viz}')


def hello(send=False, recv=False, msg=None):
    """
    Função para lidar com mensagens da operação HELLO.

    :param send: Indica se a função é chamada pelo remetente.
    :param recv: Indica se a função é chamada pelo destinatário.
    :param msg: Lista com os argumentos da mensagem (caso a função tenha sido chamada pelo destinatário).
    """
    if send:
        print("Escolha o vizinho:")
        listar_vizinhos()

        viz = int(input())

        dest = vizinhos[viz]

        msg = f"{host}:{port} {seqno} 1 HELLO"

        # Envia a mensagem
        print(f"Tentando adicionar vizinho {dest}")
        ack = send_msg(msg, dest)

        return ack

    if recv and msg:
        # Armazena o campo ORIGIN da mensagem
        origin_msg = msg[0]

        # Verifica se o remetente está na tabela de vizinhos conhecidos
        if origin_msg in vizinhos:
            print(f'    Vizinho já está na tabela: {origin_msg}')
        else:
            print(f'    Adicionando vizinho na tabela: {origin_msg}')
            vizinhos.append(origin_msg)


def search(send=False, recv=False, msg=None, mode=None):
    global no_mae, viz_disp, viz_ativ
    if send:
        busca = input("Digite a chave a ser buscada: ")

        # Procura chave na tabela local
        if busca in cvs.keys():
            print("Valor na tabela local!")
            print(f"     chave: {busca} valor: {cvs[busca]}")

        # Se não achar, envia mensagem de busca para vizinhos
        else:
            msg = (f"{host}:{port} "  # origin
                   f"{seqno} "  # seqno
                   f"{ttl} "  # ttl
                   f"SEARCH "  # op
                   f"{mode} "  # mode
                   f"{port} "  # last_hop_port
                   f"{busca} "  # key
                   f"1")  # hop_count

            # Busca por FLOODING
            if mode == "FL":
                for viz in vizinhos:
                    send_msg(msg, viz)

            # Busca por RANDOM WALK
            elif mode == "RW":
                viz = random.choice(vizinhos)
                send_msg(msg, viz)

            # Busca por BUSCA EM PROFUNDIDADE
            elif mode == "BP":
                # Inicializa nó mãe, vizinho ativo e lista de vizinhos disponíveis
                no_mae = f"{host}:{port}"
                viz_disp = vizinhos.copy()
                viz_ativ = random.choice(viz_disp)

                # Remove vizinho ativo da lista de vizinhos disponíveis
                viz_disp.remove(viz_ativ)

                id_msg = f"{seqno}:{port}"
                msgs_vistas.append(id_msg)

                # Envia mensagem para vizinho ativo
                send_msg(msg, viz_ativ)

    if recv and msg:
        viz_ori = msg[0]  # endereço do vizinho de origem
        viz_rmt = f"{host}:{msg[5]}"  # endereço do vizinho remetente da mensagem

        id_msg = f"{msg[1]}:{msg[0].split(':')[1]}"  # id da mensagem (seqno:origin_port)

        seqno_msg = msg[1]
        ttl_msg = int(msg[2])
        mode_msg = msg[4]
        count_msgs[mode_msg] += 1

        busca_msg = msg[6]
        hop_count = int(msg[7])

        # Se a chave estiver na tabela local, retorna VAL
        if busca_msg in cvs.keys() and id_msg not in msgs_vistas:
            print('Chave encontrada!')

            msgs_vistas.append(id_msg)

            msg = (f"{host}:{port} "
                   f"{seqno} "
                   f"{ttl} "
                   f"VAL "
                   f"{mode_msg} "
                   f"{busca_msg} "
                   f"{cvs[busca_msg]} "
                   f"{hop_count}")

            send_msg(msg, viz_ori)

        else:
            hop_count += 1
            ttl_msg -= 1

            if ttl_msg == 0:
                print("TTL igual a zero, descartando mensagem")
                return

            msg = (f"{viz_ori} "
                   f"{seqno_msg} "
                   f"{ttl_msg} "
                   f"SEARCH "
                   f"{mode_msg} "
                   f"{port} "
                   f"{busca_msg} "
                   f"{hop_count}")

            # Busca por FLOODING
            if mode_msg == "FL":
                if id_msg in msgs_vistas:
                    print("Flooding: mensagem repetida!")
                    return

                msgs_vistas.append(id_msg)

                for viz in vizinhos:
                    if viz != viz_ori and viz != viz_rmt:
                        send_msg(msg, viz)

            # Busca por RANDOM WALK
            elif mode_msg == "RW":
                if ttl_msg == 0:
                    print("TTL igual a zero, descartando mensagem")
                    return

                if len(vizinhos) == 1 and vizinhos[0] == viz_rmt:
                    # Caso seja, envia a mensagem de volta para o remetente
                    send_msg(msg, viz_rmt)

                else:
                    # Caso não seja, envia para um novo vizinho aleatório que não seja o remetente
                    dest = random.choice([v for v in vizinhos if v != viz_rmt])

                    send_msg(msg, dest)

            # Busca por BUSCA EM PROFUNDIDADE
            elif mode_msg == "BP":

                if id_msg not in msgs_vistas:
                    no_mae = viz_rmt
                    viz_disp = vizinhos.copy()
                    viz_ativ = False
                    msgs_vistas.append(id_msg)

                if viz_rmt in viz_disp:
                    print(f'vizinho removido: {viz_rmt}')
                    viz_disp.remove(viz_rmt)

                if no_mae == f"{host}:{port}" and viz_ativ == viz_rmt and len(viz_disp) == 0:
                    print(f"BP: Não foi possível localizar a chave {busca_msg}")
                    return

                if viz_ativ and viz_ativ != viz_rmt:
                    print("BP: Ciclo detectado, devolvendo a mensagem...")
                    dest_busca = viz_rmt

                elif len(viz_disp) == 0:
                    print("BP: Nenhum vizinho encontrou a chave, retrocedendo...")
                    dest_busca = no_mae

                else:
                    dest_busca = random.choice(viz_disp)
                    viz_ativ = dest_busca
                    viz_disp.remove(dest_busca)

                send_msg(msg, dest_busca)

    return


def stats():
    """
    Função para exibir estatísticas.
    """
    print("Estatísticas")
    print(f"     Total de mensagens de flooding vistas: {count_msgs['FL']}\n"
          f"     Total de mensagens de random walk vistas: {count_msgs['RW']}\n"
          f"     Total de mensagens de busca em profundidade vistas: {count_msgs['BP']}\n"
          f"     Média de saltos até encontrar destino por flooding: {np.mean(fl_stats):.2f} (dp {np.std(fl_stats):.2f})\n"
          f"     Média de saltos até encontrar destino por random walk: {np.mean(rw_stats):.2f} (dp {np.std(rw_stats):.2f})\n"
          f"     Média de saltos até encontrar destino por busca em profundidade: {np.mean(bp_stats):.2f} (dp {np.std(bp_stats):.2f})\n")


def alt_ttl():
    """
    Função que altera TTL.
    """
    global ttl
    ttl = int(input("Digite novo valor de TTL"))


def bye(send=False, recv=False, msg=None):
    """
    Função para lidar com as mensagens da operação BYE.

    :param send: Indica se a função é chamada pelo remetente.
    :param recv: Indica se a função é chamada pelo destinatário.
    :param msg: Lista com os argumentos da mensagem (caso a função tenha sido chamada pelo destinatário).
    """
    if send:
        print("Você escolheu 9")
        print("Saindo...")

        msg = f"{host}:{port} {seqno} 1 BYE"

        for viz in vizinhos:
            send_msg(msg, viz)

    if recv and msg:
        origin_msg = msg[0]
        print(f'    Removendo vizinho da tabela: {origin_msg}')
        vizinhos.remove(origin_msg)


def val(msg):
    """
    Função que trata mensagens de VAL.

    :param msg: Mensagem recebida com operação VAL.
    """
    id_msg = f"{msg[1]}:{msg[0].split(':')[1]}"
    mode_val = msg[4]
    key_val = msg[5]
    value_val = msg[6]
    hop_count = int(msg[7])

    if id_msg not in msgs_vistas:  # Verifica se mensagem já foi vista
        print("     Valor encontrado!\n"
              f"        chave: {key_val} valor: {value_val}")

        if mode_val == 'FL':
            fl_stats.append(hop_count)

        elif mode_val == 'RW':
            rw_stats.append(hop_count)

        elif mode_val == 'BP':
            bp_stats.append(hop_count)

        msgs_vistas.append(id_msg)


if __name__ == '__main__':
    # Lê os argumentos passados por linha de comando
    p = argparse.ArgumentParser(description="")

    p.add_argument("end", help="Endereço do nó a ser criado.")
    p.add_argument("viz", help="Nome do arquivo que contém a lista de nós vizinhos.", nargs='?')
    p.add_argument("lista_cv", help="Nome do arquivo que contém a lista de pares chave-valor.", nargs='?')

    args = p.parse_args()

    # Inicializa endereço, porta, seqno e ttl
    host, port = args.end.split(":")
    seqno = 1
    ttl = 100
    
    # Parâmetros para busca em profundidade
    no_mae = ""
    viz_disp = []
    viz_ativ = False
    
    # Parâmetros para estatísticas
    count_msgs = {"FL": 0, "RW": 0, "BP": 0}

    fl_stats = []
    rw_stats = []
    bp_stats = []

    # Lista de mensagens já vistas
    msgs_vistas = []

    # Inicializa socket
    sock_host = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock_host.bind((host, int(port)))
    print(f"Servidor criado: {host}:{port}")

    sock_online = True

    # Inicializa lista de vizinhos
    vizinhos = []
    if args.viz:
        arq_viz = args.viz
        with open(arq_viz, 'r') as file:
            for no in file.readlines():
                # Remove quebra de linha
                no = no[:14]

                # Envia HELLO para o vizinho listado
                print(f"Tentando adicionar vizinho {no}")
                msg_hello = f"{host}:{port} {seqno} 1 HELLO"

                ack_hello = send_msg(msg_hello, no)

                # Adiciona à lista de vizinhos conhecidos
                if ack_hello:
                    vizinhos.append(no)

    # Inicializa lista de pares chave_valor
    cvs = {}
    if args.lista_cv:
        arq_cv = args.lista_cv
        with open(arq_cv, 'r') as file:
            for line in file.readlines():
                chave, valor = line.split()
                cvs[chave] = valor
                print(f"Adicionando par ({chave}, {valor}) na tabela local")

    # Inicia threads de receber inputs e ouvir mensagens
    recvs_inputs = threading.Thread(target=user)
    listen_msgs = threading.Thread(target=listen)

    recvs_inputs.start()
    listen_msgs.start()

    recvs_inputs.join()
    listen_msgs.join()

    sys.exit(0)


