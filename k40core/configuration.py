"""Persistência JSON versionada das preferências do aplicativo."""

import json
import os
import tempfile


SCHEMA_VERSION = 1


class ConfigurationError(ValueError):
    pass


def load_configuration(path):
    with open(path, "r", encoding="utf-8") as stream:
        payload = json.load(stream)
    if not isinstance(payload, dict):
        raise ConfigurationError("A configuração precisa ser um objeto JSON.")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ConfigurationError("Versão de configuração não suportada.")
    settings = payload.get("settings")
    if not isinstance(settings, dict):
        raise ConfigurationError("A seção 'settings' precisa ser um objeto.")
    return settings


def save_configuration(path, settings):
    """Grava atomicamente para uma interrupção não truncar o arquivo real."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=".k40-config-", suffix=".tmp", dir=directory, text=True
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(
                {"schema_version": SCHEMA_VERSION, "settings": dict(settings)},
                stream, ensure_ascii=False, indent=2, sort_keys=True,
            )
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
