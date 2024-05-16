import asyncio
import json
import logging
import webbrowser

import firebase_admin
import requests
import streamlit as st
from firebase_admin import auth, credentials, exceptions, initialize_app
from httpx_oauth.clients.google import GoogleOAuth2
from streamlit_cookies_controller import CookieController

from firebase_admin import credentials, db

firebase_credentials = {
    "type": st.secrets["FIREBASE"]["TYPE"],
    "project_id": st.secrets["FIREBASE"]["PROJECT_ID"],
    "private_key_id": st.secrets["FIREBASE"]["PRIVATE_KEY_ID"],
    "private_key": st.secrets["FIREBASE"]["PRIVATE_KEY"].replace('\\n', '\n'),
    "client_email": st.secrets["FIREBASE"]["CLIENT_EMAIL"],
    "client_id": st.secrets["FIREBASE"]["CLIENT_ID"],
    "auth_uri": st.secrets["FIREBASE"]["AUTH_URI"],
    "token_uri": st.secrets["FIREBASE"]["TOKEN_URI"],
    "auth_provider_x509_cert_url": st.secrets["FIREBASE"]["AUTH_PROVIDER_X509_CERT_URL"],
    "client_x509_cert_url": st.secrets["FIREBASE"]["CLIENT_X509_CERT_URL"]
}

# Initialize Firebase app with the provided credentials and database URL
cred = credentials.Certificate(firebase_credentials)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://ecco6-803de-default-rtdb.europe-west1.firebasedatabase.app/'
})

# Check if the default app instance exists
if firebase_admin.get_app():
    # Access the default app instance
    default_app = firebase_admin.get_app()

    # Print information about the default app instance
    print("Firebase app initialized successfully.")
    print("Project ID:", default_app.project_id)
    print("Database URL:", default_app.options.get('databaseURL'))
else:
    print("Error: Firebase app initialization failed.")

## -------------------------------------------------------------------------------------------------
## Firebase Auth API -------------------------------------------------------------------------------
## -------------------------------------------------------------------------------------------------
def add_user_email_to_firebase(email):
    ref = db.reference('/logged_in_users')
    ref.push(email)

# Function to remove user email from Firebase on logout
def remove_user_email_from_firebase(email):
    ref = db.reference('/logged_in_users')
    data = ref.get()
    for user_id in data:
        if data[user_id] == email:
            ref.child(user_id).delete()

def sign_in_with_email_and_password(email, password):
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key={0}".format(st.secrets['FIREBASE_WEB_API_KEY'])
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"email": email, "password": password, "returnSecureToken": True})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def get_account_info(id_token):
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/getAccountInfo?key={0}".format(st.secrets['FIREBASE_WEB_API_KEY'])
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"idToken": id_token})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def send_email_verification(id_token):
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/getOobConfirmationCode?key={0}".format(st.secrets['FIREBASE_WEB_API_KEY'])
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"requestType": "VERIFY_EMAIL", "idToken": id_token})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def send_password_reset_email(email):
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/getOobConfirmationCode?key={0}".format(st.secrets['FIREBASE_WEB_API_KEY'])
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"requestType": "PASSWORD_RESET", "email": email})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def create_user_with_email_and_password(email, password):
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/signupNewUser?key={0}".format(st.secrets['FIREBASE_WEB_API_KEY'])
    headers = {"content-type": "application/json; charset=UTF-8" }
    data = json.dumps({"email": email, "password": password, "returnSecureToken": True})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def delete_user_account(id_token):
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/deleteAccount?key={0}".format(st.secrets['FIREBASE_WEB_API_KEY'])
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"idToken": id_token})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def raise_detailed_error(request_object):
    try:
        request_object.raise_for_status()
    except requests.exceptions.HTTPError as error:
        raise requests.exceptions.HTTPError(error, request_object.text)

## -------------------------------------------------------------------------------------------------
## Authentication functions ------------------------------------------------------------------------
## -------------------------------------------------------------------------------------------------

# Initialize Google OAuth2 client
client_id = st.secrets["GOOGLE_AUTH"]["CLIENT_ID"] 
client_secret = st.secrets["GOOGLE_AUTH"]["CLIENT_SECRET"]
redirect_url = "http://localhost:8501"  # Your redirect URL

client = GoogleOAuth2(client_id=client_id, client_secret=client_secret)

#@st.cache(allow_output_mutation=True)
#def get_session_state():
#    return {'user_email': None}


#session_state = get_session_state()


