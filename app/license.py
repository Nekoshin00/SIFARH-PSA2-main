"""Verificación de la clave de activación de SIFARH.

Se valida en línea contra Supabase. Si no hay conexión, se usa la última validación
guardada localmente (firmada con la clave secreta de esta instalación) durante un
periodo de gracia, para que el programa siga funcionando sin internet.
"""
import hashlib
import hmac
import json
import time

import httpx

from .config import DATA_DIR, settings

_CACHE_PATH = DATA_DIR / ".license_cache"
_OFFLINE_GRACE_SECONDS = 30 * 24 * 60 * 60  # 30 días sin conexión antes de pedir revalidar


class LicenseError(RuntimeError):
    pass


def _hash_clave(clave: str) -> str:
    return hashlib.sha256(clave.strip().upper().encode("utf-8")).hexdigest()


def _firma(key_hash: str) -> str:
    """HMAC con la clave secreta de esta instalación: evita copiar la caché a otro equipo."""
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), key_hash.encode("utf-8"), hashlib.sha256).hexdigest()


def _leer_cache():
    try:
        with _CACHE_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _guardar_cache(key_hash: str) -> None:
    datos = {"key_hash": key_hash, "firma": _firma(key_hash), "validado_en": time.time()}
    _CACHE_PATH.write_text(json.dumps(datos), encoding="utf-8")
    try:
        _CACHE_PATH.chmod(0o600)
    except OSError:
        pass


def _cache_valida(key_hash: str) -> bool:
    datos = _leer_cache()
    if not datos or datos.get("key_hash") != key_hash:
        return False
    if not hmac.compare_digest(str(datos.get("firma", "")), _firma(key_hash)):
        return False
    return (time.time() - float(datos.get("validado_en", 0))) <= _OFFLINE_GRACE_SECONDS


def verificar_licencia() -> None:
    """Lanza LicenseError si falta la clave, es inválida, o no se puede validar ni hay caché."""
    if not settings.LICENSE_KEY:
        raise LicenseError(
            "Falta LICENSE_KEY en el archivo .env. Copia tu clave de activación desde "
            "la sección 'Mis descargas' del sitio de SIFARH."
        )

    key_hash = _hash_clave(settings.LICENSE_KEY)

    try:
        resp = httpx.post(
            f"{settings.LICENSE_API_URL}/rest/v1/rpc/verify_license",
            headers={
                "apikey": settings.LICENSE_API_KEY,
                "Authorization": f"Bearer {settings.LICENSE_API_KEY}",
            },
            json={"p_key": settings.LICENSE_KEY},
            timeout=10,
        )
        resp.raise_for_status()
    except httpx.HTTPError:
        if _cache_valida(key_hash):
            return  # Sin conexión, pero ya se validó esta clave en este equipo recientemente.
        raise LicenseError(
            "No se pudo validar la licencia: se requiere conexión a internet la primera vez "
            "(y cada 30 días para revalidar)."
        )

    if resp.json() is not True:
        try:
            _CACHE_PATH.unlink()
        except FileNotFoundError:
            pass
        raise LicenseError("La clave de activación (LICENSE_KEY) no es válida o fue revocada.")

    _guardar_cache(key_hash)
