"""Fiscal AI assistant: RAG + customer data + company tone."""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from openai import OpenAI

from app.utils import get_customer_info, format_customer_block, build_user_prompt

load_dotenv()

BASE_DIR = Path(__file__).parent.parent

# Free local embeddings — no OpenAI quota used for RAG
Settings.embed_model = HuggingFaceEmbedding(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

# ── System prompt (static — tone of voice never changes) ───────────────────

with open(BASE_DIR / "configs" / "tone_of_voice.txt") as f:
    _tone = f.read().strip()

SYSTEM_PROMPT = f"""Sei l'assistente fiscale di Fiscozen.

## Tono di voce — OBBLIGATORIO, non derogare mai
{_tone}

## Regole operative
- Usa SOLO le informazioni del contesto fiscale fornito nel messaggio utente. Non inventare dati fiscali.
- Personalizza la risposta con i dati del cliente quando sono pertinenti alla domanda.
- Se la domanda è complessa, ambigua o potenzialmente rischiosa per il cliente → invita esplicitamente a contattare il Customer Success Consultant assegnato.
- Se il contesto fiscale non copre la domanda → dichiaralo con onestà e suggerisci l'escalation.
- Rispondi sempre in italiano.

## Formato della risposta
1. Risposta diretta e strutturata alla domanda.
2. Se necessario: "Per questa situazione ti consigliamo di parlare con il tuo Customer Success Consultant, [nome], che ti potrà supportare in modo personalizzato."
"""


# ── RAG index (built once at import time) ──────────────────────────────────

def _build_query_engine():
    docs = SimpleDirectoryReader(
        input_files=[
            str(BASE_DIR / "data" / "tax_knowledge_1.docx"),
            str(BASE_DIR / "data" / "tax_knowledge_2.docx"),
        ]
    ).load_data()

    splitter = SentenceSplitter(chunk_size=512, chunk_overlap=64)
    index = VectorStoreIndex.from_documents(docs, transformations=[splitter])
    return index.as_query_engine(similarity_top_k=4)


_query_engine = _build_query_engine()


def _get_tax_context(question: str) -> str:
    return str(_query_engine.query(question))


# ── Main entry point ───────────────────────────────────────────────────────

_llm_client = OpenAI()


def generate_answer(question: str, nome: str, cognome: str) -> str:
    """
    Generate a fiscal assistant response.

    Args:
        question: The customer's question.
        nome:     Customer first name (used to look up customer data).
        cognome:  Customer last name.

    Returns:
        The assistant's answer as a string.
    """
    customer_info = get_customer_info(nome, cognome)
    customer_block = format_customer_block(customer_info)
    tax_context = _get_tax_context(question)

    user_prompt = build_user_prompt(question, customer_block, tax_context)

    response = _llm_client.chat.completions.create(
        model="gpt-5.4-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content
