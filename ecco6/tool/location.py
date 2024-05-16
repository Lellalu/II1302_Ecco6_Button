import googlemaps
import streamlit as st


def get_current_location(latitude: float, longitude: float) -> str:
  gmaps = googlemaps.Client(key=st.secrets["GOOGLE_API_KEY"])
  reverse_geocode_result = gmaps.reverse_geocode((latitude, longitude))
  if reverse_geocode_result:
    return reverse_geocode_result[0]["formatted_address"]
  return "Cannot find the current location"

