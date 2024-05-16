from firebase_admin import db
from langchain.pydantic_v1 import BaseModel, Field
import streamlit as st
import time
import datetime
import pyttsx3
from typing import Optional

class SetAlarmInput(BaseModel):
    day: str = Field(description="The day to set the alarm for.")
    date: str = Field(description="The date to set the alarm for.")
    clock: str = Field(description="The time to set the alarm for.")
    title: Optional[str] = Field(description="Optional title for the alarm.")


class ModifyAlarmArgs(BaseModel):
    existing_day: str
    existing_date: str
    existing_clock: str
    existing_title: str = None
    new_day: str = None
    new_date: str = None
    new_clock: str = None
    new_title: str = None


# Implement the alarm function
def set_alarm(alarm_info: SetAlarmInput) -> str:
    # Construct the alarm data
    alarm_data = {
        "day": alarm_info.day,
        "date": alarm_info.date,
        "clock": alarm_info.clock,
        "title": alarm_info.title  
    }

    # Push the alarm data to Firebase
    db.reference(f'/users/{st.session_state.email.replace(".", "_")}/alarms').push(alarm_data)

    return "Alarm set successfully."


def delete_alarm(alarm_info: SetAlarmInput) -> str:
    # Get the user's email
    user_email = st.session_state.email.replace(".", "_")

    # Query Firebase for alarms matching the given properties
    alarms_ref = db.reference(f'/users/{user_email}/alarms')
    alarms_to_delete = alarms_ref.get()

    # Filter alarms based on day
    if alarm_info.day:
        alarms_to_delete = {alarm_id: alarm_data for alarm_id, alarm_data in alarms_to_delete.items() if alarm_data.get('day') == alarm_info.day}

    # Filter alarms based on date
    if alarm_info.date:
        alarms_to_delete = {alarm_id: alarm_data for alarm_id, alarm_data in alarms_to_delete.items() if alarm_data.get('date') == alarm_info.date}

    # Filter alarms based on clock
    if alarm_info.clock:
        alarms_to_delete = {alarm_id: alarm_data for alarm_id, alarm_data in alarms_to_delete.items() if alarm_data.get('clock') == alarm_info.clock}

    # Filter alarms based on title
    if alarm_info.title:
        alarms_to_delete = {alarm_id: alarm_data for alarm_id, alarm_data in alarms_to_delete.items() if alarm_data.get('title') == alarm_info.title}

    # Check if any alarms match the given properties
    if alarms_to_delete:
        # Iterate over the matching alarms and delete them
        for alarm_id in alarms_to_delete.keys():
            alarms_ref.child(alarm_id).delete()
        
        return "Alarms matching the specified properties deleted successfully."
    else:
        return "No alarms found matching the specified properties."


def modify_alarm(args: ModifyAlarmArgs) -> str:
    # Get the user's email
    user_email = st.session_state.email.replace(".", "_")

    # Query Firebase for all alarms
    alarms_ref = db.reference(f'/users/{user_email}/alarms')
    alarms_to_modify = alarms_ref.get()

    # Filter alarms based on day
    if args.existing_day:
        alarms_to_modify = {alarm_id: alarm_data for alarm_id, alarm_data in alarms_to_modify.items() if alarm_data.get('day') == args.existing_day}

    # Filter alarms based on date
    if args.existing_date:
        alarms_to_modify = {alarm_id: alarm_data for alarm_id, alarm_data in alarms_to_modify.items() if alarm_data.get('date') == args.existing_date}

    # Filter alarms based on clock
    if args.existing_clock:
        alarms_to_modify = {alarm_id: alarm_data for alarm_id, alarm_data in alarms_to_modify.items() if alarm_data.get('clock') == args.existing_clock}

    # Filter alarms based on title
    if args.existing_title:
        alarms_to_modify = {alarm_id: alarm_data for alarm_id, alarm_data in alarms_to_modify.items() if alarm_data.get('title') == args.existing_title}

    # Check if any alarms match the given properties
    if alarms_to_modify:
        # Iterate over the matching alarms and modify them
        for alarm_id, alarm_data in alarms_to_modify.items():  
            # Update the alarm day if new day is provided
            if args.new_day is not None:
                alarms_ref.child(alarm_id).update({"day": args.new_day})

            # Update the alarm date if new date is provided
            if args.new_date is not None:
                alarms_ref.child(alarm_id).update({"date": args.new_date})

            # Update the alarm clock if new clock is provided
            if args.new_clock is not None:
                alarms_ref.child(alarm_id).update({"clock": args.new_clock})

            # Update the alarm title if new title is provided
            if args.new_title is not None:
                alarms_ref.child(alarm_id).update({"title": args.new_title})
            
        return "Alarms matching the specified properties modified successfully."
    else:
        return "No alarms found matching the specified properties."


def list_user_alarms():
    # Query Firebase for user alarms
    user_email = st.session_state.email.replace(".", "_")
    alarms_ref = db.reference(f'/users/{user_email}/alarms')
    alarms = alarms_ref.get()

    user_alarms = []

    if alarms:
        for key, value in alarms.items():
            user_alarms.append({
                "id": key,
                "day": value.get("day"),
                "date": value.get("date"),
                "clock": value.get("clock"),
                "title": value.get("title")
            })

    return user_alarms



def check_and_notify_alarms(email):
    while True:
        # Get the current time
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        # Query Firebase for alarms
        user_email = email.replace(".", "_")
        alarms_ref = db.reference(f'/users/{user_email}/alarms')
        alarms = alarms_ref.order_by_key().end_at(current_time).get()

        # Print available alarms
        if alarms:
            print("Available alarms:")
            for key, value in alarms.items():
                print(f"Alarm ID: {key}, Time: {value['clock']}, Day: {value['day']}, Date: {value['date']}")

        # If there are any alarms that have passed, notify and remove them
        if alarms:
            engine = pyttsx3.init()

            for key, value in alarms.items():
                alarm_time_str = f"{value['date']} {value['clock']}"
                try:
                    alarm_time = datetime.datetime.strptime(alarm_time_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    alarm_time = datetime.datetime.strptime(alarm_time_str, "%Y-%m-%d %H:%M")
                    
                alarm_time_formatted = alarm_time.strftime("%Y-%m-%d %H:%M")
                
                print(alarm_time_formatted)
                if alarm_time_formatted <= current_time:
                    engine.say(f"Alarm at {value['clock']} on {value['day']}, {value['date']} has passed.")
                    print(f"Alarm at {value['clock']} on {value['day']}, {value['date']} has passed.")
                    alarms_ref.child(key).delete()
                else:
                    print(f"Alarm {alarm_time} is still pending.")
            
            engine.runAndWait()


            # Check if the engine is already running
            if not engine.isBusy():
                # Start the engine to process the speech synthesis tasks
                engine.runAndWait()

        # Wait for some time before checking again (e.g., every 60 seconds)
        time.sleep(60)