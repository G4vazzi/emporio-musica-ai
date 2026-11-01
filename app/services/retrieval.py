
"""Recuperação lexical de seções do manual da loja."""

import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import pymupdf


STOPWORDS = {
    "a", "as", "ao", "aos", "com", "como",
    "da", "das", "de", "do", "dos", "e",
    "em", "eu", "me", "meu", "minha",
    "na", "nas", "no", "nos", "o", "os",
    "ou", "para", "por", "posso",
    "qual", "quais", "que", "se", "ser",
    "tem", "um", "uma", "voces",
    "loja", "empresa", "sobre",
    "estou", "queria", "quero", "mais",
}

# Grupos de sinônimos usados nas pesquisas
GRUPOS = (
    {
        "arrependi", "arrependimento",
        "devolver", "devolucao", "devolucoes",
        "reembolso", "desistir"
    },
    {
        "troca", "trocas", "trocar", "substituir"
    },
    {
        "horario", "horarios", "abre", "abrem",
        "fecha", "fecham", "funcionamento",
        "expediente"
    },
    {
        "endereco", "localizacao",
        "rua", "onde", "fica", "situada"
    },
    {
        "parcelar", "parcelamento",
        "parcela", "parcelas", "vezes",
        "cartao", "credito"
    },
    {
        "entrega", "entregas", "frete",
        "enviar", "envio", "transportadora"
    },
    {
        "rastrear", "rastreamento",
        "codigo", "correios", "jadlog"
    },
    {
        "garantia", "defeito", "defeitos",
        "quebrou", "reparo"
    },
    {
        "promocao", "promocoes",
        "desconto", "descontos", "pix"
    },
    {
        "whatsapp", "telefone",
        "contato", "ligar"
    },
)

# Identifica títulos como:
# 4. Política de Trocas
# 4.1 Direito de Arrependimento
TITULO_RE = re.compile(
    r"^(\d{1,2}\.\d+|\d{1,2}\.)\s+(.+)$"
)


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize(
        "NFKD", texto.casefold()
    )

    return "".join(
        c for c in texto
        if not unicodedata.combining(c)
    )


def _tokens(texto: str) -> set[str]:
    return {
        palavra
        for palavra in re.findall(
            r"[a-z0-9]+",
            _normalizar(texto)
        )
        if len(palavra) >= 3
        and palavra not in STOPWORDS
    }


def _expandir(termos: set[str]) -> set[str]:
    resultado = termos.copy()

    for grupo in GRUPOS:
        if termos & grupo:
            resultado.update(grupo)

    return resultado


@lru_cache(maxsize=4)
def _extrair_secoes(
    caminho: str,
    modificacao: int
) -> tuple[dict, ...]:
    """
    Extrai seções do PDF preservando
    referências às páginas originais.
    """

    secoes = []
    atual = None

    with pymupdf.open(caminho) as documento:

        for numero_pagina, pagina in enumerate(
            documento, start=1
        ):

            # Página 1 é a capa
            if numero_pagina == 1:
                continue

            linhas = pagina.get_text(
                "text", sort=True
            ).splitlines()

            for linha in linhas:
                limpa = (
                    linha.strip()
                    .replace("\u200b", "")
                )

                if not limpa:
                    continue

                # Remove cabeçalho e numeração
                if (
                    "Empório da Música Manual de Políticas"
                    in limpa
                ):
                    continue

                if re.fullmatch(
                    r"Página \d+", limpa
                ):
                    continue

                # Títulos não são indentados
                titulo = (
                    TITULO_RE.match(linha)
                    if linha == linha.lstrip()
                    else None
                )

                if titulo:
                    if atual is not None:
                        atual["texto"] = " ".join(
                            atual["partes"]
                        )
                        del atual["partes"]
                        secoes.append(atual)

                    atual = {
                        "secao": titulo.group(1).rstrip("."),
                        "titulo": titulo.group(2),
                        "pagina_inicial": numero_pagina,
                        "pagina_final": numero_pagina,
                        "partes": [],
                    }
                    continue

                if atual is not None:
                    atual["partes"].append(
                        re.sub(r"\s+", " ", limpa)
                    )

                    atual["pagina_final"] = numero_pagina

    if atual is not None:
        atual["texto"] = " ".join(
            atual["partes"]
        )
        del atual["partes"]
        secoes.append(atual)

    return tuple(secoes)


def recuperar_secoes(
    caminho: Path,
    pergunta: str,
    limite: int = 3
) -> list[dict]:
    """
    Recupera os trechos documentais
    mais relacionados à pergunta.
    """

    if not caminho.is_file():
        raise FileNotFoundError(
            f"Manual não encontrado: {caminho}"
        )

    if not pergunta or not pergunta.strip():
        return []

    if not 1 <= limite <= 5:
        raise ValueError(
            "O limite deve estar entre 1 e 5."
        )

    termos = _expandir(_tokens(pergunta))

    if not termos:
        return []

    secoes = _extrair_secoes(
        str(caminho),
        caminho.stat().st_mtime_ns
    )

    resultados = []

    for secao in secoes:

        titulo = _tokens(secao["titulo"])
        texto = _tokens(secao["texto"])

        # Maior peso para correspondências no título
        relevancia = (
            4 * len(termos & titulo)
            + len(termos & texto)
        )

        if relevancia > 0 and secao["texto"]:
            resultados.append(
                (relevancia, secao)
            )

    resultados.sort(
        key=lambda item: (
            -item[0],
            item[1]["secao"]
        )
    )

    return [
        {
            "secao": (
                f'{s["secao"]} {s["titulo"]}'
            ),
            "pagina_inicial": s["pagina_inicial"],
            "pagina_final": s["pagina_final"],
            "trecho": s["texto"],
        }
        for _, s in resultados[:limite]
    ]
