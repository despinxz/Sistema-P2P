# Sistema-P2P
Este repositório contém a implementação de um sistema peer-to-peer em Python. Ele permite a busca de valores na rede a partir de uma chave, através dos métodos de flooding, random walk ou busca em profundidade.

## Como executar
Para executar o aplicativo, execute o seguinte comando no terminal:
  python main.py <endereco>:<porta> [vizinhos.txt[pares-chave-valor.txt]]
Sendo cada parâmetro:
- **endereco**: O endereço IP do nó a ser criado;
- **porta**: A porta do nó a ser criado;
- **vizinhos.txt**: Arquivo .txt contendo o endereço e porta de vizinhos conhecidos (opcional);
- **pares-chave-valor.txt**: Arquivo .txt contendo os pares chave-valor do nó (opcional).
