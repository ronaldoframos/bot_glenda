""" Psicoterapeuta Virtual STS """
import os
import time
from io import BytesIO
# import uuid

import streamlit as st # type: ignore
from streamlit_js_eval import streamlit_js_eval

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser  #,  JsonOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI,HarmCategory,HarmBlockThreshold
# from langchain_openai import ChatOpenAI

from dotenv import load_dotenv

from PIL import Image
import requests

from gtts import gTTS
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

from groq import Groq

# Ler o arquivo .env
load_dotenv()

audio_saida_bytes = BytesIO()

# para usar o grog para transcrição de audios para texto
client = Groq()

# configuração do eleven labs texto para audio
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
client_eleven = ElevenLabs(api_key=ELEVENLABS_API_KEY,)

# Configuração da página
st.set_page_config(page_title="Eu te Escuto", page_icon="🤖", layout="wide")

# função para salvar e encerrar a sessão
def salvar_e_encerrar():
    """    salvar a conversa
     
      MODIFICAR ESTA PARTE PARA SALVAR DIRETAMENTE NO BANCO E ELIMINAR A NECESSIDADE DO FASTAPI
       
        
     """
    url = "http://localhost:8010/salvar/"
    parametros = {
        "historico": str(st.session_state.chat_history),
    }
    headers = {
        "accept": "application/json"
    }
    try:
        # Envia os dados via POST no formato JSON
        resposta = requests.post(url, headers=headers, params=parametros, data="")
        # Verifica se a requisição foi bem-sucedida
        if resposta.status_code == 200:
            print("Dados enviados com sucesso!")
        else:
            print(f"Erro: {resposta.status_code}") 
    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição: {e}")
    st.session_state.clear()  # Limpa o estado da sessão
    streamlit_js_eval(js_expressions="parent.window.location.reload()")   # Reinicializa a página

# Função para obter a resposta do bot
def get_response(user_query, chat_history):
    """ função de consult ao llm """
    template = """

    **Prompt:**

    "Você é um chatbot treinado para atuar como uma médica psicoterapeuta. Seu nome é Glenda. Seu objetivo é ouvir com empatia, fazer perguntas abertas e ajudar o usuário a explorar seus sentimentos e pensamentos de forma segura e não julgadora. Sempre mostre compreensão, mantenha a confidencialidade e forneça suporte emocional. Se um problema específico precisar de intervenção de um profissional de saúde mental, encoraje o usuário a buscar ajuda de um psicoterapeuta qualificado."

    **Exemplos de Respostas:**

    1. Usuário: "Estou me sentindo muito ansioso ultimamente e não sei o que fazer."
    Chatbot: "Sinto muito que você esteja passando por isso. Pode me contar um pouco mais sobre o que tem causado essa ansiedade? Estou aqui para ouvir."

    2. Usuário: "Tenho tido muitos conflitos no trabalho e isso está me afetando."
    Chatbot: "Entendo que conflitos no trabalho podem ser muito estressantes. Como esses conflitos têm impactado você pessoalmente? Vamos explorar isso juntos."

    3. Usuário: "Não consigo parar de me sentir triste e desmotivado."
    Chatbot: "Lamento que você esteja se sentindo assim. O que você acha que pode estar contribuindo para esses sentimentos? Falar sobre isso pode ajudar a esclarecer."

    4. Usuário: "Estou lutando para lidar com a perda de um ente querido."
    Chatbot: "A perda de alguém querido é extremamente dolorosa. Você gostaria de compartilhar mais sobre essa pessoa e como você está se sentindo? Estou aqui para ouvir e apoiar você."

    ---      
    Os dados para gerar a resposta são:
        
    História da conversa: {chat_history}

    Pergunta do usuário: {user_question}.
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
        "chat_history": chat_history,
        "user_question": user_query,
    })
    return resp

# Estrutura do cabeçalho
st.markdown(
    """
    <div class="header">
        <h1> Converse comigo. Sou o Dra. Glenda e te escutarei.  </h1>
    </div>
    """,
    unsafe_allow_html=True
)

# Inicialização do estado da sessão
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

audio_query = None
texto_query = None
query = None

# Entrada do usuário no rodapé
with st.sidebar:
    # Carregar a imagem
    image_path = "./glenda.jpg" # Substitua pelo caminho correto 
    image = Image.open(image_path)
    st.image(image,caption = 'Dra Glenda',width=250, use_column_width=False)
    audio_input = st.experimental_audio_input("Registre sua mensagem em áudio ...")
    opcao_sintese_audio = st.radio(
        "Síntese de Áudio:",
        ("Google", "Eleven Labs")
    )
    print("processando audio")
    if audio_input:
        audio_bytes = audio_input.getvalue()
        audio_file = BytesIO(audio_bytes)
        transcription = client.audio.transcriptions.create(
            file=("audio.wav", BytesIO(audio_bytes)), # Required audio file
            model="whisper-large-v3", # Required model to use for transcription
            prompt="Specify context or spelling",  # Optional
            response_format="json",  # Optional
            language="pt",  # Optional
            temperature=0.0  # Optional
        )
        audio_query = transcription.text
    texto_query = st.chat_input("Digite a sua mensagem aqui ...", key="user_input")
    if st.button("Encerrar"):
        salvar_e_encerrar()
if texto_query:
    query = texto_query
elif audio_query:
    query = audio_query
if query:
    st.session_state.chat_history.append(HumanMessage(content=query))
    for i in range(10):
        try:
            resposta = get_response(query, st.session_state.chat_history)
            break
        except Exception as e:
            print(f"Erro na resposta {e} ")
            time.sleep(5)
    else:
        resposta = "Não entendi colega. Diga o que você quer "
    response_text = resposta
    response_text = response_text.replace(']','')
    response_text = response_text.replace('[','')
    response_text = response_text.replace('{','')
    response_text = response_text.replace('}','')
    response_text = response_text.replace(':','')
    response_text = response_text.replace('ofensa','')
    st.session_state.chat_history.append(AIMessage(content=response_text))
    for message in st.session_state.chat_history:
        if isinstance(message, AIMessage):
            with st.chat_message("AI"):
                st.write(message.content)
        elif isinstance(message, HumanMessage):
            with st.chat_message("Human"):
                st.write(message.content)
        else:
            with st.chat_message("Human"):
                st.write(message)
    if response_text and opcao_sintese_audio == 'Google':
        myobj = gTTS(text=response_text, lang='pt', slow=False)
        myobj.write_to_fp(audio_saida_bytes)
        st.audio(audio_saida_bytes, format='audio/mp3',autoplay=True)
    elif response_text and opcao_sintese_audio == 'Eleven Labs':
        response = client_eleven.text_to_speech.convert(
            voice_id="cyD08lEy76q03ER1jZ7y", # ScheilaSMTy
            output_format="mp3_22050_32",
            text=response_text,
            model_id="eleven_multilingual_v2",
            voice_settings=VoiceSettings(
                stability=0.0,
                similarity_boost=1.0,
                style=0.0,
                use_speaker_boost=True,
            ),
        )
        for chunk in response:
            if chunk:
                audio_saida_bytes.write(chunk)
        audio_saida_bytes.seek(0)
        st.audio(audio_saida_bytes, format='audio/mp3',autoplay=True)
