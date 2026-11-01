
"""Agente local da Empório da Música com Ollama."""

import json
import os
import sqlite3
from pathlib import Path

import httpx
from dotenv import load_dotenv
from ollama import Client, ResponseError

from app.prompts import INSTRUCOES_SISTEMA
from app.tools.products import buscar_produtos, consultar_produto
from app.tools.orders import consultar_pedido
from app.tools.policies import consultar_politicas


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


# Funções autorizadas: nenhuma altera o banco.
FERRAMENTAS = {
    "buscar_produtos": buscar_produtos,
    "consultar_produto": consultar_produto,
    "consultar_pedido": consultar_pedido,
    "consultar_politicas": consultar_politicas,
}


def criar_definicao(nome, descricao, propriedades, obrigatorios):
    return {
        "type": "function",
        "function": {
            "name": nome,
            "description": descricao,
            "parameters": {
                "type": "object",
                "properties": propriedades,
                "required": obrigatorios,
            },
        },
    }


DEFINICOES_FERRAMENTAS = [
    criar_definicao(
        "buscar_produtos",
        "Busca instrumentos por nome, categoria, orçamento e estoque.",
        {
            "termo": {
                "type": "string",
                "description": "Parte do nome do produto.",
            },
            "categoria": {
                "type": "string",
                "description": "Categoria, como violões ou guitarras.",
            },
            "preco_maximo": {
                "type": "number",
                "description": "Preço máximo em reais.",
            },
            "apenas_disponiveis": {
                "type": "boolean",
                "description": "Use true para produtos disponíveis.",
            },
            "limite": {
                "type": "integer",
                "description": "Máximo de 10 produtos.",
            },
        },
        [],
    ),
    criar_definicao(
        "consultar_produto",
        "Consulta preço, estoque e detalhes de um produto específico.",
        {
            "produto_id": {
                "type": "integer",
                "description": "ID numérico do produto.",
            },
            "nome": {
                "type": "string",
                "description": "Nome ou modelo do instrumento.",
            },
        },
        [],
    ),
    criar_definicao(
        "consultar_pedido",
        "Consulta pedido histórico mediante número e e-mail informado.",
        {
            "numero_pedido": {
                "type": "integer",
                "description": "Número do pedido.",
            },
            "email_cliente": {
                "type": "string",
                "description": "E-mail cadastrado informado pelo cliente.",
            },
        },
        ["numero_pedido", "email_cliente"],
    ),
    criar_definicao(
        "consultar_politicas",
        "Busca regras de trocas, horários, frete, pagamento e garantia.",
        {
            "pergunta": {
                "type": "string",
                "description": "Assunto a consultar no manual.",
            },
            "limite": {
                "type": "integer",
                "description": "Quantidade de seções, entre 1 e 3.",
            },
        },
        ["pergunta"],
    ),
]


def executar_ferramenta(nome: str, argumentos: dict) -> dict:
    """Executa apenas funções permitidas."""

    funcao = FERRAMENTAS.get(nome)

    if funcao is None:
        return {"erro": "Ferramenta não autorizada."}

    if not isinstance(argumentos, dict):
        return {"erro": "Argumentos inválidos."}

    try:
        if nome == "buscar_produtos":
            argumentos.setdefault("apenas_disponiveis", True)
            argumentos.setdefault("limite", 10)

        if nome == "consultar_politicas":
            argumentos.setdefault("limite", 3)

        return funcao(**argumentos)

    except (
        TypeError,
        ValueError,
        FileNotFoundError,
        OverflowError,
        sqlite3.Error,
    ):
        return {
            "erro": "Não foi possível realizar essa consulta."
        }


class AtendenteIA:

    def __init__(self, client=None):
        self.modelo = os.getenv(
            "OLLAMA_MODEL", "qwen2.5:7b"
        )

        self.max_historico = max(
            2,
            int(os.getenv("MAX_HISTORY_MESSAGES", "12"))
        )

        self.historico = []

        self.client = client or Client(
            host=os.getenv(
                "OLLAMA_HOST", "http://127.0.0.1:11434"
            ),
            timeout=120.0,
        )

    def limpar_historico(self):
        self.historico.clear()

    def _chamar_modelo(self, mensagens, ferramentas):
        return self.client.chat(
            model=self.modelo,
            messages=mensagens,
            tools=ferramentas,
            stream=False,
            options={
                "temperature": 0.2,
                "num_ctx": 8192,
            },
        )

    def _finalizar(self, pergunta, resposta):
        resposta = (resposta or "").strip()

        if not resposta:
            return (
                "Não consegui formular uma resposta. "
                "Pode reformular sua pergunta?"
            )

        self.historico.extend([
            {"role": "user", "content": pergunta},
            {"role": "assistant", "content": resposta},
        ])

        self.historico = self.historico[
            -self.max_historico:
        ]

        return resposta

    def responder(self, mensagem: str) -> str:

        if not isinstance(mensagem, str) or not mensagem.strip():
            return "Envie uma pergunta para começarmos."

        mensagem = mensagem.strip()

        mensagens = [
            {
                "role": "system",
                "content": INSTRUCOES_SISTEMA,
            },
            *self.historico[-self.max_historico:],
            {
                "role": "user",
                "content": mensagem,
            },
        ]

        try:
            # No máximo quatro rodadas de consultas.
            for _ in range(4):

                resposta = self._chamar_modelo(
                    mensagens,
                    DEFINICOES_FERRAMENTAS,
                )

                chamadas = resposta.message.tool_calls or []

                if not chamadas:
                    return self._finalizar(
                        mensagem,
                        resposta.message.content,
                    )

                # Guarda a chamada antes de devolver
                # os resultados das ferramentas.
                mensagens.append(resposta.message)

                for chamada in chamadas:

                    nome = chamada.function.name
                    argumentos = chamada.function.arguments

                    # Compatível com argumentos em JSON
                    # ou dicionário Python.
                    if isinstance(argumentos, str):
                        try:
                            argumentos = json.loads(argumentos)
                        except json.JSONDecodeError:
                            argumentos = {}

                    print(f"[Ferramenta] {nome}")

                    resultado = executar_ferramenta(
                        nome, argumentos
                    )

                    mensagens.append({
                        "role": "tool",
                        "tool_name": nome,
                        "content": json.dumps(
                            resultado,
                            ensure_ascii=False,
                            default=str,
                        ),
                    })

            # Após quatro rodadas, pede uma resposta
            # final sem disponibilizar novas ferramentas.
            resposta = self._chamar_modelo(
                mensagens, []
            )

            return self._finalizar(
                mensagem,
                resposta.message.content,
            )

        except ResponseError as erro:

            if erro.status_code == 404:
                return (
                    f"O modelo {self.modelo} não foi encontrado. "
                    f"Execute: ollama pull {self.modelo}"
                )

            return (
                f"Erro no Ollama (HTTP {erro.status_code}). "
                "Confira o terminal e a configuração do modelo."
            )

        except httpx.ConnectError:
            return (
                "Não consegui conectar ao Ollama. "
                "Verifique se ele está iniciado no Windows."
            )

        except httpx.TimeoutException:
            return (
                "O modelo demorou demais para responder. "
                "Tente uma pergunta mais simples."
            )
