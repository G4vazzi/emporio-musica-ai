
"""Interface web do agente Empório da Música AI."""

import streamlit as st
from time import perf_counter

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

    if st.button(
        "Nova conversa",
        use_container_width=True,
        type="primary",
    ):
        st.session_state.atendente.limpar_historico()
        st.session_state.mensagens = []
        st.rerun()

    conteudo_exportacao = (
        "# Empório da Música AI\n\n"
        "## Registro de antendimento\n\n"
    )

    for mensagem in st.session_state.mensagens:

        papel= (
            "Cliente"
            if mensagem["role"] == "user"
            else "Atendente"
        )

        conteudo_exportacao += (
            f"### {papel}\n\n"
            f"{mensagem['content']}\n\n"
        )

    st.download_button(
        label="Baixar conversa (.md)",
        data=conteudo_exportacao,
        file_name="conversa_emporio.md",
        mime="text/markdown",
        use_container_width=True,
        disabled=not st.session_state.mensagens,
    )

    st.caption(
        "Antes de publicar, revise e remova"
        " informações pessoais ou sensíveis"
        "das conversas."
    )

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

else:
    sugestao_produtos = False
    sugestao_pedidos = False
    sugestao_politicas = False


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
    pergunta = "Quero consultar o status do meu pedido."

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

    st.session_state.mensagens.append({
        "role": "user",
        "content": pergunta,
    })

    with st.chat_message("user", avatar="👤"):
        st.markdown(pergunta)

    with st.chat_message("assistant", avatar="🎸"):

        inicio = perf_counter()

        with st.spinner(
            "Consultando informações da loja..."
        ):
            resposta = (
                st.session_state.atendente.responder(
                    pergunta
                )
            )

        duracao = perf_counter() - inicio

        st.markdown(resposta)

        st.caption(
            f"Processado em {duracao:.2f}s"
        )

    st.session_state.mensagens.append({
        "role": "assistant",
        "content": resposta,
        "tempo": duracao,
    })
