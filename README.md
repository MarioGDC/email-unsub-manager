# 📧 Email Unsubscribe Manager

Herramienta CLI para analizar tu bandeja de entrada, detectar spam, marketing y newsletters, y tomar acciones masivas (eliminar, desuscribir, bloquear).

Funciona con **cualquier proveedor de correo** que soporte IMAP: Outlook, Gmail, Yahoo, y más.

---

## ✨ Características

- 🔍 **Detección inteligente**: puntúa cada remitente según señales de spam/marketing (cabecera `List-Unsubscribe`, patrones en el remitente, palabras clave, píxeles de rastreo)
- 📊 **Vista agrupada por remitente**: muestra cuántos emails tienes de cada sender y su puntuación
- 🗑 **Eliminar en masa**: borra todos los correos de un remitente de una vez
- 📤 **Desuscripción automática**: usa la cabecera `List-Unsubscribe` para darte de baja
- 🚫 **Bloquear remitentes** (instrucciones para hacerlo manualmente en tu cliente de correo)
- 🔐 **Sin APIs externas**: solo IMAP estándar, sin Azure Portal ni Google Cloud Console

---

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/MarioGDC/email-unsub-manager.git
cd email-unsub-manager
```

### 2. Crear y activar el entorno virtual

```bash
python -m venv venv
```

**Windows (PowerShell):**
```powershell
venv\Scripts\activate
```

**macOS / Linux:**
```bash
source venv/bin/activate
```

> ⚠️ En Windows, si te aparece un error de ejecución de scripts, ejecuta primero:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Copiar el archivo de configuración

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Edita `.env` con tus credenciales (opcional, también puedes introducirlas al ejecutar la herramienta).

---

## ⚙️ Configuración

Edita el archivo `.env`:

```env
IMAP_EMAIL=tu-email@outlook.com
IMAP_PASSWORD=tu-contraseña-de-aplicación
IMAP_SERVER=           # dejar vacío para autodetección
IMAP_PORT=993
MAX_EMAILS_TO_SCAN=500
```

> 💡 Si dejas `IMAP_EMAIL` y `IMAP_PASSWORD` vacíos en `.env`, la herramienta te los pedirá de forma interactiva al ejecutarla.

---

## 🔑 Contraseñas de aplicación (recomendado si tienes 2FA)

Si tienes la **verificación en dos pasos** activada en tu cuenta, necesitas crear una **contraseña de aplicación** en lugar de usar tu contraseña habitual.

### Outlook / Hotmail / Live

1. Ve a [https://account.microsoft.com/security](https://account.microsoft.com/security)
2. Inicia sesión con tu cuenta de Microsoft
3. Ve a **Opciones de seguridad avanzadas**
4. Busca la sección **Contraseñas de aplicación** y haz clic en **Crear una nueva contraseña de aplicación**
5. Copia la contraseña generada y úsala en `IMAP_PASSWORD`

### Gmail

1. Ve a [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Inicia sesión con tu cuenta de Google
3. En "Seleccionar aplicación", elige **Correo** (o "Otra")
4. En "Seleccionar dispositivo", elige **Ordenador con Windows** (o el tuyo)
5. Haz clic en **Generar**
6. Copia la contraseña de 16 caracteres y úsala en `IMAP_PASSWORD`

---

## 📬 Habilitar IMAP en tu cuenta de correo

### Outlook

1. Abre [Outlook.com](https://outlook.com) y ve a **Configuración** (⚙️)
2. Busca **Correo → Sincronización del correo electrónico**
3. Activa la opción **IMAP**

### Gmail

1. Abre [Gmail](https://mail.google.com) y ve a **Configuración** (⚙️) → **Ver toda la configuración**
2. Ve a la pestaña **Reenvío y correo POP/IMAP**
3. En la sección **Acceso IMAP**, selecciona **Habilitar IMAP**
4. Haz clic en **Guardar cambios**

---

## ▶️ Uso

```bash
python -m src.main
```

La herramienta te guiará por los siguientes pasos:

1. **Selecciona tu proveedor**: Outlook, Gmail, Yahoo u otro
2. **Introduce tus credenciales**: email y contraseña (o contraseña de aplicación)
3. **Espera el análisis**: descarga y puntúa los correos
4. **Revisa los resultados**: tabla con remitentes detectados y puntuaciones
5. **Elige una acción por remitente**: eliminar, desuscribir, bloquear u omitir
6. **Confirma y ejecuta**: las acciones se realizan en tu buzón

---

## 🧪 Ejecutar tests

```bash
pytest tests/ -v
```

---

## 📁 Estructura del proyecto

```
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── setup.py
├── config/
│   └── settings.py
├── src/
│   ├── main.py
│   ├── models/
│   │   └── email_message.py
│   ├── providers/
│   │   ├── base_provider.py
│   │   └── imap_provider.py
│   ├── analyzer/
│   │   └── spam_detector.py
│   ├── actions/
│   │   └── email_actions.py
│   └── ui/
│       └── terminal_ui.py
└── tests/
    ├── test_spam_detector.py
    └── test_imap_provider.py
```

---

## 🛡️ Privacidad y seguridad

- Las credenciales se almacenan **solo en tu archivo `.env` local** (nunca se envían a ningún servidor externo)
- La herramienta se conecta directamente a tu servidor IMAP con SSL/TLS
- El archivo `.env` está incluido en `.gitignore` para que no se suba accidentalmente a GitHub