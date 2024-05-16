import os
import difflib
import csv
import requests
from langchain.pydantic_v1 import BaseModel, Field
from langchain.tools import StructuredTool
import streamlit as st
import requests
from .location import get_current_location
from ecco6.tool import stops

#================ TRAVEL PLANER ===================
current_dir = os.path.dirname(__file__)
#current_dir = os.path.dirname(os.path.abspath(__file__))
stops_file = os.path.join(current_dir, "stops.txt")

def get_station_coordinates(station_name):
    reader = csv.DictReader(stops.STOP_CSV_STR.splitlines())
    station_names = [row['stop_name'].lower() for row in reader]

    closest_matches = difflib.get_close_matches(station_name.lower(), station_names, n=1, cutoff=0.6)
    if closest_matches:
        closest_station_name = closest_matches[0]
        reader = csv.DictReader(stops.STOP_CSV_STR.splitlines())
        for row in reader:
            if row['stop_name'].lower() == closest_station_name:
                return float(row['stop_lat']), float(row['stop_lon'])
    return None, None

SL_RESEPLANERARE_API_KEY = st.secrets["SL_RESEPLANERARE_API_KEY"]

class GetTravelSuggestionsInput(BaseModel):
    origin_station_name: str = Field(description="The name of the origin station.")
    destination_station_name: str = Field(description="The name of the destination station.")

def get_travel_suggestions(origin_station_name: str, destination_station_name: str) -> str:
    origin_lat, origin_lon = get_station_coordinates(origin_station_name)
    destination_lat, destination_lon = get_station_coordinates(destination_station_name)

    if origin_lat is None or origin_lon is None:
        return f"Error: Station '{origin_station_name}' not found in the database."

    if destination_lat is None or destination_lon is None:
        return f"Error: Station '{destination_station_name}' not found in the database."

    url = f"https://journeyplanner.integration.sl.se/v1/TravelplannerV3_1/trip.json?key={SL_RESEPLANERARE_API_KEY}&originCoordLat={origin_lat}&originCoordLong={origin_lon}&destCoordLat={destination_lat}&destCoordLong={destination_lon}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()

        found_lines = 0
        travel_suggestions = ""

        for trip in data.get("Trip", []):
            for leg in trip["LegList"]["Leg"]:
                if "Product" in leg:
                    product = leg["Product"]
                    if product["catOut"] == "TRAIN" and "PENDELTÅG" in product["name"]:
                        travel_suggestions += f"Pendeltåg Line: {product['name']}\n"
                        travel_suggestions += f"Departure: {leg['Origin']['name']}\n"
                        travel_suggestions += f"Destination: {leg['Destination']['name']}\n"
                        travel_suggestions += f"Departure Time: {leg['Origin']['time']}\n"
                        travel_suggestions += f"Arrival Time: {leg['Destination']['time']}\n\n"
                        found_lines += 1
                    elif product["catOut"] == "BUS":
                        travel_suggestions += f"Bus Line: {product['name']}\n"
                        travel_suggestions += f"Departure: {leg['Origin']['name']}\n"
                        travel_suggestions += f"Destination: {leg['Destination']['name']}\n"
                        travel_suggestions += f"Departure Time: {leg['Origin']['time']}\n"
                        travel_suggestions += f"Arrival Time: {leg['Destination']['time']}\n\n"
                        found_lines += 1
                    if found_lines == 2:
                        break
            if found_lines == 2:
                break
        return travel_suggestions or "No travel suggestions found."
    else:
        return f"Error: {response.status_code}"

#================= NEARBY STOPS ======================

class GetNearbyStopsInput(BaseModel):
    latitude: float = Field(description="The latitude of the location.")
    longitude: float = Field(description="The longitude of the location.")
    max_results: int = Field(default=3, description="Maximum number of nearby stops to retrieve.")
    radius: int = Field(default=1000, description="Radius in meters around the location to search for stops.")

SL_NEARBYSTOPS_API_KEY = st.secrets["SL_NEARBYSTOPS_API_KEY"]

def get_nearby_stops(latitude: float, longitude: float, max_results: int = 3, radius: int = 1000) -> list:
    url = f"https://journeyplanner.integration.sl.se/v1/nearbystopsv2.json?key={SL_NEARBYSTOPS_API_KEY}&originCoordLat={latitude}&originCoordLong={longitude}&maxNo={max_results}&r={radius}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        nearby_stops = data.get('stopLocationOrCoordLocation', [])
        formatted_stops = []
        for stop in nearby_stops:
            formatted_stop = {
                'name': stop['StopLocation']['name'],
                'distance': stop['StopLocation']['dist'],
                'location': stop['StopLocation']['id']
            }
            formatted_stops.append(formatted_stop)
        return formatted_stops
    else:
        return []
