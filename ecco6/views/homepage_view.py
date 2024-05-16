import asyncio
import logging
from typing import Tuple
import json

import streamlit as st
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from PIL import Image
from streamlit_js_eval import get_geolocation
from streamlit_mic_recorder import mic_recorder

from ecco6 import util
from ecco6.agent import Ecco6Agent
from ecco6.auth import firebase_auth
from ecco6.client.OpenAIClient import OpenAIClient

from firebase_admin import db


def init_homepage() -> Tuple[st.selectbox, st.selectbox]:
  """Initialize the Chatbox and the Sidebar of streamlit.
  
  Initialize the session state and the sidebar.

  Returns:
    A tuple cotaining the two selectbox of chat model and tts voice.
  """
  #st.title("Chatbox")

  location = get_geolocation()
  if location:
    st.session_state.latitude = location["coords"]["latitude"]
    st.session_state.longitude = location["coords"]["longitude"]

  if "messages" not in st.session_state:
     st.session_state.messages = []


  image = Image.open('./ecco6/ecco6logo.png')
  col1, col2 = st.columns([1, 3])  # Adjust the width ratio as needed
  with col1:
      st.image(image, width=150)
  with col2:
      st.title("Welcome to ECCO6")
  st.subheader("Instructions:")
  st.write("1. Start by connecting your device with the Ecco6 device via Bluetooth.")
  st.write("2. Say the wake word 'Hello' to get the Ecco6 ready for your questions.")
  st.write("   Before each question, say the wake word 'Hello'.")
  st.write("3. In the sidebar:")
  st.write("   - 3.1. Connect the app with your Google account to access the full potential of our different services.")
  st.write("   -  Services include:")
  st.write("      - 1. Modifying your Google Calendar")
  st.write("      - 2. Getting your location")
  st.write("      - 3. Modifying your tasks")
  st.write("      - 4. Realtime weather and news infromation")


  with st.sidebar:
    st.markdown("""
      <style >
      .stDownloadButton, div.stButton {text-align:center}
      .stDownloadButton button, div.stButton > button:first-child {
          background-color: #48cae4;
          color:#000000;
          border-radius: 2px;
          border: 2px solid #48cae4;                                                   
      }
          }
      </style>""", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    #set three colums on the page, markdown on the 2nd col to ensure center positioning.
    with col1:
        st.write(' ')

    with col2:
        st.markdown("<h1 style='text-align: center;color: #03045e'>Ecco6</h1>", unsafe_allow_html=True)
        #image = Image.open('./ecco6/ecco6logo.png')
        #st.image(image, width=90)

    with col3:
        st.write(' ')

    st.info("This app is a voice AI assistant, which is able to connect to multiple services.")
    st.button(label='Sign Out', on_click=firebase_auth.sign_out, type='primary')

    settings_expander = st.expander(label='Settings')
    with settings_expander:
      openai_chat_model = st.selectbox(
        "OpenAI chat model",
        ("gpt-3.5-turbo", "gpt-4-turbo")
      )
      openai_tts_voice = st.selectbox(
        "OpenAI voice options",
        ("alloy", "echo", "fable", "onyx", "nova", "shimmer")
      )

    rpi_url_input = st.text_input(
      "Raspberry Pi alarm server url",
      "localhost:8080"
    )
    if rpi_url_input:
        st.session_state.rpi_url = rpi_url_input

    settings_expander = st.expander(label='Services')
    with settings_expander:
      st.write("Services to Google:")
      google_client_config = {
         "web": {
            "client_id": st.secrets["GOOGLE_AUTH"]["CLIENT_ID"],
            "project_id": st.secrets["GOOGLE_AUTH"]["PROJECT_ID"],
            "auth_uri": st.secrets["GOOGLE_AUTH"]["AUTH_URI"],
            "token_uri": st.secrets["GOOGLE_AUTH"]["TOKEN_URI"],
            "auth_provider_x509_cert_url": st.secrets["GOOGLE_AUTH"]["AUTH_PROVIDER_X509_CERT_URL"],
            "client_secret": st.secrets["GOOGLE_AUTH"]["CLIENT_SECRET"],
            "redirect_uris": st.secrets["GOOGLE_AUTH"]["REDIRECT_URIS"],
         }
      }
      scopes = [
         "https://www.googleapis.com/auth/calendar",
         "https://mail.google.com/",
         "https://www.googleapis.com/auth/tasks",
         "https://www.googleapis.com/auth/documents",
         "https://www.googleapis.com/auth/drive",
         "https://www.googleapis.com/auth/drive.appdata",
      ]
      flow = InstalledAppFlow.from_client_config(
          google_client_config,
          scopes=scopes,
          redirect_uri = st.secrets["GOOGLE_AUTH"]["REDIRECT_URIS"][0],
      )

      authorization_url = asyncio.run(firebase_auth.client.get_authorization_url(
          st.secrets["GOOGLE_AUTH"]["REDIRECT_URIS"][0],
          scope=scopes,
          extras_params={"access_type": "offline"},
      ))
      auth_code = st.query_params.get("code")
      if auth_code:
        flow.fetch_token(code=auth_code)
        google_credentials = flow.credentials
        st.session_state["google_credentials"] = google_credentials
        st.query_params.clear()
      if "google_credentials" not in st.session_state:
        st.link_button("Sign in with Google", authorization_url)
      else:
        creds = st.session_state.google_credentials
        if not creds.valid or (creds.expired and creds.refresh_token): 
          creds.refresh(Request())
          st.session_state.google_credentials = creds
        st.write("Logged into Google!")
      return openai_chat_model, openai_tts_voice


def homepage_view():
    st.empty()
    openai_chat_model, openai_tts_voice = init_homepage()

    openai_client = OpenAIClient(
        st.secrets["OPENAI_API_KEY"],
        chat_model=openai_chat_model,
        tts_voice=openai_tts_voice)
    
    ecco6_agent = Ecco6Agent(
        st.secrets["OPENAI_API_KEY"], 
        google_credentials=st.session_state.google_credentials if "google_credentials" in st.session_state else None,
        rpi_url=st.session_state.rpi_url if "rpi_url" in st.session_state else None,
        chat_model=openai_chat_model)
    
    user_audio = mic_recorder(
        start_prompt="Start recording",
        stop_prompt="Stop recording",
        just_once=True,
        format="wav",
    )
    if user_audio:
      buffer = util.create_memory_file(user_audio['bytes'], "foo.wav")
      transcription = openai_client.speech_to_text(buffer)
      logging.info(f"User said: {transcription}.")
      util.append_message("user", transcription, user_audio['bytes'])
      answer = ecco6_agent.chat_completion([
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages
      ])
      if answer:
        logging.info(f"trying to play {answer}.")
        audio_response = openai_client.text_to_speech(answer)
        util.append_message("assistant", answer, audio_response)
        util.autoplay_hidden_audio(audio_response)
