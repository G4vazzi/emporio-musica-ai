
"""Interface web do agente Empório da Música AI."""

from time import perf_counter

import streamlit as st

from app.agent import AtendenteIA


# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================

st.set_page_config(
    page_title="Empório da Música AI",
    page_icon="🎸",
    layout="centered",
    initial_sidebar_state="expanded",
)


# ==========================================
# INICIALIZAÇÃO DA SESSÃO
# ==========================================

if "atendente" not in st.session_state:
    st.session_state.atendente = AtendenteIA()

if "mensagens" not in st.session_state:
    st.session_state.mensagens = []


# ==========================================
# MENU LATERAL
# ==========================================

with st.sidebar:

    st.title("🎸 Empório da Música")

    st.caption("Sua música começa aqui.")

    st.divider()

    st.subheader("Sobre o assistente")

    st.write("**Inteligência artificial:** Ollama")
    st.write(
        f"**Modelo:** {st.session_state.atendente.modelo}"
    )
    st.write("**Dados:** SQLite")
    st.write("**Políticas:** Manual PDF")

    st.divider()

    # Reinicia o atendimento
    if st.button(
        "Nova conversa",
        use_container_width=True,
        type="primary",
    ):
        st.session_state.atendente.limpar_historico()
        st.session_state.mensagens = []
        st.rerun()

    st.divider()

    st.info(
        "Protótipo de atendimento desenvolvido "
        "para o desafio técnico de AI Engineer "
        "da Artefact."
    )

    st.caption(
        "Os pedidos utilizam dados históricos "
        "de demonstração, não rastreamento ao vivo."
    )


# ==========================================
# CABEÇALHO
# ==========================================

st.title("Empório da Música AI")

st.markdown(
    "Encontre seu próximo instrumento musical "
    "com a ajuda do nosso assistente virtual."
)

st.divider()


# ==========================================
# SUGESTÕES DE PERGUNTAS
# ==========================================

sugestao_produtos = False
sugestao_pedidos = False
sugestao_politicas = False

if not st.session_state.mensagens:

    st.markdown("**Como posso ajudar você hoje?**")

    col1, col2, col3 = st.columns(3)

    with col1:
        sugestao_produtos = st.button(
            "🎸 Ver violões",
            use_container_width=True,
        )

    with col2:
        sugestao_pedidos = st.button(
            "📦 Consultar pedido",
            use_container_width=True,
        )

    with col3:
        sugestao_politicas = st.button(
            "📖 Trocas e devoluções",
            use_container_width=True,
        )


# ==========================================
# HISTÓRICO VISUAL
# ==========================================

for mensagem in st.session_state.mensagens:

    with st.chat_message(
        mensagem["role"],
        avatar=(
            "🎸"
            if mensagem["role"] == "assistant"
            else "👤"
        ),
    ):

        st.markdown(mensagem["content"])

        if mensagem.get("tempo") is not None:
            st.caption(
                f"Processado em "
                f"{mensagem['tempo']:.2f}s"
            )


# ==========================================
# ENTRADA DE MENSAGENS
# ==========================================

texto_digitado = st.chat_input(
    "Digite sua mensagem...",
    max_chars=2000,
)

pergunta = texto_digitado

if sugestao_produtos:
    pergunta = (
        "Quais violões estão disponíveis "
        "por até R$ 1.000?"
    )

elif sugestao_pedidos:
    pergunta = (
        "Quero consultar o status do meu pedido."
    )

elif sugestao_politicas:
    pergunta = (
        "Como funciona a devolução de "
        "compras feitas pela internet?"
    )


# ==========================================
# PROCESSAMENTO DA PERGUNTA
# ==========================================

if pergunta and pergunta.strip():

    pergunta = pergunta.strip()

    # Registra mensagem do cliente
    st.session_state.mensagens.append({
        "role": "user",
        "content": pergunta,
    })

    with st.chat_message("user", avatar="👤"):
        st.markdown(pergunta)

    # Processa resposta do agente
    with st.chat_message(
        "assistant",
        avatar="🎸",
    ):

        inicio = perf_counter()

        with st.spinner(
            "Consultando informações da loja..."
        ):

            try:
                resposta = (
                    st.session_state.atendente.responder(
                        pergunta
                    )
                )

            except Exception as erro:
                print(
                    f"[ERRO] Atendimento: "
                    f"{type(erro).__name__}: {erro}",
                    flush=True,
                )

                resposta = (
                    "Ocorreu um problema durante "
                    "o atendimento. Tente novamente."
                )

        duracao = perf_counter() - inicio

        st.markdown(resposta)

        st.caption(
            f"Processado em {duracao:.2f}s"
        )

    # Registra a resposta no histórico
    st.session_state.mensagens.append({
        "role": "assistant",
        "content": resposta,
        "tempo": duracao,
    })


# ==========================================
# EXPORTAÇÃO DA CONVERSA
# ==========================================

# IMPORTANTE:
# Este bloco fica depois do processamento
# para incluir a resposta mais recente.

with st.sidebar:

    st.divider()

    st.subheader("Exportar atendimento")

    # Monta o conteúdo em Markdown
    linhas = [
        "# Empório da Música AI",
        "",
        "## Registro de atendimento",
        "",
    ]

    for mensagem in st.session_state.mensagens:

        papel = (
            "Cliente"
            if mensagem["role"] == "user"
            else "Atendente"
        )

        linhas.extend([
            f"### {papel}",
            "",
            mensagem["content"],
            "",
        ])

    conteudo_exportacao = "\n".join(linhas)

    # Converte para UTF-8
    arquivo_markdown = conteudo_exportacao.encode(
        "utf-8"
    )

    # Verifica se a conversa contém mensagens
    tem_mensagens = bool(
        st.session_state.mensagens
    )

    # Botão para baixar o histórico
    st.download_button(
        label="Baixar conversa (.md)",
        data=arquivo_markdown,
        file_name="conversa_emporio.md",
        mime="text/markdown",
        use_container_width=True,
        disabled=not tem_mensagens,
        key="download_conversa",
    )

    if tem_mensagens:

        total = len(
            st.session_state.mensagens
        )

        st.caption(
            f"{total} mensagem(ns) "
            "disponíveis para exportação."
        )

    else:

        st.caption(
            "Inicie uma conversa para "
            "habilitar o download."
        )

    st.caption(
        "Antes de publicar, revise e remova "
        "informações pessoais ou sensíveis "
        "das conversas."
    )
