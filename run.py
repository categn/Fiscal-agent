from __future__ import annotations

import argparse
import sys

from app.main import generate_answer


def interactive():
    print("\n\n=== Assistente Fiscale Fiscozen ===\n")
    print("Sono l'assistente fiscale di Fiscozen. Rispondo alle tue domande fiscali")
    print("cercando prima nella knowledge base aziendale, poi sul sito fiscozen.it.")
    print("Per domande complesse ti metto in contatto con il tuo Customer Success Consultant.\n")
    print("Digita 'esci' per uscire.\n")
    nome = input("Nome cliente: ").strip()
    cognome = input("Cognome cliente: ").strip()
    print()

    while True:
        try:
            domanda = input("Domanda: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nArrivederci!")
            sys.exit(0)

        if domanda.lower() == "esci":
            print("Arrivederci!")
            sys.exit(0)

        if not domanda:
            continue

        risposta = generate_answer(domanda, nome, cognome)
        print("\nRisposta:")
        print(f"{risposta}\n{'─' * 60}\n")


def cli():
    parser = argparse.ArgumentParser(description="Assistente fiscale Fiscozen")
    parser.add_argument("--nome", required=True)
    parser.add_argument("--cognome", required=True)
    parser.add_argument("--domanda", required=True)
    args = parser.parse_args()

    if not args.domanda.strip():
        print("Errore: la domanda non può essere vuota.")
        sys.exit(1)

    risposta = generate_answer(args.domanda, args.nome, args.cognome)
    print(risposta)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cli()
    else:
        interactive()
