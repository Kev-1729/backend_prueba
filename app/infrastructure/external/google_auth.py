# app/infrastructure/external/google_auth.py
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import config # Usamos el config.py del root

def get_google_credentials():
    """
    Carga las credenciales desde token.json.
    """
    creds = None
    if not os.path.exists(config.TOKEN_FILE):
        raise FileNotFoundError(f"El archivo '{config.TOKEN_FILE}' no se encontró.")

    creds = Credentials.from_authorized_user_file(config.TOKEN_FILE, config.SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    
    return creds