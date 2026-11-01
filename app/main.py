
"""Chat de atendimento via terminal."""

from app.agent import AtendenteIA


def main():

    try:
        atendente = AtendenteIA()

    except RuntimeError as erro:
        print(f"Configuração: {erro}")
        return

    print("\nEmpório da Música — Sua música começa aqui!")
    print("Digite /limpar para reiniciar ou /sair para encerrar.\n")

    while True:

        try:
            mensagem = input("Você: ").strip()

        except (KeyboardInterrupt, EOFError):
            print("\nAtendimento encerrado.")
            break

        if mensagem.lower() == "/sair":
            print("Atendimento encerrado.")
            break

        if mensagem.lower() == "/limpar":
            atendente.limpar_historico()
            print("Histórico limpo.\n")
            continue

        if not mensagem:
            continue

        resposta = atendente.responder(mensagem)

        print(f"\nEmpório: {resposta}\n")


if __name__ == "__main__":
    main()
