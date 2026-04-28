"""Utility functions: customer lookup, prompt building."""
from __future__ import annotations

import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
_CUSTOMER_FILE = BASE_DIR / "data" / "customer_data.xlsx"

_customer_df: pd.DataFrame | None = None


def _load_customers() -> pd.DataFrame:
    global _customer_df
    if _customer_df is None:
        _customer_df = pd.read_excel(_CUSTOMER_FILE, engine="openpyxl")
        _customer_df["nome"] = _customer_df["nome"].str.strip()
        _customer_df["cognome"] = _customer_df["cognome"].str.strip()
    return _customer_df


def get_customer_info(nome: str, cognome: str) -> dict | None:
    """Return the customer row as a dict, or None if not found."""
    df = _load_customers()
    mask = (df["nome"].str.lower() == nome.lower()) & (
        df["cognome"].str.lower() == cognome.lower()
    )
    row = df[mask]
    return row.iloc[0].to_dict() if not row.empty else None


def format_customer_block(info: dict | None) -> str:
    if info is None:
        return "Nessuna informazione cliente disponibile."
    labels = {
        "nome": "Nome",
        "cognome": "Cognome",
        "regime": "Regime fiscale",
        "cassa": "Cassa previdenziale",
        "commercialista": "Customer Success Consultant assegnato",
        "apertura_piva": "Data apertura P.IVA",
        "fatturato_2025": "Fatturato 2025 (k€)",
        "fatturato_2026": "Fatturato 2026 (k€)",
    }
    lines = []
    for k, v in info.items():
        if hasattr(v, "strftime"):
            v = v.strftime("%d/%m/%Y")
        lines.append(f"- {labels.get(k, k)}: {v}")
    return "\n".join(lines)


def build_user_prompt(
    question: str,
    customer_block: str,
    tax_context: str,
    web_context: str = "",
) -> str:
    web_section = (
        f"\n## Guide Fiscozen (fiscozen.it)\n{web_context}" if web_context else ""
    )
    return f"""## Domanda del cliente
{question}

## Dati del cliente
{customer_block}

## Contesto fiscale rilevante (knowledge base)
{tax_context}{web_section}

Rispondi alla domanda usando il contesto fiscale e le guide Fiscozen. \
Adatta la risposta ai dati del cliente quando è utile."""
