# Agente de Inteligência Legislativa - OSB-SP

Suporte de IA para o Observatório Social do Brasil - São Paulo: ajuda voluntários e gestão na fiscalização e análise de dados públicos, usando Gemini (API gratuita do Google) e web scraping.

## Funcionalidades

1. **Login Google (OAuth/OIDC nativo do Streamlit)**, com lista opcional de e-mails/domínios autorizados.
2. **Fontes de dados extras**: PDF, planilhas CSV/XLSX e páginas do Portal da Transparência (BeautifulSoup).
3. **Chat com memória de conversa** e instruções legislativas (Lei 12.527/11, Lei 14.133/21, Art. 37 CF/88).
4. **Ações rápidas**: prestação de contas, emendas parlamentares, checklist da Lei 14.133 e pedido via LAI.
5. **Fallback automático de modelos** Gemini e tratamento de limite da cota gratuita.

## Estrutura

- `main.py`: interface Streamlit
- `ai_client.py`: chamadas ao Gemini
- `helpers.py`: PDF, planilha e scraping
- `config.py`: secrets, modelos e controle de acesso

