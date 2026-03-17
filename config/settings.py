import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Centralized application settings."""

    # IMAP Configuration
    IMAP_EMAIL: str = os.getenv("IMAP_EMAIL", "")
    IMAP_PASSWORD: str = os.getenv("IMAP_PASSWORD", "")
    IMAP_SERVER: str = os.getenv("IMAP_SERVER", "")
    IMAP_PORT: int = int(os.getenv("IMAP_PORT", "993"))

    # Predefined IMAP servers (auto-detection)
    IMAP_SERVERS: dict[str, str] = {
        "outlook.com": "outlook.office365.com",
        "hotmail.com": "outlook.office365.com",
        "live.com": "outlook.office365.com",
        "msn.com": "outlook.office365.com",
        "gmail.com": "imap.gmail.com",
        "yahoo.com": "imap.mail.yahoo.com",
        "yahoo.es": "imap.mail.yahoo.com",
    }

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
