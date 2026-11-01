
"""Consultas de catálogo e preço da Empório da Música."""

import json
import unicodedata
from contextlib import closing
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from app.database.connection import get_connection


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(
        c for c in texto if not unicodedata.combining(c)
    ).strip()


def _moeda(centavos: int) -> str:
    numero = f"{Decimal(centavos) / 100:,.2f}"
    return "R$ " + numero.replace(
        ",", "#"
    ).replace(".", ",").replace("#", ".")


def _aplicar_desconto(centavos: int, percentual: int) -> int:
    return int(
        (
            Decimal(centavos) * (100 - percentual) / 100
        ).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )


def _catalogo() -> list[dict]:
    sql = """
        SELECT
            p.product_id,
            p.name,
            p.description,
            p.price_cents,
            p.stock_quantity,
            p.status,
            p.specs,
            c.name AS categoria,
            COALESCE((
                SELECT MAX(pr.discount_percent)
                FROM promotions AS pr
                WHERE pr.product_id = p.product_id
                  AND pr.is_active = 1
            ), 0) AS desconto_percentual
        FROM products AS p
        JOIN categories AS c
          ON c.category_id = p.category_id
    """

    with closing(get_connection()) as conn:
        return [
            dict(row)
            for row in conn.execute(sql).fetchall()
        ]


def _formatar_produto(
    registro: dict,
    detalhado: bool = False
) -> dict:

    tabela = registro["price_cents"]
    desconto = registro["desconto_percentual"]
    atual = _aplicar_desconto(tabela, desconto)

    disponivel = (
        registro["status"] == "active"
        and registro["stock_quantity"] > 0
    )

    produto = {
        "product_id": registro["product_id"],
        "nome": registro["name"],
        "categoria": registro["categoria"],
        "status": registro["status"],
        "estoque": registro["stock_quantity"],
        "disponivel": disponivel,
        "preco_tabela": _moeda(tabela),
        "preco_atual": _moeda(atual),
        "preco_atual_centavos": atual,
        "promocao_ativa": desconto > 0,
        "desconto_percentual": desconto,
        "preco_pix": (
            None if desconto > 0
            else _moeda(_aplicar_desconto(tabela, 5))
        ),
    }

    if detalhado:
        produto["descricao"] = registro["description"]
        produto["especificacoes"] = json.loads(
            registro["specs"] or "{}"
        )

    return produto


def buscar_produtos(
    termo: str | None = None,
    categoria: str | None = None,
    preco_maximo: float | None = None,
    apenas_disponiveis: bool = True,
    limite: int = 10,
) -> dict:
    """
    Pesquisa produtos por nome, categoria,
    preço máximo (em reais) e disponibilidade.
    """

    if not 1 <= limite <= 30:
        raise ValueError("O limite deve estar entre 1 e 30.")

    teto_centavos = None

    if preco_maximo is not None:
        try:
            teto = Decimal(str(preco_maximo))
        except InvalidOperation as exc:
            raise ValueError(
                "Preço máximo inválido."
            ) from exc

        if not teto.is_finite() or teto < 0:
            raise ValueError(
                "Preço máximo deve ser um número não negativo."
            )

        teto_centavos = int(
            (teto * 100).quantize(
                Decimal("1"),
                rounding=ROUND_HALF_UP
            )
        )

    alias_categorias = {
        "violao": "violoes",
        "guitarra": "guitarras",
        "baixo": "baixos",
        "ukulele": "ukuleles",
        "bateria": "baterias",
        "teclado": "teclados",
    }

    filtro_categoria = (
        _normalizar(categoria) if categoria else None
    )

    filtro_categoria = alias_categorias.get(
        filtro_categoria, filtro_categoria
    )

    filtro_termo = _normalizar(termo) if termo else None

    encontrados = []

    for registro in _catalogo():
        produto = _formatar_produto(registro)

        if apenas_disponiveis and not produto["disponivel"]:
            continue

        if (
            filtro_categoria
            and filtro_categoria not in _normalizar(
                produto["categoria"]
            )
        ):
            continue

        if (
            filtro_termo
            and filtro_termo not in _normalizar(
                produto["nome"]
            )
        ):
            continue

        if (
            teto_centavos is not None
            and produto["preco_atual_centavos"] > teto_centavos
        ):
            continue

        encontrados.append(produto)

    encontrados.sort(
        key=lambda p: (
            p["preco_atual_centavos"],
            p["nome"]
        )
    )

    return {
        "total_encontrados": len(encontrados),
        "produtos": encontrados[:limite]
    }


def consultar_produto(
    produto_id: int | None = None,
    nome: str | None = None
) -> dict:
    """
    Consulta um produto por ID ou nome.
    Não escolhe um produto se houver ambiguidade.
    """

    if produto_id is None and not (nome and nome.strip()):
        return {
            "erro": "Informe produto_id ou nome para consultar."
        }

    catalogo = _catalogo()

    if produto_id is not None:
        encontrados = [
            r for r in catalogo
            if r["product_id"] == produto_id
        ]

    else:
        termo = _normalizar(nome)

        exatos = [
            r for r in catalogo
            if _normalizar(r["name"]) == termo
        ]

        encontrados = exatos or [
            r for r in catalogo
            if termo in _normalizar(r["name"])
        ]

    if not encontrados:
        return {
            "erro": "Produto não encontrado no catálogo."
        }

    if len(encontrados) > 1:
        return {
            "erro": (
                "Mais de um produto encontrado; "
                "especifique o modelo."
            ),
            "opcoes": [
                {
                    "product_id": r["product_id"],
                    "nome": r["name"]
                }
                for r in encontrados[:10]
            ]
        }

    return _formatar_produto(
        encontrados[0], detalhado=True
    )
