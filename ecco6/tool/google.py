import base64
import json
import re
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Dict, List
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from langchain.pydantic_v1 import BaseModel, Field
from tzlocal import get_localzone
from difflib import SequenceMatcher

#================== CALENDAR ==================================

class GetEventsByDateInput(BaseModel):
    date: str = Field(description="The date in YYYY-MM-DD format.")

def get_events_by_date(date: str, google_credentials) -> str:
    split_date = date.split('-')

    event_date = datetime(
        int(split_date[0]),  # YYYY
        int(split_date[1]),  # MM
        int(split_date[2]),  # DD
        00,  # HH
        00,  # MM
        00,  # SS
        0,
        tzinfo=get_localzone()
    ).isoformat()

    end_time = datetime(
        int(split_date[0]),
        int(split_date[1]),
        int(split_date[2]),
        23,
        59,
        59,
        999999,
        tzinfo=get_localzone()
    ).isoformat()

    service = build("calendar", "v3", credentials=google_credentials)
    events_result = service.events().list(calendarId='primary', timeMin=event_date,timeMax=end_time).execute()
    all_events = events_result.get('items', [])
    return '\n'.join(
        [json.dumps({key: event[key] for key in ["summary", "start", "end"]})
         for event in all_events]
    )


class AddEventInput(BaseModel):
    title: str = Field(description="The title of the event.")
    start_time: str = Field(description="The start datetime of the event, in the format of YYYY-MM-DDTHH:MM:SS.")
    end_time: str = Field(description="The end datetime of the event, in the format of YYYY-MM-DDTHH:MM:SS.")

def add_event(title: str, start_time: str, end_time: str, google_credentials) -> str:
    service = build("calendar", "v3", credentials=google_credentials)

    timezone = str(get_localzone())

    event = {
        'summary': title,
        'start': {
            'dateTime': start_time,
            'timeZone': timezone,
        },
        'end': {
            'dateTime': end_time,
            'timeZone': timezone,
        },
    }

    event = service.events().insert(calendarId='primary', body=event).execute()


class RemoveEventInput(BaseModel):
    event_title: str = Field(description="The title of the event.")
    date: str = Field(description="The date in YYYY-MM-DD format.")


def get_eventID(date: str, google_credentials, event_title: str) -> str:
    split_date = date.split('-')

    event_date = datetime(
        int(split_date[0]),  
        int(split_date[1]), 
        int(split_date[2]),
        00,  
        00,
        00,
        0,
        tzinfo=get_localzone()
    ).isoformat()

    end_time = datetime(
        int(split_date[0]),
        int(split_date[1]),
        int(split_date[2]),
        23,
        59,
        59,
        999999,
        tzinfo=get_localzone()
    ).isoformat()

    service = build("calendar", "v3", credentials=google_credentials)
    events_result = service.events().list(calendarId='primary', timeMin=event_date, timeMax=end_time).execute()
    all_events = events_result.get('items', [])
    
    event_ids = []

    for event in all_events:
        if 'summary' in event and event['summary'].lower() == event_title.lower():
            event_ids.append(event['id'])

    if event_ids:
        return event_ids[0]
    else:
        return None


def remove_event(event_title: str, date: str, google_credentials) -> str:
    event_id = get_eventID(date, google_credentials, event_title)
    
    if event_id:
        try:
            service = build("calendar", "v3", credentials=google_credentials)
            service.events().delete(calendarId='primary', eventId=event_id).execute()
            return f"Event '{event_title}' deleted successfully"
        except Exception as e:
            return f"An error occurred while deleting event '{event_title}': {str(e)}"
    else:
        return f"No event with title '{event_title}' found for the specified date"


class GetUnreadMessagesInput(BaseModel):
    pass 


#======================= GMAIL =======================

