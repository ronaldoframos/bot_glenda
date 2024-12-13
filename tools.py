""" Ferramentas para acesso ao banco de dados e o LLM """
import sqlite3
from dotenv import load_dotenv
import re,json
import logging

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser  #,  JsonOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI,HarmCategory,HarmBlockThreshold

from globals import *

logger = logging.getLogger()

load_dotenv()

# Conecta ao banco de dados SQLite (será criado se não existir)
try:
    conn = sqlite3.connect(BANCO_DADOS)
    cursor = conn.cursor()
    # Cria a tabela, se ainda não existir
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        situacao TEXT NOT NULL,
        dialogos TEXT NOT NULL,
        laudo TEXT NOT NULL
    )
    """)
    conn.commit()
finally:
    conn.close()

def interpretar_mensagens_brutas(texto):
    """  Expressão regular para capturar o conteúdo dentro de content='...' """
    padrao = r"content='(.*?)'"  # Captura o conteúdo entre aspas simples
    mensagens = re.findall(padrao, texto, re.DOTALL)  # Captura múltiplas linhas
    return mensagens

def extrair_json_de_string(string: str):
    """ extrair o json das respostas da llm """
    try:
        # Expressão regular para encontrar o conteúdo entre as primeiras { e }
        padrao = r"\{.*?\}"
        correspondencia = re.search(padrao, string, re.DOTALL)

        if correspondencia:
            # Extrai o JSON e converte para um dicionário
            json_str = correspondencia.group(0)
            dados = json.loads(json_str)
            return dados
        else:
            print("Nenhum JSON encontrado na string.")
            return None
    except json.JSONDecodeError as e:
        print(f"Erro ao decodificar JSON: {e}")
        return None
    
def diagnostico_psicologico(dialogo : str):
    """ fazer o diagnostico psicologico do paciente que terminou a consulta"""
    
    template = """

    Considere que você seja um psicoterapeuta. O  texto a seguir é um diálogo entre um paciente e um psicoterapeuta virtual.  Analise o 
    diálogo e faça um resumo da situação psicológica do paciente. Crie uma estrutura de dados na forma de um json retornando este resumo 
    em um campo denominado laudo. Além disso inclua no json um campo adicional chamado "situacao" cujos valores poderão ser crítica, transtorno médio, 
    trastorno moderado ou ausência de sintomas". Você deve considerar a situação como crítica quando a pessoa se manifestar com alta 
    tendência a ansiedade, depressão ou até mesmo ideias suicidas. Em outra forma considere se se trata de situação mediana, leve ou ausencias de sitomas de transtornos o que faria que a situação 
    pudesse ser considerada como transtorno médio, transtorno moderado ou ausência de sintomas. |Finalmente adicione ao json um campo chamado nome 
    incluindo o nome do paciente caso tenha sido mencionado. Não repita o seu prório nome nas perguntas sequentes a sua introdução.

    texto do diálogo: {texto}.
    
    """
    prompt = ChatPromptTemplate.from_template(template)
    #llm = ChatOpenAI()
    llm = ChatGoogleGenerativeAI(
    model="gemini-pro",
    safety_settings={HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE},
    temperature=1.0,
    frequence_penalty=2,
    )
    chain = prompt | llm | StrOutputParser()
    try:
        resp = chain.invoke({"texto": dialogo,})
    except Exception as e:
        resp = "No momento estou sem condições de continuar a conversa. Tente novamente em seguida"
        logger.error(str(e))
    return resp

def salvar_registro(historico: str):
    """ corigir isso aqui para calcular os campos necessários """
    mensagens = "\n".join(interpretar_mensagens_brutas(historico))
    json_resposta = extrair_json_de_string(diagnostico_psicologico(mensagens))
    if json_resposta["nome"]==None:
        json_resposta["nome"] = "Anônimo"
    with sqlite3.connect(BANCO_DADOS) as conn:
        conn.execute(""" INSERT INTO registros (nome, situacao, dialogos, laudo) VALUES (?, ?, ?, ?) """, 
                       (json_resposta["nome"], json_resposta["situacao"], mensagens, json_resposta["laudo"]))
        return (True,"")
    return (False, f"Erro: {e}") 

def listar_registros():
    """ retornar os registros gravados no banco de dados """
    with sqlite3.connect(BANCO_DADOS) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM registros")
        registros = cursor.fetchall()
        return {"registros": registros}
    return None

def remover_texto_entre_asteriscos(texto):
    return re.sub(r'\*.*?\*', '', texto)

def remover_human_message(texto):
    # Expressão regular para remover 'HumanMessage(...)', ignorando maiúsculas/minúsculas
    return re.sub(r'humanmessage\([^)]*\)', '', texto, flags=re.IGNORECASE)

def remover_resposta_chatbot(texto):
    # Expressão regular para remover 'ChatbotMessage(...)', ignorando maiúsculas/minúsculas
    return re.sub(r'Resposta do Chatbot\([^)]*\)', '', texto, flags=re.IGNORECASE)   

def remover_glenda_inicio(texto):
    # Expressão regular para remover 'glenda' do início da string, ignorando maiúsculas e minúsculas
    return re.sub(r'^glenda\s*', '', texto, flags=re.IGNORECASE)

def remove_chatbot_inicio(frase):
    """
    Remove a palavra 'Chatbot' do início de uma frase, 
    caso esteja presente, mantendo o restante da frase intacto.

    :param frase: A frase a ser processada (string).
    :return: A frase sem 'Chatbot' no início.
    """
    if frase.lower().startswith("chatbot"):
        return frase[len("Chatbot"):].lstrip()
    return frase

def tratar_texto(response_text):
    response_text = remove_chatbot_inicio(response_text)
    response_text = response_text.replace(']','')
    response_text = response_text.replace('[','')
    response_text = response_text.replace('{','')
    response_text = response_text.replace('}','')
    response_text = response_text.replace(':','')
    response_text = response_text.replace('ofensa','')
    trecho1 = "(aqui você irá colocar a variável com o nome do paciente)"
    response_text = response_text.replace(trecho1,'')   
    response_text = remover_human_message(response_text) 
    response_text = remover_resposta_chatbot(response_text)
    response_text = remover_glenda_inicio(response_text)    
    return remover_texto_entre_asteriscos(response_text)
