""" Psicoterapeuta Virtual STS """
import os
import time
from io import BytesIO
# import uuid
import concurrent.futures

import streamlit as st # type: ignore
from streamlit_js_eval import streamlit_js_eval

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser  #,  JsonOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI,HarmCategory,HarmBlockThreshold
from langchain_openai import ChatOpenAI

from dotenv import load_dotenv

from PIL import Image
import requests

from gtts import gTTS
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

from groq import Groq

from tools import *
from globals import *

# Ler o arquivo .env
load_dotenv()

audio_saida_bytes = BytesIO()

# para usar o grog para transcrição de audios para texto
client = Groq()

# configuração do eleven labs texto para audio
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
client_eleven = ElevenLabs(api_key=ELEVENLABS_API_KEY,)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configuração da página
st.set_page_config(page_title="Eu te Escuto", page_icon="🤖", layout="wide")

success_placeholder = st.empty()

# função para salvar e encerrar a sessão
def salvar_e_encerrar():
    """    salvar a conversa """
    resultado_salvar = salvar_registro(str(st.session_state.chat_history))
    if resultado_salvar[0]:
        success_placeholder.success("Dados salvos com sucesso! 🚀 ✅")
        #st.success("Dados salvos com sucesso! 🚀 ✅")
    else:
        success_placeholder.error(f"Erro na gravação {resultado_salvar[1]}")
        #st.error(f"Erro na gravação {resultado_salvar[1]}")
    st.session_state.clear()  # Limpa o estado da sessão
    streamlit_js_eval(js_expressions="parent.window.location.reload()")   # Reinicializa a página

# Função para obter a resposta do bot

def get_response(user_query, chat_history, gpt=True):
    """ função de consult ao llm """
    #
    # definindo qual prompt usar
    #
    arquivo_template = 'prompt_glenda_dialogo.txt'
    #arquivo_template = 'prompt_giselle_dialogo.txt'
    with open(arquivo_template) as arquivo:
        template = arquivo.read()    
    prompt = ChatPromptTemplate.from_template(template)
    if gpt:
        print("Consultado gpt")
        llm = ChatOpenAI(model="gpt-3.5-turbo", api_key=OPENAI_API_KEY, temperature=1.0)
    else:
        print("consultando gemini")
        llm = ChatGoogleGenerativeAI(
        model="gemini-pro",
        safety_settings={HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE},
        temperature=1.0,
        frequence_penalty=2,)
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

if "gpt" not in st.session_state:
    st.session_state.gpt = True

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
        ("Google", "Eleven Labs","Muda")
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
    for i in range(4):
        #try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(get_response, query, st.session_state.chat_history, st.session_state.gpt)
            #resposta = get_response(query, st.session_state.chat_history, st.session_state.gpt)
            try:
                resposta = future.result(timeout=5)  # Retorna o resultado se a função concluir no tempo limite
                st.session_state.gpt = not st.session_state.gpt
                break
            except concurrent.futures.TimeoutError:
                print("Tempo limite excedido na chamada ")
                st.session_state.gpt = not st.session_state.gpt
                continue
            except Exception as e:
                print(f"Erro na resposta {e} ")
                time.sleep(1)
    else:
        resposta = "Não entendi colega. Diga o que você quer "
    response_text = tratar_texto(resposta)
    print("Mensagem recebida e tratada: ", response_text)
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
    else:
        pass
