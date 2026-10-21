"""Configurações centrais: secrets, modelos Gemini e controle de acesso."""
import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Ordem de preferência (todos com camada gratuita na API do Google).
# Se um modelo for desativado (404) ou estourar a cota (429), o app tenta o próximo.
# Para forçar um modelo específico, defina GEMINI_MODEL nos secrets.
MODELOS_PADRAO = [
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
]


def get_secret(chave: str, padrao=None):
    """Lê de st.secrets e, se não houver (ou não existir secrets.toml), de variáveis de ambiente/.env."""
    valor = None
    try:
        valor = st.secrets.get(chave)
    except Exception:
        valor = None
    if valor in (None, ""):
        valor = os.getenv(chave)
    return valor if valor not in (None, "") else padrao


def _como_lista(valor) -> list[str]:
    if not valor:
        return []
    if isinstance(valor, str):
        valor = valor.split(",")
    return [str(v).strip().lower() for v in valor if str(v).strip()]


def get_modelos() -> list[str]:
    preferido = get_secret("GEMINI_MODEL")
    modelos = list(MODELOS_PADRAO)
    if preferido:
        modelos = [preferido] + [m for m in modelos if m != preferido]
    return modelos


def usuario_autorizado(email: str | None) -> bool:
    """Se ALLOWED_EMAILS/ALLOWED_DOMAINS estiverem vazios, qualquer conta Google logada entra."""
    emails = _como_lista(get_secret("ALLOWED_EMAILS"))
    dominios = _como_lista(get_secret("ALLOWED_DOMAINS"))
    if not emails and not dominios:
        return True
    email = (email or "").lower()
    if email in emails:
        return True
    return any(email.endswith("@" + d.lstrip("@")) for d in dominios)


def exigir_login() -> bool:
    return str(get_secret("EXIGIR_LOGIN", "false")).strip().lower() in ("1", "true", "yes", "sim")