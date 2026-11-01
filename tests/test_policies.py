
import pytest

from app.tools.policies import consultar_politicas


def test_arrependimento_compra_online():
    resultado = consultar_politicas(
        "Me arrependi da compra online, posso devolver?"
    )

    assert resultado["encontrado"]

    trecho = resultado["resultados"][0]

    assert trecho["secao"].startswith("4.1")
    assert "7 (sete) dias corridos" in trecho["trecho"]
    assert trecho["pagina_inicial"] == 4


def test_horario_sabado():
    resultado = consultar_politicas(
        "Que horas abre no sábado?"
    )

    trecho = resultado["resultados"][0]

    assert trecho["secao"].startswith("2 ")
    assert "09:00 às 13:00" in trecho["trecho"]


def test_parcelamento():
    resultado = consultar_politicas(
        "Posso parcelar em 12 vezes no cartão?"
    )

    primeiro = resultado["resultados"][0]

    assert primeiro["secao"].startswith("3.1")
    assert "7x a 12x" in primeiro["trecho"]


def test_frete_outras_cidades():
    resultado = consultar_politicas(
        "Como funciona a entrega para outras cidades?"
    )

    trecho = resultado["resultados"][0]

    assert trecho["secao"].startswith("5.2")
    assert trecho["pagina_inicial"] == 4
    assert trecho["pagina_final"] == 5
    assert "SEDEX" in trecho["trecho"]


def test_desconto_pix_nao_cumulativo():
    resultado = consultar_politicas(
        "Posso acumular desconto no PIX com promoção?"
    )

    assert any(
        "não se aplica" in item["trecho"]
        for item in resultado["resultados"]
    )


def test_contato_fontes_diferentes():
    resultado = consultar_politicas(
        "Qual é o WhatsApp da loja?"
    )

    secoes = [
        item["secao"]
        for item in resultado["resultados"]
    ]

    assert any(
        s.startswith("1.2") for s in secoes
    )

    assert any(
        s.startswith("7 ") for s in secoes
    )


def test_pergunta_fora_do_escopo():
    resultado = consultar_politicas(
        "Qual é a receita de bolo de chocolate?"
    )

    assert resultado["encontrado"] is False
    assert resultado["resultados"] == []


def test_pergunta_vazia():
    resultado = consultar_politicas("   ")

    assert "erro" in resultado


def test_manual_inexistente(
    monkeypatch,
    tmp_path
):
    monkeypatch.setenv(
        "POLICIES_PATH",
        str(tmp_path / "nao-existe.pdf")
    )

    with pytest.raises(FileNotFoundError):
        consultar_politicas(
            "Qual é o horário da loja?"
        )
