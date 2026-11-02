
from types import SimpleNamespace

from app.agent import AtendenteIA, FERRAMENTAS
from app.guardrails import (
    fonte_obrigatoria,
    resposta_politica_documentada,
    consultar_lista_categorias,
)


class ClienteFalso:
    def __init__(self, respostas):
        self.respostas = iter(respostas)
        self.chamadas = []

    def chat(self, **kwargs):
        self.chamadas.append(kwargs)
        return next(self.respostas)


def resposta(conteudo="", ferramentas=None):
    return SimpleNamespace(
        message=SimpleNamespace(
            content=conteudo,
            tool_calls=ferramentas or [],
        )
    )


def test_roteamento_por_assunto():
    assert fonte_obrigatoria(
        "Posso cancelar meu pedido?"
    ) == "consultar_politicas"

    assert fonte_obrigatoria(
        "Me arrependi da compra online"
    ) == "consultar_politicas"

    assert fonte_obrigatoria(
        "Vocês vendem amplificadores?"
    ) == "buscar_produtos"

    assert fonte_obrigatoria("Oi, tudo bem?") is None


def test_arrependimento_usa_secao_correta():
    documento = {
        "encontrado": True,
        "resultados": [
            {
                "secao": "4.3 Trocas por Preferência",
                "pagina_inicial": 4,
                "trecho": "Troca em 7 dias.",
            },
            {
                "secao": "4.1 Direito de Arrependimento",
                "pagina_inicial": 4,
                "trecho": "Devolução em 7 dias corridos.",
            },
        ],
    }

    texto = resposta_politica_documentada(
        "Me arrependi da compra online",
        documento
    )

    assert "4.1" in texto
    assert "Devolução em 7 dias" in texto
    assert "4.3" not in texto


def test_consulta_multipla_sem_itens_disponiveis():
    def ferramenta(nome, argumentos):
        return {
            "total_encontrados": 0,
            "produtos": [],
        }

    texto = consultar_lista_categorias(
        "Vocês vendem amplificadores e pedais?",
        ferramenta
    )

    assert "amplificadores" in texto.lower()
    assert "pedais" in texto.lower()
    assert texto.count("não encontrei") == 2


def test_cancelamento_sem_tool_call(monkeypatch):
    consultas = []

    def politica(**kwargs):
        consultas.append(kwargs)
        return {
            "encontrado": False,
            "resultados": [],
        }

    monkeypatch.setitem(
        FERRAMENTAS,
        "consultar_politicas",
        politica
    )

    cliente = ClienteFalso([
        resposta("Me informe o número do pedido.")
    ])

    texto = AtendenteIA(client=cliente).responder(
        "Posso cancelar meu pedido?"
    )

    assert "Não encontrei" in texto
    assert len(consultas) == 1


def test_cancelamento_com_ferramenta_errada(monkeypatch):
    chamada = SimpleNamespace(
        function=SimpleNamespace(
            name="consultar_pedido",
            arguments={
                "numero_pedido": 8,
                "email_cliente": "exemplo@teste.invalid",
            },
        )
    )

    cliente = ClienteFalso([
        resposta(ferramentas=[chamada])
    ])

    monkeypatch.setitem(
        FERRAMENTAS,
        "consultar_politicas",
        lambda **kwargs: {
            "encontrado": False,
            "resultados": [],
        },
    )

    def pedido(**kwargs):
        raise AssertionError(
            "Não deveria consultar o pedido"
        )

    monkeypatch.setitem(
        FERRAMENTAS,
        "consultar_pedido",
        pedido
    )

    texto = AtendenteIA(client=cliente).responder(
        "Posso cancelar meu pedido?"
    )

    assert "Não encontrei" in texto
    assert len(cliente.chamadas) == 1


def test_catalogo_sem_tool_call_nao_inventa():
    cliente = ClienteFalso([
        resposta("Sim, vendemos violões."),
        resposta("Sim, temos violões disponíveis."),
    ])

    texto = AtendenteIA(client=cliente).responder(
        "Vocês vendem violões?"
    )

    assert "Não consegui verificar" in texto
    assert len(cliente.chamadas) == 2
