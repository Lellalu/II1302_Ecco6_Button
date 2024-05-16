import requests
import streamlit as st

def get_top_headlines():
    url = "https://google-news13.p.rapidapi.com/world"
    querystring = {"lr": "en-US"}
    headers = {
        "X-RapidAPI-Key": st.secrets["WEATHER_API_KEY"],
        "X-RapidAPI-Host": "google-news13.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)
    data = response.json()

    headlines_info = []

    if 'items' in data:
        top_5_headlines = data['items'][:3]
        for item in top_5_headlines:
            title = item.get('title', 'Title not available')
            snippet = item.get('snippet', 'Snippet not available')
            publisher = item.get('publisher', 'Publisher not available')
            headline_info = {
                'title': title,
                'snippet': snippet,
                'publisher': publisher
            }
            headlines_info.append(headline_info)

    return headlines_info