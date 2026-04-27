"""CLI entry point — ask the fiscal assistant a question.

Usage:
    python run.py                          # interactive mode
    python run.py --nome Mario --cognome Rossi --domanda "..."
"""
from __future__ import annotations

import argparse
import sys

from app.main import generate_answer


def interactive():
    print("=== Assistente Fiscale Fiscozen ===\n")
    print("Clienti disponibili: Mario Rossi, Giulia Verdi, Luca Martini, Elena Riva\n")
    nome = input("Nome cliente: ").strip()
    cognome = input("Cognome cliente: ").strip()
    domanda = input("Domanda: ").strip()

    if not domanda:
        print("Domanda vuota. Uscita.")
        sys.exit(0)

    print("\nElaborazione...\n")
    risposta = generate_answer(domanda, nome, cognome)
    print(f"{'─' * 60}\n{risposta}\n{'─' * 60}")


def cli():
    parser = argparse.ArgumentParser(description="Assistente fiscale Fiscozen")
    parser.add_argument("--nome", required=True)
    parser.add_argument("--cognome", required=True)
    parser.add_argument("--domanda", required=True)
    args = parser.parse_args()

    risposta = generate_answer(args.domanda, args.nome, args.cognome)
    print(risposta)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cli()
    else:
        interactive()
