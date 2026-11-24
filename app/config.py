"""Configuración centralizada.

- ``config.json``: opciones no sensibles (se puede compartir o versionar).
- ``.env``: valores sensibles (licencia, tokens, credenciales). Nunca se escribe en config.json.
"""
import json
import os
import secrets

from dotenv import load_dotenv

from .paths import app_dir, resource_dir

BASE_DIR = app_dir()
RESOURCE_DIR = resource_dir()
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

_CONFIG_DEFAULTS = {
    "cookie_secure": False,
    "token_expire_minutes": 480,
    "dias_alerta_caducidad": 90,
    "telegram_mode": "polling",
    "telegram_allowed_chat_ids": "",
    "ollama_url": "http://localhost:11434/api/generate",
    "ollama_model": "llama3",
    "ollama_timeout": 180,
}


def _cargar_config_json() -> dict:
    """Lee config.json junto al ejecutable; si falta o es inválido, usa los valores por defecto."""
    ruta = BASE_DIR / "config.json"
    if not ruta.exists():
        return {}
    try:
        with ruta.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


_config = {**_CONFIG_DEFAULTS, **_cargar_config_json()}


def _cargar_secret_key() -> str:
    """Usa SECRET_KEY del entorno o genera una persistente en data/.secret_key."""
    desde_env = os.getenv("SECRET_KEY", "").strip()
    if desde_env:
        return desde_env
    ruta = DATA_DIR / ".secret_key"
    if ruta.exists():
        return ruta.read_text().strip()
    clave = secrets.token_urlsafe(48)
    ruta.write_text(clave)
    try:
        ruta.chmod(0o600)
    except OSError:
        pass
    return clave


def _lista_enteros(valor) -> set:
    if isinstance(valor, (list, tuple, set)):
        valor = ",".join(str(x) for x in valor)
    return {int(x) for x in str(valor).split(",") if x.strip().lstrip("-").isdigit()}


class Settings:
    APP_NAME = "SIFARH"

    # --- Sensibles: solo desde .env (nunca en config.json) ---
    SECRET_KEY = _cargar_secret_key()
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'farmacia.db'}")
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()
    LICENSE_KEY = os.getenv("LICENSE_KEY", "").strip()
    LICENSE_API_URL = os.getenv("LICENSE_API_URL", "https://mufcqpuegqfjlbvijylx.supabase.co").rstrip("/")
    LICENSE_API_KEY = os.getenv("LICENSE_API_KEY", "sb_publishable_1747pCc9Fq50q7fPvqIxCA_It0XKer7").strip()

    # --- No sensibles: config.json (con valores por defecto si falta el archivo) ---
    JWT_ALGORITHM = "HS256"
    TOKEN_EXPIRE_MINUTES = int(_config["token_expire_minutes"])
    COOKIE_NAME = "access_token"
    COOKIE_SECURE = bool(_config["cookie_secure"])
    DIAS_ALERTA_CADUCIDAD = int(_config["dias_alerta_caducidad"])
    TELEGRAM_MODE = str(_config["telegram_mode"]).strip().lower()
    TELEGRAM_ALLOWED_CHAT_IDS = _lista_enteros(_config["telegram_allowed_chat_ids"])
    OLLAMA_URL = str(_config["ollama_url"])
    OLLAMA_MODEL = str(_config["ollama_model"])
    OLLAMA_TIMEOUT = float(_config["ollama_timeout"])


settings = Settings()
