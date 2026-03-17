import sys
from src.providers.imap_provider import ImapProvider
from src.analyzer.spam_detector import SpamDetector
from src.actions.email_actions import EmailActionExecutor
from src.ui.terminal_ui import TerminalUI
from config.settings import settings


def main():
    ui = TerminalUI()
    ui.show_banner()

    # Step 1: Configure IMAP connection
    provider_key, kwargs = ui.select_provider()
    if provider_key == "exit":
        ui.show_info("¡Hasta luego! 👋")
        sys.exit(0)

    # Step 2: Authenticate
    try:
        ui.show_info("Conectando al servidor de correo...")
        provider = ImapProvider(**kwargs)
        provider.authenticate()
        ui.show_success(f"Conectado a {provider.get_provider_name()} correctamente.")
    except Exception as e:
        ui.show_error(str(e))
        sys.exit(1)

    # Step 3: Fetch emails
    try:
        max_emails = settings.MAX_EMAILS_TO_SCAN
        ui.show_info(f"Escaneando hasta {max_emails} correos...")
        with ui.show_scanning_progress() as progress:
            task = progress.add_task("Descargando correos...", total=None)
            emails = provider.fetch_emails(max_results=max_emails)
            progress.update(task, description=f"✅ {len(emails)} correos descargados")
        ui.show_success(f"Se descargaron {len(emails)} correos.")
    except Exception as e:
        ui.show_error(f"Error descargando correos: {e}")
        sys.exit(1)

    if not emails:
        ui.show_info("No se encontraron correos en la bandeja de entrada.")
        sys.exit(0)

    # Step 4: Analyze
    ui.show_info("Analizando correos...")
    detector = SpamDetector()
    analyzed = detector.analyze(emails)
    groups = detector.group_by_sender(analyzed, min_score=15.0)

    # Step 5: Show results
    ui.show_results_table(groups)
    if not groups:
        sys.exit(0)

    # Step 6: Get user actions
    groups = ui.get_user_actions(groups)

    # Step 7: Confirm and execute
    if ui.confirm_actions(groups):
        ui.show_info("Ejecutando acciones...")
        executor = EmailActionExecutor(provider)
        summary = executor.execute_actions(groups)
        ui.show_execution_summary(summary)
    else:
        ui.show_info("Operación cancelada.")

    ui.show_info("¡Hasta luego! 👋")


if __name__ == "__main__":
    main()
