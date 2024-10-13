"""  Registro de consultas  """
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
from dotenv import load_dotenv
import re,json

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser  #,  JsonOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI,HarmCategory,HarmBlockThreshold

#
# carregar variaveis de ambiente
#
load_dotenv()

PRODUCAO = False

if PRODUCAO:
    app = FastAPI(
    docs_url=None, # Disable docs (Swagger UI)
    redoc_url=None, # Disable redoc
)
else:
    app = FastAPI()

# Configurar o CORS
origins = ["*"]  # Permitir todas as origens, você pode ajustar isso conforme necessário

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=1,
    allow_methods=["*"], 
    allow_headers=["*"],
)


# Conecta ao banco de dados SQLite (será criado se não existir)
conn = sqlite3.connect("dados.db")
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

# Modelo de dados com Pydantic para validar entrada
class Registro(BaseModel):
    nome: str
    situacao: str
    dialogos: str
    laudo: str

# Função para extrair mensagens usando regex
def interpretar_mensagens_brutas(texto):
    # Expressão regular para capturar o conteúdo dentro de content='...'
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
    incluindo o nome do paciente caso tenha sido mencionado.

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
    resp = chain.invoke({
        "texto": dialogo,
    })
    return resp

# Rota para receber os dados via POST
@app.post("/salvar/")
async def salvar_registro(historico: str):
    """ corigir isso aqui para calcular os campos necessários """
    mensagens = "\n".join(interpretar_mensagens_brutas(historico))
    json_resposta = extrair_json_de_string(diagnostico_psicologico(mensagens))
    try:
        # Insere os dados no banco de dados
        cursor.execute(""" INSERT INTO registros (nome, situacao, dialogos, laudo) VALUES (?, ?, ?, ?) """, 
                       (json_resposta["nome"], json_resposta["situacao"], mensagens, json_resposta["laudo"]))
        conn.commit()
        return {"mensagem": "Dados salvos com sucesso!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar dados: {str(e)}")

# Rota para listar todos os registros
@app.get("/registros/")
async def listar_registros():
    cursor.execute("SELECT * FROM registros")
    registros = cursor.fetchall()
    return {"registros": registros}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("registro:app", host="0.0.0.0",reload=True,port=8010)
