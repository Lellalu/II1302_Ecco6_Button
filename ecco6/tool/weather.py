from langchain.pydantic_v1 import BaseModel
import requests
import streamlit as st
from typing import Optional

class WeatherInput(BaseModel):
    city_name: str
    date: Optional[str]

def get_weather(input_data: WeatherInput) -> str:
    base_url = "https://ai-weather-by-meteosource.p.rapidapi.com"
    headers = {
        "X-RapidAPI-Key": st.secrets["WEATHER_API_KEY"],
        "X-RapidAPI-Host": "ai-weather-by-meteosource.p.rapidapi.com"
    }

    find_places_url = f"{base_url}/find_places"
    find_places_query = {"text": input_data.city_name, "language": "en"}
    find_places_response = requests.get(find_places_url, headers=headers, params=find_places_query)
    place_id = find_places_response.json()[0]['place_id']

    if input_data.date:
        url = f"{base_url}/daily"
    else:
        url = f"{base_url}/current"
    
    querystring = {
        "place_id": place_id,
        "timezone": "auto",
        "language": "en",
        "units": "metric"
    }

    response = requests.get(url, headers=headers, params=querystring)

    if input_data.date:
        daily_forecast = None
        weather_data = response.json()
        for i in range(21):  # Assuming 22 days of forecast data are available
            daily_forecast = weather_data['daily']['data'][i]
            if daily_forecast['day'] == input_data.date:
                break

        if daily_forecast is not None:
            response = f"On {daily_forecast['day']}, the weather in {input_data.city_name} is forecasted to be {daily_forecast['summary']}. "
            response += f"The temperature will range from {daily_forecast['temperature_min']}°C to {daily_forecast['temperature_max']}°C. "
            response += f"It will feel like {daily_forecast['feels_like_min']}°C to {daily_forecast['feels_like_max']}°C. "
            response += f"The wind speed will be {daily_forecast['wind']['speed']} m/s coming from the {daily_forecast['wind']['dir']} direction, "
            response += f"with gusts up to {daily_forecast['wind']['gusts']} m/s. "
            response += f"There is {daily_forecast['precipitation']['type']} precipitation, and the humidity level is {daily_forecast['humidity']}%. "
            response += f"The visibility is {daily_forecast['visibility']} km."
        else:
            response = f"No forecast available for {input_data.date} in {input_data.city_name}."
    else:
        weather_data_c = response.json()
        current_weather = weather_data_c['current']
        response = f"In {input_data.city_name}, the weather is currently {current_weather['summary']}. "
        response += f"The temperature is {current_weather['temperature']}°C, but it feels like {current_weather['feels_like']}°C. "
        response += f"The wind speed is {current_weather['wind']['speed']} m/s coming from the {current_weather['wind']['dir']} direction, "
        response += f"with gusts up to {current_weather['wind']['gusts']} m/s. "
        response += f"There is {current_weather['precipitation']['type']} precipitation, and the humidity level is {current_weather['humidity']}%. "
        response += f"The UV index is {current_weather['uv_index']}. "
        response += f"The visibility is {current_weather['visibility']} km. "
        response += f"The wind chill is {current_weather['wind_chill']}°C."

    return response