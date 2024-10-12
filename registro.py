"""  Registro de consultas  """
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
from dotenv import load_dotenv
import re
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

def diagnostico_psicologico():
    pass

# Rota para receber os dados via POST
@app.post("/salvar/")
async def salvar_registro(historico: str):
    """ corigir isso aqui para calcular os campos necessários """
    mensagens = "\n".join(interpretar_mensagens_brutas(historico))
    #
    # FALTA FAZER O LAUDO, GRAVAR NO BANCO E MOSTRAR NO STREAMLIT
    #
    #try:
    #    # Insere os dados no banco de dados
    #    cursor.execute("""
    #    #INSERT INTO registros (nome, situacao, dialogos, laudo) 
    #    #VALUES (?, ?, ?, ?)
    #    """, (registro.nome, registro.situacao, registro.dialogos, registro.laudo))
    #    conn.commit()
    #    return {"mensagem": "Dados salvos com sucesso!"}
    #except Exception as e:
    #    raise HTTPException(status_code=500, detail=f"Erro ao salvar dados: {str(e)}")
    print("Mensagens tratadas ",mensagens)
    return "Ok"



# Rota para listar todos os registros
@app.get("/registros/")
async def listar_registros():
    cursor.execute("SELECT * FROM registros")
    registros = cursor.fetchall()
    return {"registros": registros}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("registro:app", host="0.0.0.0",reload=True,port=8010)
