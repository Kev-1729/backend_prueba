# config.py

# --- CONFIGURACIÓN DE GOOGLE ---
# ID de la carpeta principal en Google Drive
DRIVE_PARENT_FOLDER_ID = '1F2qZ_0J-8poaScZDXLXkVmpojwUQzuLm'

# Alcances requeridos por las APIs de Google
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.send"
]

CLIENT_SECRETS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

# --- CONFIGURACIÓN DE GMAIL ---
RECIPIENT_EMAIL = 'kevin.tupac@capitalexpress.cl'
EMAIL_SUBJECT = 'Confirmación de Facturas Negociables'

