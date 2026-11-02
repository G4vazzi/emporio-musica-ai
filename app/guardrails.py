
"""Regras para validar informações antes das respostas."""

import re
import unicodedata


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize(
        "NFKD", texto.casefold()
    )
    return "".join(
        c for c in texto
        if not unicodedata.combining(c)
    )


def fonte_obrigatoria(pergunta: str) -> str | None:
    texto = normalizar(pergunta)

    # Consultar status de pedido não é consultar
    # as políticas gerais de entrega.
    if (
        re.search(
            r"\b(?:status|rastrear|rastreio|rastreamento)\b",
            texto
        )
        and re.search(r"\bpedido\b", texto)
        and not re.search(r"\bcancel\w*\b", texto)
    ):
        return None

    if re.search(
        r"\b(?:arrepend\w*|devol\w*|cancel\w*|"
        r"troca\w*|trocar|garantia|defeito\w*|"
        r"frete|entrega\w*|parcel\w*|"
        r"pagamento\w*|horario\w*|"
        r"funcionamento|loja abre|loja fecha)\b",
        texto
    ):
        return "consultar_politicas"

    if re.search(
        r"\b(?:vende\w*|catalogo|instrumento\w*|"
        r"violao|violoes|guitarra\w*|baixo\w*|"
        r"bateria\w*|teclado\w*|amplificador\w*|"
        r"pedal\w*|estoque|preco\w*|"
        r"disponib\w*|ukulele\w*)\b",
        texto
    ):
        return "buscar_produtos"

    return None


def resposta_politica_documentada(
    pergunta: str,
    resultado: dict
) -> str:

    if "erro" in resultado:
        return (
            "Não consegui consultar o manual "
            "da loja agora."
        )

    if (
        not resultado.get("encontrado")
        or not resultado.get("resultados")
    ):
        return (
            "Não encontrei uma regra específica "
            "para isso no manual da loja. "
            "Recomendo confirmar o procedimento "
            "com a equipe de atendimento."
        )

    documentos = resultado["resultados"]
    texto = normalizar(pergunta)

    # Arrependimento online não deve ser
    # confundido com troca por preferência.
    if (
        "arrepend" in texto
        or (
            "internet" in texto
            and re.search(r"\bdevol\w*", texto)
        )
    ):
        documentos = [
            secao
            for secao in documentos
            if str(
                secao.get("secao", "")
            ).startswith("4.1 ")
        ]

        if not documentos:
            return (
                "Não consegui confirmar a regra "
                "de arrependimento na seção "
                "correspondente do manual. "
                "Recomendo confirmar com a loja."
            )

    secao = documentos[0]

    return (
        f"Segundo o manual, **seção "
        f"{secao['secao']} "
        f"(página {secao['pagina_inicial']})**:\n\n"
        f"{secao['trecho']}\n\n"
        "Se precisar solicitar o procedimento, "
        "entre em contato com a loja."
    )


def _singular(termo: str) -> str:
    if termo.endswith("ais"):
        return termo[:-3] + "al"

    if termo.endswith("oes"):
        return termo[:-3] + "ao"

    if termo.endswith("es"):
        return termo[:-2]

    if termo.endswith("s"):
        return termo[:-1]

    return termo


def consultar_lista_categorias(
    pergunta: str,
    executar
) -> str | None:
    """
    Verifica separadamente perguntas do tipo:
    'Vocês vendem amplificadores e pedais?'
    """

    texto = normalizar(pergunta)

    correspondencia = re.search(
        r"\bvendem\s+([^?!.]+)",
        texto
    )

    if not correspondencia:
        return None

    itens = re.split(
        r"\s+e\s+",
        correspondencia.group(1).strip()
    )

    if not 2 <= len(itens) <= 3:
        return None

    itens = [
        re.sub(
            r"^(?:um|uma|uns|umas|os|as)\s+",
            "",
            item
        ).strip()
        for item in itens
    ]

    if any(
        not item or len(item.split()) > 2
        for item in itens
    ):
        return None

    linhas = [
        "Conferi os itens separadamente no catálogo:",
        ""
    ]

    for item in itens:
        termo = _singular(item)

        resultado = executar(
            "buscar_produtos",
            {"categoria": termo}
        )

        if "erro" in resultado:
            return (
                "Não consegui consultar o catálogo "
                "agora. Tente novamente."
            )

        if not resultado.get("produtos"):
            resultado = executar(
                "buscar_produtos",
                {"termo": termo}
            )

        if "erro" in resultado:
            return (
                "Não consegui consultar o catálogo "
                "agora. Tente novamente."
            )

        if resultado.get("produtos"):
            primeiro = resultado["produtos"][0]

            linhas.append(
                f"- **{item.capitalize()}**: encontrei "
                f"{resultado['total_encontrados']} "
                f"opção(ões) disponíveis. "
                f"Exemplo: {primeiro['nome']} "
                f"({primeiro['preco_atual']})."
            )

        else:
            linhas.append(
                f"- **{item.capitalize()}**: "
                "não encontrei itens disponíveis "
                "na base atual."
            )

    return "\n".join(linhas)
