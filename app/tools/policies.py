
"""Ferramenta de consulta às políticas da loja."""

import os
from pathlib import Path

from dotenv import load_dotenv

from app.services.retrieval import recuperar_secoes


PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


def consultar_politicas(
    pergunta: str,
    limite: int = 3
) -> dict:
    """
    Busca trechos relevantes no manual.

    Retorna texto e páginas de origem.
    Não gera uma resposta com LLM.
    """

    if (
        not isinstance(pergunta, str)
        or not pergunta.strip()
    ):
        return {
            "erro": (
                "Informe uma pergunta para "
                "consultar as políticas."
            )
        }

    configurado = Path(
        os.getenv(
            "POLICIES_PATH",
            "data/politicas_da_loja.pdf"
        )
    )

    caminho = (
        configurado
        if configurado.is_absolute()
        else PROJECT_ROOT / configurado
    )

    resultados = recuperar_secoes(
        caminho,
        pergunta,
        limite
    )

    return {
        "pergunta": pergunta,
        "fonte": (
            "Manual de Políticas e Procedimentos, "
            "v2.1 (junho/2025)"
        ),
        "encontrado": bool(resultados),
        "resultados": resultados,
        "observacao": (
            "São trechos do manual, não uma "
            "resposta final. Em caso de dúvida "
            "ou divergência, encaminhar à gerência."
        ),
    }
