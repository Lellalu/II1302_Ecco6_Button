import logging

from ecco6.views.homepage_view import homepage_view
from ecco6.views.login_view import login_view

from ecco6.tool import alarm
from ecco6 import util
import threading


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

def main():
  if not util.is_login():
    login_view()
  else:
    #user_email = st.session_state.email 
    #alarm_thread = threading.Thread(target=alarm.check_and_notify_alarms, args=(user_email,))
    #alarm_thread.start()
    homepage_view()
    
if __name__ == "__main__":
    main()