import json
import requests
from langchain.pydantic_v1 import BaseModel, Field

class SetLightInput(BaseModel):
    pass

def turn_on_light(url: str, token: str):
    headers = {"Content-Type": "application/json",
               "Authorization": f"Bearer {token}"}
    try:
        r = requests.post(url, headers=headers, timeout=3)
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        return str(e)

    return "The light has been successfully turned on."

def turn_off_light(url: str, token: str):
    headers = {"Content-Type": "application/json",
               "Authorization": f"Bearer {token}"}
    try:
        r = requests.post(url, headers=headers, timeout=3)
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        return str(e)
    
def set_brightness_low(url: str, token: str):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    try:
        r = requests.post(url, headers=headers, timeout=3)
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        return str(e)

    return "Brightness of the light has been set as low."

def set_brightness_medium(url: str, token: str):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"}
    try:
        r = requests.post(url, headers=headers, timeout=3)
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        return str(e)

    return "Brightness of the light has been set as medium."

def set_brightness_high(url: str, token: str):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"}
    try:
        r = requests.post(url, headers=headers, timeout=3)
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        return str(e)

    return "Brightness of the light has been set as high."