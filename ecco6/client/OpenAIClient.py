import logging
from typing import BinaryIO, Mapping, Sequence

from openai import OpenAI

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

class OpenAIClient:
  """The OpenAI client.
  
  This client is responsible for audio-based questioning-answering.
  """
  def __init__(
      self, openai_api_key: str, chat_model: str = "gpt-3.5-turbo",
      stt_model: str = "whisper-1", tts_model: str = "tts-1", 
      tts_voice: str = "nova"):
    self.client = OpenAI(api_key=openai_api_key)
    self.chat_model = chat_model
    self.stt_model = stt_model
    self.tts_model = tts_model
    self.tts_voice = tts_voice
    logging.info("OpenAIClient initialized")

  def speech_to_text(self, file: BinaryIO) -> str:
    """Transfer speech recording to text.
  
      Args:
        file: The file of the audio recording
      Returns:
        A string of audio recording.
    """
    transcription = self.client.audio.transcriptions.create(
        model=self.stt_model,
        file=file,
    )
    logging.debug(f"Transcribed {file.name} to {transcription.text}")
    return transcription.text

  def text_to_speech(self, text: str) -> bytes:
    """Transfer generated text to audio response.
  
      Args:
        file: The generated text from GPT. 
      Returns:
        The bytes of audio response.
    """
    response = self.client.audio.speech.create(
        model=self.tts_model,
        voice=self.tts_voice,
        input=text,
    )
    logging.debug(f"Converted {text} to audio")
    return response.read()

  def chat_completion(self, messages: Sequence[Mapping[str, str]]) -> str:
    """Complete chat by getting response from GPT API.

      Args:
        messages: The chat messages in session state. 
      Returns:
        A string of response from OpenAI.
    """
    response = self.client.chat.completions.create(
      model=self.chat_model,
      messages=messages,
    )
    logging.debug(f"Send {len(messages)} messages to {self.chat_model}. Received {response.choices[0].message.content}")
    return response.choices[0].message.content
