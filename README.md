# SIFARH · Inventario farmacéutico hospitalario

FastAPI + SQLAlchemy + SQLite + Jinja2. Autenticación con JWT en cookie `HttpOnly`/`SameSite=Lax`.
Requiere una clave de activación (ver [Licencia](#licencia)).

## Puesta en marcha (desde el código fuente)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # claves sensibles (ver tabla abajo)
cp config.example.json config.json   # opciones normales (ver tabla abajo)
python seed_demo.py           # opcional: datos de demostración
python run.py                 # http://127.0.0.1:8000
```

La primera visita redirige a `/registro`: **la primera cuenta creada es Admin**. Los registros posteriores
quedan *pendientes* (rol Médico/Farmacéutico, nunca Admin) hasta que un Admin los apruebe en `/usuarios`.

## Configuración: `.env` vs `config.json`

Para no exponer datos sensibles si se comparte o versiona la configuración, se dividió en dos archivos:

- **`.env`** (no se versiona): solo valores sensibles.

  | Variable | Descripción |
  |---|---|
  | `LICENSE_KEY` | **Obligatoria.** Clave de activación de "Mis descargas" del sitio de SIFARH. |
  | `SECRET_KEY` | Firma los JWT. Si se omite, se genera una y se guarda en `data/.secret_key`. |
  | `DATABASE_URL` | Cadena de conexión (SQLite por defecto; usa esta variable si migras a PostgreSQL con usuario/contraseña). |
  | `TELEGRAM_BOT_TOKEN` | Token del bot de Telegram (opcional). |
  | `TELEGRAM_WEBHOOK_SECRET` | Solo en modo `webhook` (ver abajo). |

- **`config.json`** (se puede compartir/versionar, no sensible):

  | Clave | Por defecto | Descripción |
  |---|---|---|
  | `cookie_secure` | `false` | Pon `true` si sirves por HTTPS. |
  | `token_expire_minutes` | `480` | Duración de la sesión. |
  | `dias_alerta_caducidad` | `90` | Umbral de alerta de caducidad. |
  | `telegram_mode` | `"polling"` | `polling` (el servidor consulta a Telegram) o `webhook`. |
  | `telegram_allowed_chat_ids` | `""` | Chat IDs autorizados separados por coma. Vacío = cualquiera. |
  | `ollama_url` | `http://localhost:11434/api/generate` | Endpoint de Ollama. |
  | `ollama_model` | `"llama3"` | Modelo (debe estar descargado: `ollama pull <modelo>`). |
  | `ollama_timeout` | `180` | Segundos de espera. |

  Si falta `config.json`, se usan estos valores por defecto.

Ambos archivos van **junto al ejecutable** (o en la raíz del proyecto si corres `python run.py`), nunca dentro
del `.exe`.

## Licencia

Al iniciar, el programa valida `LICENSE_KEY` contra el servidor de licencias (una sola petición, sin enviar
datos del inventario). Funciona sin internet después de la primera vez:

1. **Primera vez:** necesita conexión para validar la clave. Si es válida, guarda una confirmación firmada en
   `data/.license_cache` (atada a este equipo mediante `SECRET_KEY`).
2. **Siguientes arranques sin internet:** usa esa confirmación durante 30 días.
3. **Cada 30 días (o si cambias la clave):** vuelve a pedir conexión para revalidar.

Si la clave es inválida o fue revocada, el programa no arranca y lo indica en el mensaje de error.

## Compilar un ejecutable (.exe)

Para no distribuir el código fuente:

```bash
python -m venv .venv-build && source .venv-build/bin/activate   # o .venv-build\Scripts\activate en Windows
pip install -r requirements-build.txt
pyinstaller SIFARH.spec
```

El flujo de GitHub Actions compila el ejecutable Linux para Rocky Linux 9 x86_64 dentro de un contenedor
`rockylinux:9`. Para compilarlo manualmente con esa misma compatibilidad, ejecuta los comandos anteriores
en Rocky Linux 9 x86_64.

El resultado queda en `dist/SIFARH.exe` (o `dist/SIFARH` en Linux/macOS). Para distribuirlo, copia junto al
ejecutable:

```
SIFARH.exe
.env            # con LICENSE_KEY=... (y el resto de valores sensibles)
config.json     # opcional, solo si cambias algo de la tabla de arriba
```

Las plantillas y archivos estáticos ya quedan empaquetados dentro del `.exe`; `data/` (base de datos, caché
de licencia) se crea junto al ejecutable en el primer arranque.

## Estructura

```
app/
  main.py  config.py  paths.py  license.py  database.py  models.py  security.py  deps.py  templating.py
  routes/    auth, reports (dashboard + CSV), inventory (CRUD), search (consulta), users, api (Telegram/Ollama)
  services/  inventory (alertas, búsqueda, CSV), telegram_bot, ollama
  templates/ layout, login, registro, dashboard, inventario, medicamento_form, consulta, usuarios
  static/    css/style.css, js/app.js
tests/test_app.py   seed_demo.py   run.py   SIFARH.spec
```

## Permisos

| Acción                          | Admin | Farmacéutico | Médico |
|---------------------------------|:-----:|:------------:|:------:|
| Ver dashboard / consulta / inventario | ✔ | ✔ | ✔ |
| Crear/editar/eliminar medicamentos    | ✔ | ✔ | ✖ |
| Exportar CSV, análisis con IA         | ✔ | ✔ | ✖ |
| Administrar usuarios                  | ✔ | ✖ | ✖ |

## Alertas (resaltadas en rojo/naranja)

Stock < mínimo · Stock > máximo · Caducidad ≤ 90 días (`dias_alerta_caducidad` en `config.json`) o ya caducado.

## Telegram

1. Crea un bot con @BotFather y pon `TELEGRAM_BOT_TOKEN` en `.env`.
2. **Modo `polling`** (por defecto, ideal en local): el servidor arranca un worker; no necesita URL pública.
3. **Modo `webhook`**: pon `"telegram_mode": "webhook"` en `config.json`, define `TELEGRAM_WEBHOOK_SECRET` en
   `.env` y registra `https://TU_HOST/api/telegram/webhook` con `setWebhook` (parámetro `secret_token`).
4. Restringe quién puede consultar con `telegram_allowed_chat_ids` (envía `/start` al bot para ver tu `chat_id`).

Comandos: texto libre o `/stock <texto>`, `/criticos`, `/caducan`, `/ayuda`.

## Ollama

`POST /api/ai/analisis` (sesión Admin/Farmacéutico; botón en el dashboard) envía a `ollama_url`
los medicamentos caducados/por caducar y con stock crítico (máx. 50 de cada tipo) y devuelve el análisis.
Configura el modelo con `ollama_model` (debe estar descargado: `ollama pull <modelo>`).

## Pruebas

```bash
python -m pytest -q
```

## Notas de seguridad

- Contraseñas con PBKDF2-SHA256; bloqueo temporal tras 5 intentos fallidos de login.
- Se revalida el usuario en BD en cada petición (suspender/eliminar surte efecto inmediato).
- Pon `"cookie_secure": true` en `config.json` si sirves por HTTPS. Para producción, migra a PostgreSQL y un
  limitador de intentos compartido.
- El CSV neutraliza inyección de fórmulas (`=`, `+`, `-`, `@`).
