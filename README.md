# 📧 Email Unsubscribe Manager

Herramienta CLI en Python para analizar tu bandeja de entrada, detectar correos de spam, marketing y newsletters, y permitirte tomar acciones: **eliminar**, **bloquear** o **desuscribirte** fácilmente.

Compatible con **Gmail**, **Outlook**, **Yahoo** y cualquier proveedor con soporte IMAP.

---

## 🚀 Características

- 🔍 Detecta automáticamente correos de spam, marketing y newsletters mediante análisis de contenido y remitente.
- 📊 Agrupa los correos por remitente para facilitar la revisión.
- 🗑️ Elimina correos no deseados directamente desde la terminal.
- 🚫 Bloquea remitentes para no recibir más correos de ellos.
- 📭 Desuscríbete automáticamente a través del enlace de baja cuando está disponible.
- 🎨 Interfaz de terminal visual e interactiva gracias a **Rich**.
- 🌐 **Provider IMAP Universal** (recomendado): funciona con cualquier proveedor solo con email + contraseña, sin necesidad de registrar aplicaciones en Azure ni Google Cloud.
- 🔐 Autenticación segura con OAuth 2.0 (Gmail API) y MSAL (Outlook API).

---

## 🛠️ Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/MarioGDC/email-unsub-manager.git
cd email-unsub-manager
```

### 2. Crear y activar el entorno virtual

```bash
python -m venv venv
# En Linux/macOS:
source venv/bin/activate
# En Windows:
venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
cp .env.example .env
# Edita el archivo .env con tus credenciales
```

---

## 🌐 IMAP Universal (Recomendado)

Este es el método más sencillo: **no requiere Azure Portal ni Google Cloud Console**. Solo necesitas tu dirección de email y tu contraseña (o contraseña de aplicación si tienes la verificación en dos pasos activada).

### Outlook / Hotmail / Live

1. **Verifica que IMAP esté habilitado:**
   - Ve a [outlook.live.com](https://outlook.live.com) e inicia sesión.
   - ⚙️ Configuración → Correo → Sincronizar correo electrónico → confirma que IMAP está activo.

2. **Contraseña de aplicación (solo si tienes verificación en 2 pasos):**
   - Ve a [account.microsoft.com/security](https://account.microsoft.com/security).
   - Verificación en dos pasos → Contraseñas de aplicación → Crea una nueva y cópiala.

3. **Configura `.env`** (opcional, también se puede introducir de forma interactiva):
   ```env
   IMAP_EMAIL=tu-email@outlook.com
   IMAP_PASSWORD=tu-contraseña-o-app-password
   IMAP_SERVER=outlook.office365.com
   IMAP_PORT=993
   ```

### Gmail

1. **Habilita el acceso IMAP:**
   - Ve a Gmail → ⚙️ Configuración → Ver toda la configuración → Reenvío y POP/IMAP.
   - Activa **Habilitar IMAP** y guarda los cambios.

2. **Contraseña de aplicación (obligatoria con 2FA):**
   - Ve a [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).
   - Crea una contraseña de aplicación con nombre "Email Unsub Manager" y cópiala.

3. **Configura `.env`** (opcional):
   ```env
   IMAP_EMAIL=tu-email@gmail.com
   IMAP_PASSWORD=tu-app-password-de-16-caracteres
   IMAP_SERVER=imap.gmail.com
   IMAP_PORT=993
   ```

### Yahoo

1. **Habilita el acceso IMAP:**
   - Ve a Yahoo Mail → ⚙️ Configuración → Seguridad → Contraseñas de aplicaciones.
   - Genera una contraseña de aplicación y cópiala.

2. **Configura `.env`** (opcional):
   ```env
   IMAP_EMAIL=tu-email@yahoo.com
   IMAP_PASSWORD=tu-app-password
   IMAP_SERVER=imap.mail.yahoo.com
   IMAP_PORT=993
   ```

> **Nota:** Si no configuras el `.env`, la herramienta te pedirá el email y la contraseña de forma interactiva (la contraseña no se mostrará en pantalla).

---

## 📧 Configuración de Gmail (API)

> ⚠️ Este método requiere acceso a **Google Cloud Console**. Si prefieres una configuración más sencilla, usa el método **IMAP Universal** descrito arriba.

1. Ve a [Google Cloud Console](https://console.cloud.google.com/).
2. Crea un nuevo proyecto o selecciona uno existente.
3. Activa la **Gmail API** en *APIs y servicios > Biblioteca*.
4. Ve a *APIs y servicios > Credenciales* y crea credenciales de tipo **OAuth 2.0 (aplicación de escritorio)**.
5. Descarga el archivo JSON de credenciales y guárdalo como `credentials.json` en la raíz del proyecto.
6. En `.env`, asegúrate de que `GMAIL_CREDENTIALS_FILE=credentials.json`.

---

## 📬 Configuración de Outlook (API)

> ⚠️ Este método requiere acceso a **Azure Portal** (puede requerir suscripción). Si prefieres una configuración más sencilla, usa el método **IMAP Universal** descrito arriba.

1. Ve al [Portal de Azure](https://portal.azure.com/).
2. Navega a *Azure Active Directory > Registros de aplicaciones > Nuevo registro*.
3. Asigna un nombre y selecciona el tipo de cuenta adecuado.
4. En *Permisos de API*, agrega los permisos de **Microsoft Graph**:
   - `Mail.Read`
   - `Mail.ReadWrite`
5. Copia el **Client ID**, crea un **Client Secret** y anota el **Tenant ID**.
6. En `.env`, configura:
   ```
   OUTLOOK_CLIENT_ID=tu-client-id
   OUTLOOK_CLIENT_SECRET=tu-client-secret
   OUTLOOK_TENANT_ID=tu-tenant-id
   ```

---

## ▶️ Uso

```bash
python -m src.main
```

Se mostrará un menú interactivo en la terminal donde podrás:
1. Seleccionar tu proveedor de correo:
   - 📫 Gmail (API) — requiere Google Cloud Console
   - 📬 Outlook (API) — requiere Azure Portal
   - 🌐 **IMAP Universal (Recomendado)** — solo email + contraseña
2. Escanear tu bandeja de entrada.
3. Revisar los correos detectados como spam/marketing.
4. Elegir qué hacer con cada grupo de correos: eliminar, bloquear o desuscribirte.

---

## 🧪 Tests

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
│   ├── __init__.py
│   ├── main.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── email_message.py
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base_provider.py
│   │   ├── gmail_provider.py
│   │   ├── imap_provider.py
│   │   └── outlook_provider.py
│   ├── analyzer/
│   │   ├── __init__.py
│   │   └── spam_detector.py
│   ├── actions/
│   │   ├── __init__.py
│   │   └── email_actions.py
│   └── ui/
│       ├── __init__.py
│       └── terminal_ui.py
└── tests/
    ├── __init__.py
    ├── test_imap_provider.py
    └── test_spam_detector.py
```

---

## 📄 Licencia

MIT
