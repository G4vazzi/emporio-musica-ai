
"""Testes do agente Ollama sem consumir recursos do modelo."""

from types import SimpleNamespace

from app.agent import (
    AtendenteIA,
    FERRAMENTAS,
    executar_ferramenta,
)


class ClienteFalso:
    def __init__(self, respostas):
        self.respostas = iter(respostas)
        self.chamadas = []

    def chat(self, **kwargs):
        self.chamadas.append(kwargs)
        return next(self.respostas)


def resposta_falsa(conteudo="", ferramentas=None):
    return SimpleNamespace(
        message=SimpleNamespace(
            content=conteudo,
            tool_calls=ferramentas or [],
        )
    )


def test_resposta_sem_ferramentas():
    cliente = ClienteFalso([
        resposta_falsa("Olá! Como posso ajudar?")
    ])

    agente = AtendenteIA(client=cliente)

    resultado = agente.responder("Oi")

    assert "Olá" in resultado
    assert len(agente.historico) == 2
    assert cliente.chamadas[0]["model"] == agente.modelo


def test_function_calling(monkeypatch):

    monkeypatch.setitem(
        FERRAMENTAS,
        "buscar_produtos",
        lambda **kwargs: {
            "total_encontrados": 1,
            "produtos": [
                {
                    "nome": "Violão de teste",
                    "preco_atual": "R$ 500,00",
                }
            ],
        },
    )

    chamada = SimpleNamespace(
        function=SimpleNamespace(
            name="buscar_produtos",
            arguments={
                "categoria": "violões",
                "preco_maximo": 1000,
            },
        )
    )

    cliente = ClienteFalso([
        resposta_falsa(ferramentas=[chamada]),
        resposta_falsa(
            "Temos um violão por R$ 500,00."
        ),
    ])

    agente = AtendenteIA(client=cliente)

    resultado = agente.responder(
        "Tem violões até mil reais?"
    )

    assert "500,00" in resultado
    assert len(cliente.chamadas) == 2

    mensagens = cliente.chamadas[1]["messages"]

    assert mensagens[-1]["role"] == "tool"
    assert mensagens[-1]["tool_name"] == "buscar_produtos"
    assert "Violão de teste" in mensagens[-1]["content"]


def test_ferramenta_nao_autorizada():
    resultado = executar_ferramenta(
        "excluir_pedido",
        {"numero_pedido": 1},
    )

    assert "erro" in resultado


def test_selecao_numerica_consulta_produto(monkeypatch):

    cliente = ClienteFalso([])
    agente = AtendenteIA(client=cliente)

    agente.ultima_lista = [
        {
            "product_id": 81,
            "nome": "Yamaha C40 Nylon Natural"
        }
    ]

    monkeypatch.setitem(
        FERRAMENTAS,
        "consultar_produto",
        lambda produto_id: {
            "nome": "Yamaha C40 Nylon Natural",
            "preco_atual": "R$ 599,90",
            "estoque": 12,
            "disponivel": True,
            "descricao": "Violão clássico para iniciantes.",
            "especificacoes": {"strings": "nylon"},
        },
    )

    texto = agente.responder("1")

    assert "Yamaha C40" in texto
    assert "599,90" in texto
    assert "nylon" in texto.lower()

    # A seleção funciona sem chamar o LLM
    assert cliente.chamadas == []
