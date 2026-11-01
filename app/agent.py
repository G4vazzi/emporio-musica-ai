
"""Agente local da Empório da Música com Ollama."""

import json
import os
import sqlite3
import time
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
            argumentos.setdefault("limite", 5)

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
            "OLLAMA_MODEL", "qwen2.5:3b"
        )

        self.max_historico = max(
            2,
            int(os.getenv("MAX_HISTORY_MESSAGES", "12"))
        )

        self.historico = []
        self.ultima_lista = []

        self.client = client if client is not None else Client(
            host=os.getenv(
                "OLLAMA_HOST",
                "http://127.0.0.1:11434"
            ),
            timeout=240.0,
        )

    def limpar_historico(self):
        self.historico.clear()
        self.ultima_lista.clear()

    def _chamar_modelo(self, mensagens, ferramentas):

        from time import perf_counter

        inicio = perf_counter()

        print(
            "\n[IA] Processando solicitação...",
            flush=True
        )

        try:
            resposta = self.client.chat(
                model=self.modelo,
                messages=mensagens,
                tools=ferramentas,
                stream=False,
                keep_alive="10m",
                options={
                    "temperature": 0.2,
                    "num_ctx": 4096,
                    "num_predict": 384,
                },
            )

            return resposta

        finally:
            duracao = perf_counter() - inicio

            print(
                f"[IA] Tempo da chamada: {duracao:.2f}s",
                flush=True
            )

    def _finalizar(self, pergunta, resposta):

        resposta = (resposta or "").strip()

        if not resposta:
            return (
                "Não consegui formular uma resposta. "
                "Pode reformular sua pergunta?"
            )

        self.historico.extend([
            {
                "role": "user",
                "content": pergunta,
            },
            {
                "role": "assistant",
                "content": resposta,
            },
        ])

        self.historico = self.historico[
            -self.max_historico:
        ]

        return resposta

    def responder(self, mensagem: str) -> str:

        if not isinstance(mensagem, str) or not mensagem.strip():
            return "Envie uma pergunta para começarmos."

        mensagem = mensagem.strip()

        
        # Seleção direta de um produto da última lista
        if mensagem.isdecimal() and self.ultima_lista:

            indice = int(mensagem) - 1

            if not 0 <= indice < len(self.ultima_lista):
                return (
                    f"Escolha um número entre 1 e "
                    f"{len(self.ultima_lista)}."
                )

            item = self.ultima_lista[indice]

            print("[Ferramenta] consultar_produto")

            produto = executar_ferramenta(
                "consultar_produto",
                {"produto_id": item["product_id"]}
            )

            if "erro" in produto:
                return (
                    "Não consegui consultar esse instrumento. "
                    "Pode tentar novamente?"
                )

            linhas = [
                f"**{produto['nome']}**",
                f"Preço: {produto['preco_atual']}",
                (
                    f"Estoque: {produto['estoque']} unidades"
                    if produto["disponivel"]
                    else "Atualmente indisponível"
                ),
            ]

            if produto.get("descricao"):
                linhas.append(
                    f"\n{produto['descricao']}"
                )

            especificacoes = produto.get(
                "especificacoes", {}
            )

            if isinstance(especificacoes, dict) and especificacoes:
                linhas.append("\nEspecificações:")

                for chave, valor in list(
                    especificacoes.items()
                )[:5]:
                    linhas.append(
                        f"- {chave.replace('_', ' ').title()}: {valor}"
                    )

            linhas.append(
                "\nPosso ajudar com mais alguma informação?"
            )

            return self._finalizar(
                mensagem,
                "\n".join(linhas)
            )


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
            # Limita a quatro rodadas de ferramentas
            for rodada in range(4):

                print(
                    f"\n[Agente] Rodada {rodada + 1}/4"
                )

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

                mensagens.append(resposta.message)

                for chamada in chamadas:

                    nome = chamada.function.name
                    argumentos = chamada.function.arguments

                    if isinstance(argumentos, str):
                        try:
                            argumentos = json.loads(argumentos)
                        except json.JSONDecodeError:
                            argumentos = {}

                    print(
                        f"[Ferramenta] {nome}",
                        flush=True
                    )

                    if nome == "buscar_produtos":
                        print(
                            f"[DEBUG] Filtros recebidos: {argumentos}",
                            flush=True
                        )

                    resultado = executar_ferramenta(
                        nome,
                        argumentos,
                    )

                    if nome == "buscar_produtos":
                        print(
                            "[DEBUG] Total encontrado:",
                            resultado.get("total_encontrados", "ERRO")
                        )

                        print(
                            "[DEBUG] Produtos retornados:",
                            len(resultado.get("produtos", []))
                        )

                    if nome == "buscar_produtos":
                        self.ultima_lista = (
                            resultado.get("produtos", [])
                            if isinstance(resultado, dict)
                            else []
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

            print(
                "[Agente] Limite de ferramentas atingido."
            )

            # Resposta final sem novas chamadas
            resposta = self._chamar_modelo(
                mensagens,
                [],
            )

            return self._finalizar(
                mensagem,
                resposta.message.content,
            )

        except ResponseError as erro:

            if erro.status_code == 404:
                return (
                    f"Modelo {self.modelo} não encontrado. "
                    f"Execute: ollama pull {self.modelo}"
                )

            print(
                f"[Erro Ollama] HTTP {erro.status_code}"
            )

            return (
                "O Ollama não conseguiu processar "
                "sua solicitação."
            )

        except httpx.ConnectError:
            return (
                "Não consegui conectar ao Ollama. "
                "Verifique se está iniciado."
            )

        except httpx.TimeoutException:
            return (
                "O modelo demorou demais para responder. "
                "Verifique o desempenho do computador."
            )
