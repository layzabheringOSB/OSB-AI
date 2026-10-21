"""Funções auxiliares: leitura de PDF, planilhas e páginas web."""
import io
import ipaddress
import socket
from urllib.parse import urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

LIMITE_PDF = 30000
LIMITE_WEB = 15000
LIMITE_PLANILHA = 25000


def extrair_texto_pdf(file_bytes: bytes) -> str:
    """Extrai texto de um PDF carregado em memória."""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        partes = []
        for num, page in enumerate(reader.pages, start=1):
            conteudo = page.extract_text()
            if conteudo:
                partes.append(f"\n--- Página {num} ---\n{conteudo}")
        texto = "".join(partes)
        if not texto.strip():
            return "Não foi possível extrair texto (o PDF pode ser escaneado/imagem)."
        return texto[:LIMITE_PDF]
    except Exception as e:
        return f"Erro ao processar PDF: {e}"


def _url_segura(url: str) -> tuple[bool, str]:
    """Evita que o app seja usado para acessar a rede interna (SSRF)."""
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        return False, "Informe uma URL começando com http:// ou https://"
    try:
        for info in socket.getaddrinfo(p.hostname, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False, "Endereço não permitido."
    except socket.gaierror:
        return False, "Não foi possível resolver o endereço da URL."
    return True, ""


def extrair_dados_web(url: str) -> str:
    """Web scraping simples do texto principal de uma página pública."""
    url = (url or "").strip()
    ok, motivo = _url_segura(url)
    if not ok:
        return f"Erro ao acessar a URL: {motivo}"
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        ok, motivo = _url_segura(resp.url)  # confere também o destino após redirecionamentos
        if not ok:
            return f"Erro ao acessar a URL: {motivo}"

        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "header", "footer", "nav", "aside", "noscript"]):
            tag.decompose()
        texto = " ".join(soup.get_text(separator=" ").split())
        return texto[:LIMITE_WEB] or "A página foi acessada, mas não retornou texto legível."
    except Exception as e:
        return f"Erro ao acessar a URL {url}: {e}"


def ler_planilha(arquivo) -> pd.DataFrame:
    """Lê CSV (detecta separador e codificação) ou Excel enviados pelo st.file_uploader."""
    if arquivo.name.lower().endswith(".csv"):
        bruto = arquivo.getvalue()
        for enc in ("utf-8-sig", "latin-1"):
            try:
                return pd.read_csv(io.BytesIO(bruto), sep=None, engine="python", encoding=enc)
            except UnicodeDecodeError:
                continue
        raise ValueError("Não foi possível identificar a codificação do CSV.")
    return pd.read_excel(arquivo)


def _tabela(df: pd.DataFrame) -> str:
    try:
        return df.to_markdown(index=False)
    except ImportError:  # 'tabulate' ausente
        return df.to_string(index=False)


def resumir_dataframe(df: pd.DataFrame) -> str:
    """Resumo estruturado da planilha, sem estourar o limite de tokens."""
    linhas, colunas = df.shape
    info_colunas = [
        f"- **{col}** ({df[col].dtype}): {df[col].nunique()} valores distintos, {df[col].isna().sum()} vazios"
        for col in df.columns
    ]
    partes = [
        "### RESUMO DA PLANILHA",
        f"- **Total de linhas:** {linhas}",
        f"- **Total de colunas:** {colunas}",
        "\n#### Estrutura das colunas:",
        "\n".join(info_colunas),
    ]

    numericas = df.select_dtypes("number")
    if not numericas.empty:
        partes += ["\n#### Estatísticas das colunas numéricas:", _tabela(numericas.describe().round(2).reset_index())]

    partes += ["\n#### Primeiras linhas (amostra):", _tabela(df.head(30))]
    return "\n".join(partes)[:LIMITE_PLANILHA]