
import streamlit as st

from ai_client import gerar_resposta, get_client
from config import exigir_login, get_modelos, get_secret, usuario_autorizado
from helpers import extrair_dados_web, extrair_texto_pdf, ler_planilha, resumir_dataframe

st.set_page_config(page_title="Agente IA - OSB-SP", page_icon="⚖️", layout="wide")

ACOES_RAPIDAS = {
    "📄 Resumir prestação de contas": (
        "Resuma o documento/dados carregados como uma prestação de contas: principais receitas e despesas, "
        "valores relevantes, datas e pontos que merecem atenção da fiscalização. "
        "Se não houver material carregado, diga quais documentos preciso anexar."
    ),
    "🏛️ Analisar emenda parlamentar": (
        "Analise a emenda parlamentar descrita no material carregado: autor, valor, finalidade, destinatário, "
        "execução e possíveis inconsistências ou pontos a fiscalizar. "
        "Se não houver material carregado, explique como localizar essas informações no Portal da Transparência."
    ),
    "⚖️ Checklist Lei 14.133/21": (
        "Monte um checklist de fiscalização de licitação com base na Lei 14.133/21 (fase preparatória, edital, "
        "julgamento, contratação e execução), adaptado ao material carregado, se houver."
    ),
    "🔍 Pedido via LAI": (
        "Redija um modelo de pedido de acesso à informação (Lei 12.527/11) sobre o tema ou documento carregado, "
        "com linguagem formal, objeto claro e prazos legais."
    ),
}

#Layout 

LOGO_OSB = "https://www.osbrasil.org.br/wp-content/uploads/2024/11/LOGO-OSB-1024x387.webp"

ESTILO = """
<style>
.stApp { background-color: #F4FAF6; }
[data-testid="stSidebar"] { background-color: #E3F1E8; border-right: 1px solid #BFDDCB; }
.osb-header {
    background: linear-gradient(135deg, #006437 0%, #0A7F4A 100%);
    padding: 22px 28px; border-radius: 14px; margin-bottom: 18px;
}
.osb-header h1 { color: #FFFFFF; margin: 0; font-size: 1.9rem; padding: 0; }
.osb-header p { color: #E3F1E8; margin: 6px 0 0 0; }
.stButton > button {
    background-color: #FFFFFF; color: #006437; border: 1px solid #006437; border-radius: 10px;
}
.stButton > button:hover { background-color: #006437; color: #FFFFFF; border-color: #006437; }
.stButton > button:hover p { color: #FFFFFF; }
.stButton > button[kind="primary"] { background-color: #006437; color: #FFFFFF; }
[data-testid="stChatMessage"] {
    background-color: #FFFFFF; border: 1px solid #D5E8DC; border-radius: 12px; padding: 10px 14px;
}
</style>
"""
st.markdown(ESTILO, unsafe_allow_html=True)

# Estado da sessão 
st.session_state.setdefault("messages", [])
st.session_state.setdefault("contexto_documento", "")
st.session_state.setdefault("contexto_nome", "")
st.session_state.setdefault("assinatura_upload", None)


def definir_contexto(nome: str, texto: str):
    st.session_state.contexto_nome = nome
    st.session_state.contexto_documento = texto


# Autenticação 
LOGIN_ATIVO = exigir_login()

if not LOGIN_ATIVO:
    nome_usuario, email_usuario = "voluntário(a)", None
else:
    if not getattr(st.user, "is_logged_in", False):  # False também quando [auth] não está configurado
        _, col, _ = st.columns([1, 2, 1])
        with col:
            st.markdown(
                """
                <div style="background-color:#f8f9fa;padding:30px;border-radius:15px;border:1px solid #006437;text-align:center;">
                    <h1 style="color:#006437;margin-bottom:10px;">🤖 Agente IA OSB-SP</h1>
                    <p style="color:#4b5563;font-size:1.1em;">Assistente de Inteligência Legislativa & Transparência</p>
                    <hr style="margin:20px 0;border:0;border-top:1px solid #eee;">
                    <p style="color:#6b7280;margin-bottom:25px;">Faça login com sua conta Google para continuar.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.write("")
            if st.button("Entrar com Google", use_container_width=True, type="primary"):
                try:
                    st.login("google")
                except Exception as e:
                    st.error(
                        "Login Google não configurado. Confira a seção [auth] em .streamlit/secrets.toml "
                        f"(veja secrets.toml.example). Detalhe: {e}"
                    )
            st.info("🔒 Acesso restrito aos voluntários do Observatório Social.")
        st.stop()

    email_usuario = st.user.get("email")
    nome_usuario = st.user.get("name") or email_usuario or "voluntário(a)"

    if not usuario_autorizado(email_usuario):
        st.error(f"A conta {email_usuario} não tem acesso a este aplicativo.")
        if st.button("Sair"):
            st.logout()
        st.stop()

# Gemini 
api_key = get_secret("GEMINI_API_KEY")
if not api_key:
    st.error("Chave da API Gemini (GEMINI_API_KEY) não encontrada nas configurações!")
    st.stop()

client = get_client(api_key)
modelos = get_modelos()

# Barra lateral 
with st.sidebar:
    st.markdown(f"### 👤 Olá, {nome_usuario}!" if LOGIN_ATIVO else "### ⚖️ Agente IA OSB-SP")
    if LOGIN_ATIVO and st.button("Sair", use_container_width=True):
        st.logout()

    st.divider()
    st.subheader("📂 Upload de Arquivos & Dados")

    tipo = st.radio(
        "Selecione a fonte de dados extra:",
        ["Nenhum", "Planilha (CSV/XLSX)", "Documento PDF", "Link Portal Transparência"],
    )

    if tipo == "Planilha (CSV/XLSX)":
        arquivo = st.file_uploader("Envie a planilha", type=["csv", "xlsx"])
        if arquivo and st.session_state.assinatura_upload != (arquivo.name, arquivo.size):
            try:
                df = ler_planilha(arquivo)
                definir_contexto(f"Planilha: {arquivo.name}", resumir_dataframe(df))
                st.session_state.assinatura_upload = (arquivo.name, arquivo.size)
                st.session_state.df_preview = df.head(20)
            except Exception as e:
                st.error(f"Erro ao ler a planilha: {e}")
        if arquivo and st.session_state.get("df_preview") is not None:
            st.success(f"Planilha '{arquivo.name}' carregada!")
            with st.expander("Pré-visualizar dados"):
                try:
                    st.dataframe(st.session_state.df_preview.astype(str))
                except Exception:
                    st.write(st.session_state.df_preview)

    elif tipo == "Documento PDF":
        arquivo = st.file_uploader("Envie o documento PDF", type=["pdf"])
        if arquivo and st.session_state.assinatura_upload != (arquivo.name, arquivo.size):
            texto = extrair_texto_pdf(arquivo.getvalue())
            definir_contexto(f"PDF: {arquivo.name}", f"CONTEÚDO DO PDF ({arquivo.name}):\n{texto}")
            st.session_state.assinatura_upload = (arquivo.name, arquivo.size)
        if arquivo:
            st.success(f"PDF '{arquivo.name}' anexado ao contexto!")

    elif tipo == "Link Portal Transparência":
        url = st.text_input("URL do Portal de SP:", "https://www.saopaulo.sp.leg.br/transparencia/")
        if st.button("Extrair dados da URL"):
            with st.spinner("Lendo página..."):
                conteudo = extrair_dados_web(url)
            if conteudo.startswith("Erro"):
                st.error(conteudo)
            else:
                definir_contexto(f"URL: {url}", f"DADOS EXTRAÍDOS DA URL ({url}):\n{conteudo}")
                st.success("Dados da URL carregados no contexto!")

    if st.button("Limpar Dados Carregados", use_container_width=True):
        definir_contexto("", "")
        st.session_state.assinatura_upload = None
        st.session_state.df_preview = None
        st.toast("Contexto limpo com sucesso.")
        st.rerun()

    if st.button("Nova conversa", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.caption(f"Modelo: {modelos[0]}")

    st.image(LOGO_OSB, use_container_width=True)

# --- Chat ---
st.markdown(
    """
    <div class="osb-header">
        <h1>🤖 Agente IA - Observatório Social SP</h1>
        <p>Consulte dados do Portal de Transparência de SP, PDFs de processos e planilhas orçamentárias.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
if st.session_state.contexto_nome:
    st.info(f"📎 Contexto ativo: {st.session_state.contexto_nome}")

prompt = None
colunas = st.columns(len(ACOES_RAPIDAS))
for col, (rotulo, texto_prompt) in zip(colunas, ACOES_RAPIDAS.items()):
    if col.button(rotulo, use_container_width=True):
        prompt = texto_prompt

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

digitado = st.chat_input("Como posso te ajudar no controle social hoje?")
prompt = digitado or prompt

if prompt:
    historico = list(st.session_state.messages)  # histórico anterior, sem a pergunta atual
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analisando solicitação e base legal..."):
            resp = gerar_resposta(
                client, modelos, historico, prompt, nome_usuario, st.session_state.contexto_documento
            )
        if resp.ok:
            st.markdown(resp.texto)
            st.caption(f"Modelo: {resp.modelo}")
        else:
            st.error(resp.texto)

    st.session_state.messages.append({"role": "assistant", "content": resp.texto, "erro": not resp.ok})