from __future__ import annotations

import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from llama_index.core import (
    VectorStoreIndex, SimpleDirectoryReader, Settings,
    StorageContext, load_index_from_storage,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from openai import OpenAI

from app.utils import get_customer_info, format_customer_block, build_user_prompt

load_dotenv()

BASE_DIR = Path(__file__).parent.parent

_EMBED_MODEL        = os.getenv("EMBED_MODEL", "BAAI/bge-m3")
_LLM_MODEL          = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
_TEMPERATURE        = float(os.getenv("TEMPERATURE", "0.4"))
_RAG_MIN_SCORE      = float(os.getenv("RAG_MIN_SCORE", "0.5"))

Settings.embed_model = HuggingFaceEmbedding(model_name=_EMBED_MODEL)

# ── Prompts (loaded from file) ─────────────────────────────────────────────

def _load_prompt(filename: str) -> str:
    with open(BASE_DIR / "configs" / "prompts" / filename) as f:
        return f.read().strip()

with open(BASE_DIR / "configs" / "tone_of_voice.txt") as f:
    _tone = f.read().strip()

SYSTEM_PROMPT = _load_prompt("system_prompt.txt").format(tone=_tone)
SYSTEM_PROMPT_EXTRACTION = _load_prompt("system_prompt_extraction.txt")

###############################################################
# RAG index (built once at import time)
###############################################################

_STORAGE_DIR = BASE_DIR / "storage"


def _build_retriever():
    if _STORAGE_DIR.exists():
        storage_context = StorageContext.from_defaults(persist_dir=str(_STORAGE_DIR))
        index = load_index_from_storage(storage_context)
    else:
        docs = SimpleDirectoryReader(
            input_files=[
                str(BASE_DIR / "data" / "tax_knowledge_1.docx"),
                str(BASE_DIR / "data" / "tax_knowledge_2.docx"),
            ]
        ).load_data()
        splitter = SentenceSplitter(chunk_size=512, chunk_overlap=64)
        index = VectorStoreIndex.from_documents(docs, transformations=[splitter])
        index.storage_context.persist(persist_dir=str(_STORAGE_DIR))

    return index.as_retriever(similarity_top_k=4)


_retriever = _build_retriever()


def _get_tax_context(question: str) -> str:
    nodes = _retriever.retrieve(question)
    relevant = [n for n in nodes if (n.score or 0) >= _RAG_MIN_SCORE]
    if not relevant:
        return ""
    return "\n\n".join(n.get_content() for n in relevant)

###############################################################
# Web search (fiscozen.it only)
###############################################################

def _extract_keywords(question: str) -> str:
    response = _llm_client.chat.completions.create(
        model=_LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT_EXTRACTION
            },
            {
                "role": "user", 
                "content": question
            },
        ],
        temperature=0.2
    )
    return response.choices[0].message.content.strip()


def _web_search(question: str) -> str:
    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")
    if not api_key or not cse_id:
        return ""
    params = {"key": api_key, "cx": cse_id, "q": question, "num": 5}
    try:
        resp = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params=params,
            timeout=5,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if not items:
            return ""
        return "\n\n".join(
            f"{item['title']}\n{item.get('snippet', '')}" for item in items
        )
    except requests.RequestException:
        return ""


###############################################################
# Main entry point
###############################################################

_llm_client = OpenAI()


def generate_answer(question: str, nome: str, cognome: str) -> str:
    customer_info = get_customer_info(nome, cognome)
    customer_block = format_customer_block(customer_info)
    tax_context = _get_tax_context(question)
    web_context = _web_search(_extract_keywords(question)) if not tax_context else ""

    if not tax_context and not web_context:
        consultant = (customer_info or {}).get("commercialista", "il tuo Customer Success Consultant")
        return f"Non ho informazioni sufficienti per rispondere a questa domanda. Ti consigliamo di contattare {consultant}, che potrà aiutarti direttamente."

    user_prompt = build_user_prompt(question, customer_block, tax_context, web_context)

    response = _llm_client.chat.completions.create(
        model=_LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=_TEMPERATURE,
    )
    answer = response.choices[0].message.content

    if tax_context:
        source = "[Fonte: knowledge base locale]"
    else:
        source = "[Fonte: ricerca su fiscozen.it]"

    return f"{answer}\n\n{source}"
