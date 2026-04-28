# Fiscal Agent — Assistente Fiscale AI

Assistente intelligente per rispondere a domande fiscali dei clienti Fiscozen, basato su LLM con RAG sui documenti aziendali e ricerca sul sito fiscozen.it.

## Come funziona

```
Domanda + Nome cliente
        │
        ├── [utils.py] Lookup dati cliente dal file Excel
        │
        ├── [main.py]  RAG: retrieval chunk rilevanti (LlamaIndex + BAAI/bge-m3)
        │             ├── indice persistito su disco (storage/), ricostruito solo al primo avvio
        │             └── se score < RAG_MIN_SCORE → nessun contesto trovato
        │
        ├── [main.py]  Se RAG non trova nulla → Web search su fiscozen.it
        │             └── LLM estrae keyword dalla domanda (no dati personali) → Google Custom Search
        │
        ├── [main.py]  Se né RAG né web trovano nulla → escalation immediata al consulente (no LLM)
        │
        └── [main.py]  Chiamata OpenAI con:
                        ├── system prompt → caricato da configs/prompts/system_prompt.txt
                        └── user prompt   → dati cliente + contesto (RAG o web)
```

| Strato | Sorgente | Come viene usato |
|---|---|---|
| Tono di voce | `configs/tone_of_voice.txt` | Iniettato nel system prompt, non cambia mai |
| System prompt | `configs/prompts/system_prompt.txt` | Regole operative, escalation, formato risposta |
| Dati cliente | `data/customer_data.xlsx` | Estratti per nome+cognome e aggiunti al user prompt |
| Knowledge fiscale | `data/tax_knowledge_*.docx` | RAG: recupera i chunk più rilevanti per ogni domanda |
| Web search | Google Custom Search su `fiscozen.it` | Fallback se RAG non trova contesto rilevante |
| Escalation | Codice + system prompt | Rimanda al consulente se nessuna fonte copre la domanda |

## Struttura del progetto

```
├── app/
│   ├── main.py          # core: RAG, web search, chiamata LLM
│   └── utils.py         # lookup cliente, formattazione prompt
├── configs/
│   ├── tone_of_voice.txt
│   └── prompts/
│       ├── system_prompt.txt            # prompt principale (modificabile senza toccare il codice)
│       └── system_prompt_extraction.txt # prompt per estrazione keyword (web search)
├── data/
│   ├── customer_data.xlsx
│   ├── tax_knowledge_1.docx
│   └── tax_knowledge_2.docx
├── storage/             # indice RAG persistito (auto-generato, ignorato da git)
├── run.py               # entry point CLI
├── requirements.txt
└── .env.example
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# compila .env con le tue chiavi
```

## Utilizzo

**Modalità interattiva:**
```bash
python run.py
```

**Modalità CLI (testabile e scriptabile):**
```bash
python run.py --nome Mario --cognome Rossi --domanda "Cos'è il regime forfettario?"
```

## Note operative

- **Primo avvio:** l'indice RAG viene costruito dai file `.docx` e salvato in `storage/`. Gli avvii successivi caricano l'indice dal disco (molto più veloci).
- **Aggiornamento knowledge base:** se modifichi i file `.docx`, elimina la cartella `storage/` per forzare la re-indicizzazione.
- **Aggiornamento prompt:** modifica i file in `configs/prompts/` senza toccare il codice.
- **Web search:** richiede `GOOGLE_API_KEY` e `GOOGLE_CSE_ID` nel `.env`. Senza di essi il sistema funziona solo con il RAG locale.

## Stack

- **LLM:** OpenAI `gpt-5.4-mini`
- **RAG:** LlamaIndex (retrieval puro, nessuna chiamata LLM interna), persistenza su disco (`storage/`)
- **Embedding:** HuggingFace `BAAI/bge-m3` (gratuito, locale, ottimizzato per italiano)
- **Web search:** Google Custom Search API limitata a `fiscozen.it`
- **Dati cliente:** pandas + openpyxl
