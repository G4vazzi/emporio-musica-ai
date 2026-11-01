
"""Consultas de pedidos históricos da Empório da Música."""

from contextlib import closing
from datetime import date
from decimal import Decimal

from app.database.connection import get_connection


STATUS_PT = {
    "pending": "Pendente",
    "confirmed": "Confirmado",
    "shipped": "Enviado",
    "delivered": "Entregue",
    "cancelled": "Cancelado",
}

PAGAMENTO_PT = {
    "pix": "PIX",
    "debit": "Cartão de débito",
    "boleto": "Boleto bancário",
    "credit_3x": "Cartão de crédito (3x)",
    "credit_6x": "Cartão de crédito (6x)",
    "credit_12x": "Cartão de crédito (12x)",
}

RESPOSTA_NAO_ENCONTRADO = {
    "erro": (
        "Pedido não encontrado ou dados "
        "de conferência não correspondem."
    )
}


def _formatar_moeda(centavos: int) -> str:
    valor = f"{Decimal(centavos) / 100:,.2f}"

    return (
        "R$ "
        + valor.replace(",", "#")
               .replace(".", ",")
               .replace("#", ".")
    )


def _formatar_data(valor: str | None) -> str | None:
    if not valor:
        return None

    return date.fromisoformat(valor).strftime("%d/%m/%Y")


def consultar_pedido(
    numero_pedido: int,
    email_cliente: str
) -> dict:
    """
    Consulta um pedido por número e e-mail cadastrado.

    ATENÇÃO:
    A conferência por e-mail é apenas uma medida básica
    para este protótipo. Em produção, implementar
    autenticação com código de uso único (OTP).
    """

    # Validar os parâmetros
    numero_valido = (
        isinstance(numero_pedido, int)
        and not isinstance(numero_pedido, bool)
    ) or (
        isinstance(numero_pedido, str)
        and numero_pedido.strip().isdigit()
    )

    if not numero_valido:
        return RESPOSTA_NAO_ENCONTRADO.copy()

    pedido_id = int(numero_pedido)

    if (
        pedido_id <= 0
        or not isinstance(email_cliente, str)
        or not email_cliente.strip()
    ):
        return RESPOSTA_NAO_ENCONTRADO.copy()

    with closing(get_connection()) as conexao:

        # Buscar pedido conferindo o e-mail
        pedido = conexao.execute(
            """
            SELECT
                o.order_id,
                o.order_date,
                o.status,
                o.total_cents,
                o.payment_method,
                o.tracking_code,
                o.estimated_delivery
            FROM orders AS o
            INNER JOIN customers AS c
                ON c.customer_id = o.customer_id
            WHERE o.order_id = ?
              AND LOWER(TRIM(c.email)) = LOWER(TRIM(?))
            """,
            (pedido_id, email_cliente)
        ).fetchone()

        if pedido is None:
            return RESPOSTA_NAO_ENCONTRADO.copy()

        # Buscar os instrumentos do pedido
        itens = conexao.execute(
            """
            SELECT
                p.name AS nome_produto,
                oi.quantity AS quantidade
            FROM order_items AS oi
            INNER JOIN products AS p
                ON p.product_id = oi.product_id
            WHERE oi.order_id = ?
            ORDER BY p.name
            """,
            (pedido_id,)
        ).fetchall()

    # Preparar resposta sem dados pessoais
    return {
        "numero_pedido": pedido["order_id"],
        "data_pedido": _formatar_data(
            pedido["order_date"]
        ),
        "status_registrado": STATUS_PT.get(
            pedido["status"], "Não identificado"
        ),
        "valor_total_registrado": _formatar_moeda(
            pedido["total_cents"]
        ),
        "forma_pagamento": PAGAMENTO_PT.get(
            pedido["payment_method"], "Não informada"
        ),
        "codigo_rastreamento": (
            pedido["tracking_code"] or None
        ),
        "previsao_entrega_registrada": _formatar_data(
            pedido["estimated_delivery"]
        ),
        "itens": [
            {
                "produto": item["nome_produto"],
                "quantidade": item["quantidade"],
            }
            for item in itens
        ],
        "aviso": (
            "Informações de um arquivo histórico de "
            "demonstração. O status e a previsão não "
            "foram confirmados em tempo real."
        ),
    }