def get_unread_messages(google_credentials) -> str:
    creds = google_credentials
    service = build('gmail', 'v1', credentials=creds)

    query = 'in:inbox is:unread -category:(promotions OR social)'
    unread_msgs = service.users().messages().list(userId='me', q=query).execute()

    messages = unread_msgs.get('messages', [])
    if not messages:
        return "You have no unread messages in your primary inbox."

    unread_info = ""
    for msg in messages:
        msg_info = service.users().messages().get(userId='me', id=msg['id']).execute()
        headers = msg_info['payload']['headers']
        sender = next((header['value'] for header in headers if header['name'] == 'From'), 'Unknown')
        subject = next((header['value'] for header in headers if header['name'] == 'Subject'), 'No Subject')
        snippet = msg_info['snippet']
        unread_info += f"From: {sender}\nSubject: {subject}\nSnippet: {snippet}\n\n"

    return unread_info


class SendEmailInput(BaseModel):
    recipient: str = Field(description="The email address of the recipient.")
    subject: str = Field(description="The subject of the email.")
    body: str = Field(description="The body of the email.")


def preprocess_recipient(recipient: str) -> str:
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

    matches = re.findall(email_pattern, recipient)

    for match in matches:
        recipient = recipient.replace(match, match.replace(" at ", "@").replace(" dot ", "."))

    return recipient


def send_email(recipient: str, subject: str, body: str, google_credentials) -> str:
    recipient = preprocess_recipient(recipient)

    email_msg = EmailMessage()
    email_msg['To'] = recipient
    email_msg['Subject'] = subject
    email_msg.set_content(body)

    try:
        service = build('gmail', 'v1', credentials=google_credentials)
        message = {'raw': base64.urlsafe_b64encode(email_msg.as_bytes()).decode()}
        sent_message = service.users().messages().send(userId='me', body=message).execute()

        return "Email sent successfully!"
    except Exception as e:
        return f"An error occurred while sending the email: {str(e)}"

# ===================== TASKS ====================================

class ListTaskListsInput(BaseModel):
    pass


def list_task_lists(google_credentials) -> List[str]:
    service = build("tasks", "v1", credentials=google_credentials)
    task_lists = service.tasklists().list(maxResults=10).execute()
    items = task_lists.get("items", [])
    return [item["title"] for item in items]


class CreateTaskListInput(BaseModel):
    name: str = Field(description="The name of the new task list.")


def create_taskList(google_credentials, name: str) -> Dict:
    try:
        service = build("tasks", "v1", credentials=google_credentials)
        
        new_task_list = service.tasklists().insert(body={"title": name}).execute()
        
        return new_task_list
    except HttpError as err:
        return {"error": f"HTTP Error: {err}"}
    except Exception as e:
        return {"error": f"An error occurred: {e}"}


class ListTasksInListInput(BaseModel):
    task_list_name: str = Field(description="The name of the task list to list tasks from.")


def list_tasks_in_list(task_list_name: str, google_credentials) -> List[str]:
    try:
        service = build("tasks", "v1", credentials=google_credentials)
        task_lists = service.tasklists().list(maxResults=10).execute()
        items = task_lists.get("items", [])
        
        for item in items:
            if item["title"].lower() == task_list_name.lower():
                task_list_id = item["id"]
                break
        else:
            return f"No task list found with the name '{task_list_name}'"
        
        tasks = service.tasks().list(tasklist=task_list_id).execute()
        task_items = tasks.get("items", [])
        
        if not task_items:
            return f"No tasks found in the '{task_list_name}' task list"
        
        task_titles = [task["title"] for task in task_items]
        
        return task_titles
    except HttpError as err:
        return {"error": f"HTTP Error: {err}"}
    except Exception as e:
        return {"error": f"An error occurred: {e}"}


class AddTaskInput(BaseModel):
    task_name: str = Field(description="The name of the task to add.")
    task_list_name: str = Field(description="The name of the task list to add the task to.")


