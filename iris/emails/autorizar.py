"""`python -m iris.emails.autorizar`: autoriza a Iris a ler e enviar e-mails pelo seu Gmail (só uma vez)."""

from .gmail import CREDENCIAIS, TOKEN, GmailNaoConfigurado, autorizar


def main():
    print("\n  Autorizando a Iris no seu Gmail:")
    print("   - LER e buscar e-mails")
    print("   - ENVIAR e responder (sempre só depois da sua confirmação; ela não apaga nada)")
    print("  O navegador vai abrir: escolha sua conta e marque as DUAS permissões.")
    print("  Se aparecer 'O Google não verificou este app', clique em 'Continuar' (o app é seu).\n")
    try:
        autorizar()
    except GmailNaoConfigurado as erro:
        print(f"  ERRO: {erro}")
        print(f"  Coloque o arquivo baixado do Google Cloud em: {CREDENCIAIS}")
        return
    print(f"\n  Pronto! Autorização salva em {TOKEN}. Pode fechar esta janela.\n")


if __name__ == "__main__":
    main()