def sign_in(email:str, password:str) -> None:
    try:
        # Attempt to sign in with email and password
        id_token = sign_in_with_email_and_password(email,password)['idToken']

        # Get account information
        user_info = get_account_info(id_token)["users"][0]

        # If email is not verified, send verification email and do not sign in
        if not user_info["emailVerified"]:
            send_email_verification(id_token)
            st.session_state.auth_warning = 'Check your email to verify your account'

        # Save user info to session state and rerun
        else:
            st.session_state.user_info = user_info
            st.session_state.email = email
            controller = CookieController()
            controller.set('ecco6_login_email', email)
            add_user_email_to_firebase(email)
            st.experimental_rerun()

    except requests.exceptions.HTTPError as error:
        error_message = json.loads(error.args[1])['error']['message']
        if error_message in {"INVALID_EMAIL","EMAIL_NOT_FOUND","INVALID_PASSWORD","MISSING_PASSWORD"}:
            st.session_state.auth_warning = 'Error: Use a valid email and password'
        else:
            st.session_state.auth_warning = 'Error: Please try again later'
        logging.warning(error_message)
    except Exception as error:
        logging.warning(error)
        st.session_state.auth_warning = 'Error: Please try again later'


def create_account(email:str, password:str) -> None:
    try:
        # Create account (and save id_token)
        id_token = create_user_with_email_and_password(email,password)['idToken']

        # Create account and send email verification
        send_email_verification(id_token)
        st.session_state.auth_success = 'Check your inbox to verify your email'
    
    except requests.exceptions.HTTPError as error:
        error_message = json.loads(error.args[1])['error']['message']
        if error_message == "EMAIL_EXISTS":
            st.session_state.auth_warning = 'Error: Email belongs to existing account'
        elif error_message in {"INVALID_EMAIL","INVALID_PASSWORD","MISSING_PASSWORD","MISSING_EMAIL","WEAK_PASSWORD"}:
            st.session_state.auth_warning = 'Error: Use a valid email and password'
        else:
            st.session_state.auth_warning = 'Error: Please try again later'
    
    except Exception as error:
        print(error)
        st.session_state.auth_warning = 'Error: Please try again later'


def reset_password(email:str) -> None:
    try:
        send_password_reset_email(email)
        st.session_state.auth_success = 'Password reset link sent to your email'
    
    except requests.exceptions.HTTPError as error:
        error_message = json.loads(error.args[1])['error']['message']
        if error_message in {"MISSING_EMAIL","INVALID_EMAIL","EMAIL_NOT_FOUND"}:
            st.session_state.auth_warning = 'Error: Use a valid email'
        else:
            st.session_state.auth_warning = 'Error: Please try again later'    
    
    except Exception:
        st.session_state.auth_warning = 'Error: Please try again later'


def sign_out() -> None:
    remove_user_email_from_firebase(st.session_state.email)
    controller = CookieController()
    controller.remove('ecco6_login_email')
    st.session_state.clear()
    st.session_state.auth_success = 'You have successfully signed out'


def delete_account(password:str) -> None:
    try:
        # Confirm email and password by signing in (and save id_token)
        id_token = sign_in_with_email_and_password(st.session_state.user_info['email'],password)['idToken']
        
        # Attempt to delete account
        delete_user_account(id_token)
        st.session_state.clear()
        st.session_state.auth_success = 'You have successfully deleted your account'

    except requests.exceptions.HTTPError as error:
        error_message = json.loads(error.args[1])['error']['message']
        print(error_message)

    except Exception as error:
        print(error)


async def get_access_token(client: GoogleOAuth2, redirect_url: str, code: str):
    logging.info("Getting access token...")  
    return await client.get_access_token(code, redirect_url)

async def get_email(client: GoogleOAuth2, token: str):
    logging.info("Getting user email...")  
    user_id, user_email = await client.get_id_email(token)
    return user_id, user_email

def get_logged_in_user_email():
    try:
        code = st.query_params.get('code')  # Remove the parentheses
        if code:
            print("Received authorization code:", code)
            token = asyncio.run(get_access_token(client, redirect_url, code))
            print("Received access token:", token)
            st.session_state.google_auth_code = code  # Set google_auth_code in session state
            st.query_params.clear()

            if token:
                user_id, user_email = asyncio.run(get_email(client, token['access_token']))
                print("Received user email:", user_email)
                if user_email:
                    try:
                        user = auth.get_user_by_email(user_email)
                    except exceptions.FirebaseError:
                        user = auth.create_user(email=user_email)
                    st.session_state.email = user.email
                    print("Received user email:", st.session_state.email)
                    #session_state['user_email'] = user.email
                    add_user_email_to_firebase(st.session_state.email)
                    st.session_state.user_info = {"user_id": user.uid, "user_email": user.email}  # Set user_info in session state
                    return user.email
        return None
    except Exception as e:
        print("Error in get_logged_in_user_email:", e)
        pass