from __future__ import annotations

# import logging
import pandas as pd
from pathlib import Path

# logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
_CUSTOMER_FILE = BASE_DIR / "data" / "customer_data.xlsx"

_customer_df: pd.DataFrame | None = None


def _load_customers_data() -> pd.DataFrame:
    """Load the customer Excel file into a DataFrame, caching it after the first read."""
    global _customer_df
    if _customer_df is None:
        # logger.info("Caricamento file clienti da %s", _CUSTOMER_FILE)
        _customer_df = pd.read_excel(_CUSTOMER_FILE)
        # logger.debug("File clienti caricato: %d righe", len(_customer_df))
    return _customer_df


def get_customer_info(nome: str, cognome: str) -> dict | None:
    """Return the customer row as a dict, or None if not found."""
    df = _load_customers_data()
    mask = (df["nome"].str.lower() == nome.lower()) & (
        df["cognome"].str.lower() == cognome.lower()
    )
    row = df[mask]
    return row.iloc[0].to_dict() if not row.empty else None


def format_customer_block(info: dict | None) -> str:
    """Format a customer info dict into a bullet list for the prompt.

    Returns a fallback string if `info` is None.
    """
    if info is None:
        return "Nessuna informazione cliente disponibile."
    labels = {
        "nome": "Nome",
        "cognome": "Cognome",
        "regime": "Regime fiscale",
        "cassa": "Cassa previdenziale",
        "commercialista": "Commercialista",
        "apertura_piva": "Data apertura P.IVA",
        "fatturato_2025": "Fatturato 2025 (€)",
        "fatturato_2026": "Fatturato 2026 (€)",
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
    files_context: str,
    web_context: str = "",
) -> str:
    """Assemble the user-turn prompt from the question, customer data, and context.
    Includes a web section only when `web_context` is provided.
    """
    web_section = (
        f"\n## Sito web di Fiscozen (fiscozen.it)\n{web_context}" if web_context else ""
    )
    user_prompt = f"""
## Domanda del cliente
{question}

## Dati del cliente
{customer_block}

## Contesto fiscale rilevante (knowledge base)
{files_context}{web_section}
"""
    return user_prompt