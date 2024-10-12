import re

# Função para extrair mensagens usando regex
def interpretar_mensagens_brutas(texto):
    # Expressão regular para capturar o conteúdo dentro de content='...'
    padrao = r"content='(.*?)'"  # Captura o conteúdo entre aspas simples
    mensagens = re.findall(padrao, texto, re.DOTALL)  # Captura múltiplas linhas
    return mensagens

# Função para ler o arquivo de entrada
def ler_arquivo(nome_arquivo):
    try:
        with open(nome_arquivo, "r", encoding="utf-8") as f:
            return f.read()  # Lê todo o conteúdo como string
    except FileNotFoundError:
        print(f"Erro: O arquivo '{nome_arquivo}' não foi encontrado.")
        return ""

# Programa principal
nome_arquivo = "saida.txt"  # Nome do arquivo contendo as mensagens brutas
texto = ler_arquivo(nome_arquivo)  # Lê o conteúdo do arquivo

if texto:
    mensagens = interpretar_mensagens_brutas(texto)  # Extrai mensagens
    print("Mensagens extraídas:")
    for i, mensagem in enumerate(mensagens, 1):
        print(f"{i}. {mensagem}")
else:
    print("Nenhuma mensagem foi encontrada.")
