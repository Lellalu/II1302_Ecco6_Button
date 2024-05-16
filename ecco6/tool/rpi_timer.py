import requests
from langchain.pydantic_v1 import BaseModel, Field


class SetRpiTimerInput(BaseModel):
    time: str = Field(description="The time set for the timer in HH:MM:SS format.")

def set_rpi_timer(time: str, url: str):
    time_list = time.strip().split(":")
    if len(time_list) != 3:
        return "Time not in HH:MM:SS format."
    
    count_down = {'hour': time_list[0], 'minute': time_list[1], 'second': time_list[2]}

    try:
        r = requests.post(url, json = count_down)
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        return str(e)

    return "The timer has been successfully set."