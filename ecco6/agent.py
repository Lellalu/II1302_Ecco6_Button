import functools
from typing import Mapping, Sequence, Tuple

import streamlit as st
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools import StructuredTool
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from ecco6.tool import google, location, time, weather, rpi_timer, news, sl, alarm, light

SYS_PROMPT = """\
You are a voice assistant named Ecco6. Your task is to handle questions and
request from users. You have access to various tools and you must call them
if they helps you handle the request from the user. You will also have access
to their calendar, gmail and tasks as function calling if possible. You can get real-time information, 
local information by calling functions. You can also set timer and alarms for users. You have access 
to smart light as well. Do not make up answer or the question and request that you do not know or 
if the tools does not provide information to answer that question.
In the Google Task, we can create multiple task lists, and each task list can contain multiple tasks.
"""


class Ecco6Agent:
  def __init__(
    self, openai_api_key: str, google_credentials, rpi_url, chat_model: str = "gpt-4-turbo"):
    self.google_credentials = google_credentials
    self.rpi_url = rpi_url
    llm = ChatOpenAI(model=chat_model, api_key=openai_api_key)
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYS_PROMPT),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    tools = self._create_tools()
    #tools = self._create_dummy_tools()
    agent = create_tool_calling_agent(llm, tools, prompt)
    self.agent_executor = AgentExecutor(
       agent=agent, tools=tools, verbose=True)
    
  def _create_dummy_tools(self):
    dummy_tool = StructuredTool.from_function(
        func=lambda x: "Hello world",
        name="hello_world",
        description='Returns "Hellow world" as a string.',
    )
    return [dummy_tool]
    
  def _create_tools(self):
    tools = []
    if self.google_credentials is not None:
      get_events_by_date_tool = StructuredTool.from_function(
          func=functools.partial(
            google.get_events_by_date, google_credentials=self.google_credentials),
          name="get_events_by_date",
          description="Get all events of a day from Google calendar.",
          args_schema=google.GetEventsByDateInput,
      )
      tools.append(get_events_by_date_tool)

    get_current_time_tool = StructuredTool.from_function(
        func=time.get_current_time,
        name="get_current_time",
        description="Get the current date, time and the week day name."
    )
    tools.append(get_current_time_tool)
    
    add_event_tool = StructuredTool.from_function(
        func=functools.partial(
        google.add_event, google_credentials=self.google_credentials),
        name="add_event",
        description="Add an event to the Google calendar.",
        args_schema=google.AddEventInput,
    )
    tools.append(add_event_tool)

    remove_event_tool = StructuredTool.from_function(
        func=functools.partial(
            google.remove_event, google_credentials=self.google_credentials),
        name="remove_event",
        description="Remove an event from the Google calendar.",
        args_schema=google.RemoveEventInput,
    )
    tools.append(remove_event_tool)

    get_unread_messages_tool = StructuredTool.from_function(
          func=functools.partial(google.get_unread_messages, google_credentials=self.google_credentials),
          name="get_unread_messages",
          description="Retrieve unread messages from Gmail.",
          args_schema=google.GetUnreadMessagesInput,
    )
    tools.append(get_unread_messages_tool)
    
    send_email_tool = StructuredTool.from_function(
        func=functools.partial(google.send_email, google_credentials=self.google_credentials),
        name="send_email",
        description="Send an email via Gmail.",
        args_schema=google.SendEmailInput,
    )
    tools.append(send_email_tool)

    list_task_lists_tool = StructuredTool.from_function(
        func=functools.partial(google.list_task_lists, google_credentials=self.google_credentials),
        name="list_task_lists",
        description="List all task lists from Google Tasks.",
        args_schema=google.ListTaskListsInput,
    )
    tools.append(list_task_lists_tool)
    
    create_taskList_tool = StructuredTool.from_function(
        func=functools.partial(google.create_taskList, google_credentials=self.google_credentials),
        name="create_taskList",
        description="Create a new task list in Google Tasks.",
        args_schema=google.CreateTaskListInput,
    )
    tools.append(create_taskList_tool)

    list_tasks_in_list_tool = StructuredTool.from_function(
        func=functools.partial(
        google.list_tasks_in_list, google_credentials=self.google_credentials),
        name="list_tasks_in_list",
        description="List all tasks in a specified task list from Google Tasks.",
        args_schema=google.ListTasksInListInput,
    )
    tools.append(list_tasks_in_list_tool)

    add_task_tool = StructuredTool.from_function(
        func=functools.partial(
        google.add_task, google_credentials=self.google_credentials),
        name="add_task",
        description="Add a task to a specified task list in Google Tasks.",
        args_schema=google.AddTaskInput,
    )
    tools.append(add_task_tool)

    remove_task_list_tool = StructuredTool.from_function(
        func=functools.partial(
        google.remove_task_list, google_credentials=self.google_credentials),
        name="remove_task_list",
        description="Remove the entire task list in Google Tasks.",
        args_schema=google.RemoveTaskListInput,
    )
    tools.append(remove_task_list_tool)

    remove_task_tool = StructuredTool.from_function(
        func=functools.partial(
        google.remove_task, google_credentials=self.google_credentials),
        name="remove_task",
        description="Remove a task from a specified task list in Google Tasks.",
        args_schema=google.RemoveTaskInput,
    )
    tools.append(remove_task_tool)
    
    if "latitude" in st.session_state and "longitude" in st.session_state:
      get_current_location_tool = StructuredTool.from_function(
          func=lambda x: location.get_current_location(latitude=st.session_state.latitude, longitude=st.session_state.longitude),
          name="get_current_location",
          description="Get my current location.",
      )
      tools.append(get_current_location_tool)
    
    get_news_tool = StructuredTool.from_function(
    func=news.get_top_headlines,
    name="get_top_headlines",
    description="Get the top headlines news from various sources."
    )
    tools.append(get_news_tool)

    get_weather_tool = StructuredTool.from_function(
        func=lambda city_name,date=None: weather.get_weather(weather.WeatherInput(city_name=city_name,date=date)),
        name="get_weather",
        description="Get the current weather for a specified city.",
        args_schema=weather.WeatherInput,
    )
    tools.append(get_weather_tool)

    set_alarm_tool = StructuredTool.from_function(
        func=lambda day, date, clock, title=None: alarm.set_alarm(alarm.SetAlarmInput(day=day, date=date, clock=clock, title=title)),
        name="set_alarm",
        description="Set an alarm for a specified time.",
        args_schema=alarm.SetAlarmInput,
    )
    tools.append(set_alarm_tool)

    remove_alarm_tool = StructuredTool.from_function(
        func=lambda day, date, clock, title=None: alarm.delete_alarm(alarm.SetAlarmInput(day=day, date=date, clock=clock, title=title)),
        name="remove_alarm",
        description="Remove an alarm of a specified time.",
        args_schema=alarm.SetAlarmInput,
    )
    tools.append(remove_alarm_tool)

    get_alarm_tool = StructuredTool.from_function(
        func=alarm.list_user_alarms,
        name="get_alarms",
        description="Get the users alarms",
    )
    tools.append(get_alarm_tool)

    modify_alarm_tool = StructuredTool.from_function(
        func=lambda existing_day, existing_date, existing_clock, existing_title=None, new_day=None, new_date=None, new_clock=None, new_title=None: alarm.modify_alarm(alarm.ModifyAlarmArgs(existing_day=existing_day,existing_date=existing_date,existing_clock=existing_clock,existing_title=existing_title,new_day=new_day,new_date=new_date,new_clock=new_clock,new_title=new_title)),
        name="modify_alarm",
        description="Modify an existing alarm with new information.",
        args_schema=alarm.ModifyAlarmArgs, 
    )
    tools.append(modify_alarm_tool)

    if self.rpi_url is not None:
      set_rpi_timer_tool = StructuredTool.from_function(
          func=functools.partial(rpi_timer.set_rpi_timer, url=self.rpi_url),
          name="set_rpi_timer",
          description="Set an timer/countdown by given time.",
          args_schema=rpi_timer.SetRpiTimerInput,
      )
      tools.append(set_rpi_timer_tool)

    turn_on_light_tool = StructuredTool.from_function(
        func=functools.partial(
          light.turn_on_light, 
          url=st.secrets["LIGHT"]["URL"]+"/api/services/script/turn_on_bulb",
          token = st.secrets["LIGHT"]["API_KEY"]
        ),
        name="turn_on_light",
        description="Turn on the light.",
        args_schema=light.SetLightInput,
    )
    tools.append(turn_on_light_tool)

    turn_off_light_tool = StructuredTool.from_function(
        func=functools.partial(
          light.turn_off_light,
          url=st.secrets["LIGHT"]["URL"]+"/api/services/script/turn_off_bulb",
          token=st.secrets["LIGHT"]["API_KEY"]
        ),
        name="turn_off_light",
        description="Turn off the light.",
        args_schema=light.SetLightInput,
    )
    tools.append(turn_off_light_tool)

    set_brightness_low_tool = StructuredTool.from_function(
        func=functools.partial(
          light.set_brightness_low, 
          url=st.secrets["LIGHT"]["URL"]+"/api/services/script/set_brightness_low",
          token = st.secrets["LIGHT"]["API_KEY"]
        ),
        name="set_brightness_low",
        description="Set the brightness of the light as low.",
        args_schema=light.SetLightInput,
    )
    tools.append(set_brightness_low_tool)

    set_brightness_medium_tool = StructuredTool.from_function(
        func=functools.partial(
          light.set_brightness_medium, 
          url=st.secrets["LIGHT"]["URL"]+"/api/services/script/set_brightness_medium",
          token = st.secrets["LIGHT"]["API_KEY"]
        ),
        name="set_brightness_medium",
        description="Set the brightness of the light as medium.",
        args_schema=light.SetLightInput,
    )
    tools.append(set_brightness_medium_tool)

    set_brightness_high_tool = StructuredTool.from_function(
        func=functools.partial(
          light.set_brightness_high, 
          url=st.secrets["LIGHT"]["URL"]+"/api/services/script/set_brightness_high",
          token = st.secrets["LIGHT"]["API_KEY"]
        ),
        name="set_brightness_high",
        description="Set the brightness of the light as high.",
        args_schema=light.SetLightInput,
    )
    tools.append(set_brightness_high_tool)
    
    get_travel_suggestions_tool = StructuredTool.from_function(
        func=sl.get_travel_suggestions,
        name="get_travel_suggestions",
        description="Get travel suggestions for a specific journey.",
        args_schema=sl.GetTravelSuggestionsInput,
    )
    tools.append(get_travel_suggestions_tool)
    
    get_nearby_stops_tool = StructuredTool.from_function(
        func=sl.get_nearby_stops,
        name="get_nearby_stops",
        description="Get nearby stops based on current location.",
        args_schema=sl.GetNearbyStopsInput,
    )
    tools.append(get_nearby_stops_tool)

    create_document_tool = StructuredTool.from_function(
        func=functools.partial(
        google.create_document, google_credentials=self.google_credentials),
        name="create_document",
        description="Create a new Google Docs document.",
        args_schema=google.CreateDocumnetInput,
    )
    tools.append(create_document_tool)

    insert_text_tool = StructuredTool.from_function(
        func=functools.partial(google.insert_text, google_credentials=self.google_credentials),
        name="insert_text",
        description="Insert text into a Google Docs document.",
        args_schema=google.InsertTextInput,
    )
    tools.append(insert_text_tool)
    return tools
  
  
  def chat_completion(self, messages: Sequence[Mapping[str, str]]) -> str:
    chat_history = []
    for message in messages[:-1]:
      if message["role"] == "user":
        chat_history.append(HumanMessage(content=message["content"]))
      else:
        chat_history.append(AIMessage(content=message["content"]))
    
    result = self.agent_executor.invoke({
      "chat_history": chat_history,
      "input": messages[-1]["content"],
    })
    return result["output"]

