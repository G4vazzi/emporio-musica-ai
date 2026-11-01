
import pytest

from app.database import connection, import_data
from app.tools.orders import consultar_pedido


@pytest.fixture(autouse=True)
def banco_de_teste(tmp_path, monkeypatch):
    """
    Importa dados em um banco temporário.
    O banco principal não é alterado.
    """

    monkeypatch.setattr(
        connection,
        "DB_PATH",
        tmp_path / "orders_test.db"
    )

    import_data.import_data()


def test_pedido_entregue():
    pedido = consultar_pedido(
        1,
        "pedro.oliveira@jmail.com"
    )

    assert pedido["status_registrado"] == "Entregue"
    assert pedido["valor_total_registrado"] == "R$ 11.499,00"
    assert len(pedido["itens"]) == 1


def test_email_incorreto():
    pedido = consultar_pedido(
        1,
        "email.errado@exemplo.com"
    )

    assert "erro" in pedido


def test_pedido_inexistente():
    pedido = consultar_pedido(
        99999,
        "pedro.oliveira@jmail.com"
    )

    assert "erro" in pedido


def test_nao_revela_se_pedido_existe():
    incorreto = consultar_pedido(
        1,
        "email.errado@exemplo.com"
    )

    inexistente = consultar_pedido(
        99999,
        "pedro.oliveira@jmail.com"
    )

    assert incorreto == inexistente


def test_pedido_enviado_com_rastreamento():
    pedido = consultar_pedido(
        8,
        "anacarol.ferreira@coldmail.com"
    )

    assert pedido["status_registrado"] == "Enviado"
    assert pedido["codigo_rastreamento"] == "BRJL5544332BR"
    assert pedido["previsao_entrega_registrada"] == "28/02/2026"
    assert "tempo real" in pedido["aviso"]


def test_pedido_sem_rastreamento():
    pedido = consultar_pedido(
        9,
        "juliana.almeida@hayoo.com.br"
    )

    assert pedido["status_registrado"] == "Confirmado"
    assert pedido["codigo_rastreamento"] is None


def test_pedido_com_multiplos_produtos():
    pedido = consultar_pedido(
        15,
        "aline.monteiro@jmail.com"
    )

    assert len(pedido["itens"]) == 2
    assert pedido["valor_total_registrado"] == "R$ 8.348,00"


def test_nao_expoe_dados_pessoais():
    pedido = consultar_pedido(
        1,
        "pedro.oliveira@jmail.com"
    )

    assert "email" not in pedido
    assert "phone" not in pedido
    assert "customer_id" not in pedido
    assert "notes" not in pedido
