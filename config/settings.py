import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Centralized application settings loaded from environment variables."""

    # Gmail
    GMAIL_CREDENTIALS_FILE: str = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
    GMAIL_TOKEN_FILE: str = "token.pickle"
    GMAIL_SCOPES: list[str] = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",
    ]

    # Outlook
    OUTLOOK_CLIENT_ID: str = os.getenv("OUTLOOK_CLIENT_ID", "")
    OUTLOOK_CLIENT_SECRET: str = os.getenv("OUTLOOK_CLIENT_SECRET", "")
    OUTLOOK_TENANT_ID: str = os.getenv("OUTLOOK_TENANT_ID", "")
    OUTLOOK_SCOPES: list[str] = [
        "Mail.Read",
        "Mail.ReadWrite",
    ]
    OUTLOOK_AUTHORITY: str = f"https://login.microsoftonline.com/{os.getenv('OUTLOOK_TENANT_ID', 'common')}"
    OUTLOOK_GRAPH_ENDPOINT: str = "https://graph.microsoft.com/v1.0"

    # General
    MAX_EMAILS_TO_SCAN: int = int(os.getenv("MAX_EMAILS_TO_SCAN", "500"))

    # Spam/Marketing detection keywords
    SPAM_KEYWORDS: list[str] = [
        "unsubscribe", "darse de baja", "cancelar suscripción",
        "opt-out", "opt out", "email preferences", "preferencias de correo",
        "newsletter", "boletín", "marketing",
        "no longer wish to receive", "update your preferences",
        "manage your subscription", "gestionar suscripción",
        "promotional", "promocional", "oferta", "offer",
        "deal", "descuento", "discount", "sale",
        "you are receiving this email because",
        "recibes este correo porque",
    ]

    SPAM_SENDER_PATTERNS: list[str] = [
        "noreply@", "no-reply@", "newsletter@", "marketing@",
        "promo@", "info@", "notifications@", "notificaciones@",
        "deals@", "offers@", "news@", "updates@",
        "hello@", "hola@", "support@", "soporte@",
        "mailer-daemon@", "bounce@",
    ]


settings = Settings()