def add_task(task_name: str, task_list_name: str, google_credentials) -> str:
    try:
        service = build("tasks", "v1", credentials=google_credentials)
        
        task_lists = service.tasklists().list(maxResults=10).execute()
        items = task_lists.get("items", [])
        
        for item in items:
            if item["title"].lower() == task_list_name.lower():
                task_list_id = item["id"]
                break
        else:
            return f"No task list found with the name '{task_list_name}'"
        
        task = {
            'title': task_name,
        }
        
        service.tasks().insert(tasklist=task_list_id, body=task).execute()
        
        return f"Task '{task_name}' added successfully to the '{task_list_name}' task list"
    except HttpError as err:
        return f"HTTP Error: {err}"
    except Exception as e:
        return f"An error occurred: {e}"

class RemoveTaskListInput(BaseModel):
    task_list_name: str = Field(description="The name of the task list to remove the task.")

def remove_task_list(task_list_name: str, google_credentials) -> str:
    service = build("tasks", "v1", credentials=google_credentials)

    task_lists = service.tasklists().list(maxResults=10).execute()
    items = task_lists.get("items", [])

    task_list_id = None
    for item in items:
        if SequenceMatcher(None, item["title"].lower(), task_list_name.lower()).ratio() > 0.9:
            task_list_id = item["id"]
            service.tasklists().delete(tasklist=task_list_id).execute()
            return f'The {task_list_name} list has been succefully removed.'
       
    if task_list_id is None:
        return f'No task list found with the name "{task_list_name}"'
    

class RemoveTaskInput(BaseModel):
    task_list_name: str = Field(description="The name of the task list to remove the task.")
    task_name: str = Field(description="The name of the task under the task list to remove.")


def remove_task(task_list_name: str, task_name: str, google_credentials) -> str:
    service = build("tasks", "v1", credentials=google_credentials)

    task_lists = service.tasklists().list(maxResults=10).execute()
    items = task_lists.get("items", [])

    task_list_id = None
    for item in items:
        if SequenceMatcher(None, item["title"].lower(), task_list_name.lower()).ratio() > 0.9:
            task_list_id = item["id"]
            break
       
    if task_list_id is None:
        return f'No task list found with the name "{task_list_name}"'
    
    tasks = service.tasks().list(tasklist=task_list_id).execute()
    items = tasks.get("items", [])
    for item in items:
        if SequenceMatcher(None, item["title"].lower(), task_name.lower()).ratio() > 0.9:
            service.tasks().delete(tasklist=task_list_id, task=item["id"]).execute()
            return f'{task_name} under task list {task_list_name} has been succefully removed.'
        
    return f'Could not find {task_name} under task list {task_list_name}'

# ===================== DOCS ====================================

class CreateDocumnetInput(BaseModel):
    name: str = Field(description="The name of the new document.")

def create_document(google_credentials, name: str) -> Dict:
    try:
        service = build("docs", "v1", credentials=google_credentials)
        
        new_doc = service.documents().create(body={"title": name}).execute()
        
        return new_doc
    except HttpError as err:
        return {"error": f"HTTP Error: {err}"}
    except Exception as e:
        return {"error": f"An error occurred: {e}"}
    
class InsertTextInput(BaseModel):
    text: str = Field(description="The text to be inserted.")
    document_name: str = Field(description="The name of the document.")

def get_document_id(google_credentials, document_name: str) -> str:
    SCOPES = ['https://www.googleapis.com/auth/drive']

    service = build('drive', 'v3', credentials=google_credentials)

    results = service.files().list(q=f"name='{document_name}' and mimeType='application/vnd.google-apps.document'",
                                    fields="files(id)").execute()
    items = results.get('files', [])

    if items:
        return items[0]['id']
    else:
        return None
    
def insert_text(google_credentials, text: str, document_name: str) -> Dict:
    try:
        document_id = get_document_id(google_credentials, document_name)

        if document_id:
            requests = [
                {
                    'insertText': {
                        'location': {
                            'index': 1,
                        },
                        'text': text
                    }
                }
            ]

            service = build("docs", "v1", credentials=google_credentials)
            result = service.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()
            return result
        else:
            return {"error": f"Document '{document_name}' not found."}
    except HttpError as err:
        return {"error": f"HTTP Error: {err}"}
    except Exception as e:
        return {"error": f"An error occurred: {e}"}