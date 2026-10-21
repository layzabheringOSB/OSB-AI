
from dataclasses import dataclass

import streamlit as st
from google import genai
from google.genai import errors, types

MAX_HISTORICO = 10  # nº de mensagens anteriores enviadas ao modelo
CODIGOS_TENTAR_OUTRO_MODELO = {404, 429, 500, 503, 504}


@dataclass
class RespostaIA:
    texto: str
    modelo: str = ""
    ok: bool = True


@st.cache_resource(show_spinner=False)
def get_client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


def montar_instrucoes(nome_usuario: str, contexto: str) -> str:
    bloco_contexto = contexto.strip() or "(nenhum documento anexado)"
    return f"""Você é o Agente de Inteligência Legislativa do Observatório Social do Brasil - SP (OSB-SP).
Sua missão é atuar como especialista técnico em fiscalização pública, transparência e controle social.

Diretrizes:
1. Trate o usuário pelo nome: {nome_usuario}.
2. Baseie-se na legislação pertinente (Lei de Acesso à Informação nº 12.527/11, Lei de Licitações nº 14.133/21 e Art. 37 da CF/88).
3. Seja claro e objetivo; use tabelas ou tópicos para resumir achados complexos.
4. Se houver documentos/dados abaixo, use-os prioritariamente e cite de onde tirou cada informação.
5. Não invente números, valores, datas ou artigos de lei. Se não tiver certeza ou o dado não estiver no material, diga isso.
6. Responda sempre em português do Brasil.

CONTEXTO ADICIONAL / DOCUMENTOS ANEXADOS:
{bloco_contexto}
"""


def _montar_contents(historico: list[dict], pergunta: str) -> list[types.Content]:
    recentes = [m for m in historico if not m.get("erro")][-MAX_HISTORICO:]
    while recentes and recentes[0]["role"] != "user":  # o histórico deve começar pelo usuário
        recentes = recentes[1:]

    contents = []
    for m in recentes:
        role = "user" if m["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=m["content"])]))
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=pergunta)]))
    return contents


def gerar_resposta(client, modelos, historico, pergunta, nome_usuario, contexto) -> RespostaIA:
    config = types.GenerateContentConfig(
        system_instruction=montar_instrucoes(nome_usuario, contexto),
        temperature=0.3,
    )
    contents = _montar_contents(historico, pergunta)
    ultimo_erro = None

    for modelo in modelos:
        try:
            resp = client.models.generate_content(model=modelo, contents=contents, config=config)
        except errors.APIError as e:
            ultimo_erro = e
            if e.code in CODIGOS_TENTAR_OUTRO_MODELO:
                continue
            return RespostaIA(f"Erro na API do Gemini ({e.code}): {e.message}", modelo, ok=False)
        except Exception as e:  # rede, timeout etc.
            return RespostaIA(f"Erro inesperado ao consultar a IA: {e}", modelo, ok=False)

        texto = (resp.text or "").strip()
        if texto:
            return RespostaIA(texto, modelo)
        return RespostaIA(
            "A IA não devolveu texto (resposta vazia ou bloqueada pelos filtros). Tente reformular a pergunta.",
            modelo,
            ok=False,
        )

    if ultimo_erro is not None and ultimo_erro.code == 429:
        msg = ("O limite gratuito da API do Google foi atingido. Aguarde cerca de 1 minuto e tente de novo "
               "(se persistir, a cota diária pode ter acabado e só renova no dia seguinte).")
    else:
        msg = ("Nenhum dos modelos configurados respondeu. Verifique a chave GEMINI_API_KEY e, se necessário, "
               "defina GEMINI_MODEL com um modelo disponível no Google AI Studio.")
    return RespostaIA(msg, ok=False)