"""Rutas de archivos, compatibles con ejecución normal y con el ejecutable compilado.

Al compilar con PyInstaller (--onefile), los recursos de solo lectura (plantillas,
estáticos) se extraen a una carpeta temporal (``sys._MEIPASS``). Los archivos editables
por el usuario (``.env``, ``config.json``, ``data/``) deben vivir junto al ejecutable,
no en esa carpeta temporal, para que sobrevivan entre ejecuciones.
"""
import sys
from pathlib import Path


def resource_dir() -> Path:
    """Carpeta de solo lectura con los recursos empaquetados (plantillas, estáticos)."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / "app"
    return Path(__file__).resolve().parent


def app_dir() -> Path:
    """Carpeta editable junto al ejecutable (o a la raíz del proyecto en desarrollo)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent
