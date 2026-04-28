from __future__ import annotations

# import logging
import os
from pathlib import Path

from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from ddgs import DDGS
from llama_index.core import (
    VectorStoreIndex, SimpleDirectoryReader, Settings,
    StorageContext, load_index_from_storage,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from openai import OpenAI

from app.utils import get_customer_info, format_customer_block, build_user_prompt

load_dotenv()

# logging.basicConfig(
#    level=logging.INFO,
#    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
#    datefmt="%H:%M:%S",
#)
# logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent

_EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-m3")
_LLM_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
_TEMPERATURE = float(os.getenv("TEMPERATURE", "0.4"))
_RAG_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.5"))

Settings.embed_model = HuggingFaceEmbedding(model_name=_EMBED_MODEL)

_llm_client = OpenAI()


###############################################################
# Load prompts from file
###############################################################

def _load_prompt(filename: str) -> str:
    """Load and return the content of a prompt file from configs/prompts/."""
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
    """Build or load the RAG vector index and return a retriever.

    Loads the persisted index from `storage/` if it exists; otherwise builds it
    from the tax knowledge .docx files and persists it for future runs.
    """
    if _STORAGE_DIR.exists():
        # logger.info("RAG: caricamento indice da disco (%s)", _STORAGE_DIR)
        storage_context = StorageContext.from_defaults(persist_dir=str(_STORAGE_DIR))
        index = load_index_from_storage(storage_context)
    else:
        # logger.info("RAG: indice non trovato, costruzione da zero dai file")
        docs = SimpleDirectoryReader(
            input_files=[
                str(BASE_DIR / "data" / "tax_knowledge_1.docx"),
                str(BASE_DIR / "data" / "tax_knowledge_2.docx"),
            ]
        ).load_data()
        splitter = SentenceSplitter(chunk_size=512, chunk_overlap=64)
        index = VectorStoreIndex.from_documents(docs, transformations=[splitter])
        index.storage_context.persist(persist_dir=str(_STORAGE_DIR))
        # logger.info("RAG: indice costruito e salvato in %s", _STORAGE_DIR)

    return index.as_retriever(similarity_top_k=4)

# Build the RAG retriever once at import time.
_retriever = _build_retriever()


def _get_context_from_files(question: str) -> str:
    """Retrieve relevant chunks from the local knowledge base for the given question.

    Returns a concatenated string of matching chunks, or an empty string if none
    exceed the minimum similarity score.
    """
    nodes = _retriever.retrieve(question)
    relevant = [n for n in nodes if (n.score or 0) >= _RAG_MIN_SCORE]
    # logger.debug("RAG: %d chunk trovati, %d sopra la soglia (%.2f)", len(nodes), len(relevant), _RAG_MIN_SCORE)
    if not relevant:
        return ""
    return "\n\n".join(n.get_content() for n in relevant)


###############################################################
# Web search (on fiscozen.it only)
###############################################################

def _extract_keywords_with_llm(question: str) -> str:
    """Use the LLM to extract search-friendly keywords from a user question.

    Strips personal data and rephrases the question as a concise query
    suitable for Google Custom Search.
    """
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
        temperature=0.3
    )
    keywords = response.choices[0].message.content.strip()
    # logger.debug("Keyword estratte per web search: %r", keywords)
    return keywords


_NOISE_TAGS = ["script", "style", "nav", "footer", "header", "form", "noscript"]


def _scrape_page(url: str) -> str:
    """Fetch a URL and return clean text content, stripping HTML noise."""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(_NOISE_TAGS):
            tag.decompose()
        lines = [line.strip() for line in soup.get_text(separator="\n").splitlines() if line.strip()]
        return "\n".join(lines)
    except Exception as e:
        # logger.debug("Scraping fallito per %s: %s", url, e)
        return ""


def _web_search(keywords: str) -> str:
    """Search fiscozen.it via DuckDuckGo, scrape each result page, and return clean text.

    Prefixes keywords with 'site:fiscozen.it' and applies a urlparse hard filter
    to ensure only fiscozen.it URLs are scraped.
    """
    query = f"site:fiscozen.it {keywords}"
    # logger.info("Web search DuckDuckGo query: %r", query)
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=2):
                url = r.get("href", "")
                if "fiscozen" not in urlparse(url).netloc:
                    continue
                title = r.get("title", "")
                content = _scrape_page(url)
                if content:
                    results.append(f"{title}\n{content}")
                    # logger.debug("Scraped %s (%d chars)", url, len(content))
    except Exception as e:
        # logger.error("Web search fallita: %s", e)
        return ""
    # logger.debug("Web search: %d pagine scrapate per %r", len(results), query)
    return "\n\n".join(results)


###############################################################
# Main entry point
###############################################################

def generate_answer(question: str, nome: str, cognome: str) -> str:
    """Generate a fiscal answer for the given customer and question.

    Pipeline:
    1. Fetch customer data from the Excel sheet.
    2. Try RAG retrieval from the local knowledge base.
    3. If RAG finds nothing, fall back to a web search on fiscozen.it.
    4. If neither source has context, return an escalation message to the consultant.
    5. Otherwise, call the LLM with the retrieved context and return the answer with a source attribution footer.
    """
    # logger.info("Nuova domanda — cliente: %s %s", nome, cognome)
    customer_info = get_customer_info(nome, cognome)
#    if customer_info:
#        logger.debug("Cliente trovato: %s", {k: v for k, v in customer_info.items() if k in ("regime", "cassa")})
#    else:
#        logger.warning("Cliente %s %s non trovato nel file Excel", nome, cognome)

    customer_block = format_customer_block(customer_info)
    files_context = _get_context_from_files(question)

    if files_context:
        #logger.info("Fonte: knowledge base locale")
        web_context = ""
    else:
        #logger.info("RAG senza risultati — avvio web search su fiscozen.it")
        web_context = _web_search(_extract_keywords_with_llm(question))

    if not files_context and not web_context:
        #logger.info("Nessun contesto trovato — escalation al consulente")
        consultant = (customer_info or {}).get("commercialista", "il tuo Customer Success Consultant")
        return f"Non ho informazioni sufficienti per rispondere a questa domanda. Ti consiglio di contattare {consultant}, che potrà aiutarti direttamente."

    user_prompt = build_user_prompt(question, customer_block, files_context, web_context)
    #logger.debug("User prompt costruito:\n%s", user_prompt)

    response = _llm_client.chat.completions.create(
        model=_LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=_TEMPERATURE,
    )
    answer = response.choices[0].message.content

    if files_context:
        source = "[Fonte: knowledge base locale]"
    else:
        source = "[Fonte: ricerca su fiscozen.it]"

    return f"{answer}\n\n{source}"