from __future__ import annotations

import sys

from config.settings import settings
from src.actions.email_actions import EmailActions
from src.analyzer.spam_detector import SpamDetector
from src.providers.base_provider import BaseEmailProvider
from src.ui.terminal_ui import TerminalUI


def _get_provider(provider_key: str, **kwargs) -> BaseEmailProvider:
    if provider_key == "gmail":
        from src.providers.gmail_provider import GmailProvider
        return GmailProvider()
    elif provider_key == "outlook":
        from src.providers.outlook_provider import OutlookProvider
        return OutlookProvider()
    elif provider_key == "imap":
        from src.providers.imap_provider import ImapProvider
        return ImapProvider(**kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider_key}")


def main() -> None:
    ui = TerminalUI()
    ui.show_welcome()

    # 1. Select provider
    provider_key, imap_kwargs = ui.select_provider()
    provider = _get_provider(provider_key, **imap_kwargs)

    # 2. Authenticate
    ui.show_scan_start(provider.get_provider_name())
    if not provider.authenticate():
        ui.show_error("No se pudo autenticar. Verifica tus credenciales en el archivo .env.")
        sys.exit(1)

    # 3. Fetch emails
    ui.show_info(f"Descargando hasta {settings.MAX_EMAILS_TO_SCAN} correos...")
    emails = provider.fetch_emails(max_results=settings.MAX_EMAILS_TO_SCAN)

    # 4. Analyse for spam / marketing
    detector = SpamDetector()
    spam_emails = detector.analyse(emails)
    groups = detector.group_by_sender(spam_emails)

    ui.show_scan_complete(len(emails), len(spam_emails))

    # 5. Display groups and let user choose actions
    ui.show_groups(groups)
    if not groups:
        return

    groups = ui.select_actions(groups)

    # 6. Confirm and execute
    if ui.confirm_actions(groups):
        actions = EmailActions(provider)
        summary = actions.execute(groups)
        ui.show_results(summary)
    else:
        ui.show_info("Operación cancelada.")


if __name__ == "__main__":
    main()
