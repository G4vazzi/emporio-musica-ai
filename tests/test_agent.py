
"""Testes do agente Ollama sem consumir recursos do modelo."""

from types import SimpleNamespace
from app.agent import ajustar_filtros_produtos

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
                    "product_id": 1,
                    "nome": "Violão de teste",
                    "preco_atual": "R$ 500,00",
                    "estoque": 3,
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
        resposta_falsa(ferramentas=[chamada])
    ])

    agente = AtendenteIA(client=cliente)

    resultado = agente.responder(
        "Tem violões até mil reais?"
    )

    assert "Violão de teste" in resultado
    assert "R$ 500,00" in resultado
    assert len(cliente.chamadas) == 1
    assert len(agente.ultima_lista) == 1



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


def test_corrigir_categoria_gerada_pelo_modelo():

    argumentos = {
        "categoria": "viola",
        "preco_maximo": 1000,
        "limite": 5,
    }

    resultado = ajustar_filtros_produtos(
        "Quais violões vocês têm disponíveis por até R$ 1.000?",
        argumentos
    )

    assert resultado["categoria"] == "violões"
    assert resultado["preco_maximo"] == 1000

    # A função não modifica os argumentos originais
    assert argumentos["categoria"] == "viola"


def test_nao_confundir_viola_com_violao():

    argumentos = {
        "categoria": "viola",
        "preco_maximo": 1000,
    }

    resultado = ajustar_filtros_produtos(
        "Vocês vendem viola?",
        argumentos
    )

    assert resultado["categoria"] == "viola"


def test_politica_nao_encontrada_sem_alucinacao(monkeypatch):
    monkeypatch.setitem(
        FERRAMENTAS,
        "consultar_politicas",
        lambda **kwargs: {
            "encontrado": False,
            "resultados": [],
        },
    )

    chamada = SimpleNamespace(
        function=SimpleNamespace(
            name="consultar_politicas",
            arguments={"pergunta": "Posso cancelar?"},
        )
    )

    cliente = ClienteFalso([
        resposta_falsa(ferramentas=[chamada]),
    ])

    agente = AtendenteIA(client=cliente)

    texto = agente.responder(
        "Posso cancelar meu pedido?"
    )

    assert "não encontrei" in texto.lower()
    assert "manual" in texto.lower()

    # Não realiza outra chamada desnecessária ao LLM
    assert len(cliente.chamadas) == 1


def test_retorno_documental_uma_so_mensagem(monkeypatch):
    monkeypatch.setitem(
        FERRAMENTAS,
        "consultar_politicas",
        lambda **kwargs: {
            "encontrado": True,
            "resultados": [
                {
                    "secao": "2 Horários",
                    "trecho": "Sábado das 9 às 13",
                }
            ],
        },
    )

    chamada = SimpleNamespace(
        function=SimpleNamespace(
            name="consultar_politicas",
            arguments={"pergunta": "Horário de sábado"},
        )
    )

    primeira = resposta_falsa(
        ferramentas=[chamada]
    )

    cliente = ClienteFalso([
        primeira,
        resposta_falsa(
            "A loja funciona até as 13h aos sábados."
        ),
    ])

    agente = AtendenteIA(client=cliente)

    texto = agente.responder(
        "Qual é o horário de sábado?"
    )

    assert "13h" in texto

    mensagens = cliente.chamadas[1]["messages"]

    # A mensagem que chamou a ferramenta não se repete
    assert sum(
        m is primeira.message
        for m in mensagens
    ) == 1
