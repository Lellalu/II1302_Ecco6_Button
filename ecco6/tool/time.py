import calendar
import datetime


def get_current_time() -> str:
    date = datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S')
    day_name = calendar.day_name[datetime.date.today().weekday()] 
    return f'{day_name} {date}'
