
import pytest

from app.database import connection, import_data
from app.tools.products import (
    buscar_produtos,
    consultar_produto,
)


@pytest.fixture(scope="module", autouse=True)
def banco_de_teste(tmp_path_factory):
    original_path = connection.DB_PATH

    connection.DB_PATH = (
        tmp_path_factory.mktemp("emporio") / "teste.db"
    )

    try:
        import_data.import_data()
        yield
    finally:
        connection.DB_PATH = original_path


def test_busca_violoes_ate_mil_reais():
    resposta = buscar_produtos(
        categoria="violões",
        preco_maximo=1000
    )

    assert resposta["total_encontrados"] > 0

    assert all(
        p["disponivel"]
        for p in resposta["produtos"]
    )

    assert all(
        p["preco_atual_centavos"] <= 100000
        for p in resposta["produtos"]
    )


def test_consultar_takamine_gd20():
    produto = consultar_produto(nome="Takamine GD20")

    assert produto["product_id"] == 95
    assert produto["preco_tabela"] == "R$ 2.199,00"
    assert produto["preco_pix"] == "R$ 2.089,05"
    assert produto["disponivel"]


def test_promocao_ativa_nao_acumula_pix():
    produto = consultar_produto(produto_id=121)

    assert produto["desconto_percentual"] == 20
    assert produto["preco_atual"] == "R$ 439,20"
    assert produto["preco_pix"] is None


def test_produto_sem_estoque_nao_e_oferecido():
    produto = consultar_produto(produto_id=96)

    assert produto["disponivel"] is False

    encontrados = buscar_produtos(
        termo="Giannini GF-3D"
    )

    assert encontrados["total_encontrados"] == 0


def test_produto_descontinuado_com_estoque_indisponivel():
    produto = consultar_produto(produto_id=136)

    assert produto["estoque"] > 0
    assert produto["disponivel"] is False


def test_erro_sem_identificador():
    assert "erro" in consultar_produto()
