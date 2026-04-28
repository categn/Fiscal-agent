# Fiscal Agent — Assistente Fiscale AI

Assistente intelligente per rispondere a domande fiscali dei clienti Fiscozen, basato su LLM con RAG sui documenti aziendali e ricerca sul sito fiscozen.it.

## Come funziona

```
Domanda + Nome cliente
        │
        ├── [utils.py] Lookup dati cliente dal file Excel (DataFrame cached in memoria)
        │
        ├── [main.py]  RAG: retrieval chunk rilevanti (LlamaIndex + BAAI/bge-m3)
        │             ├── indice persistito su disco (storage/), ricostruito solo al primo avvio
        │             └── se score < RAG_MIN_SCORE → nessun contesto trovato
        │
        ├── [main.py]  Se RAG non trova nulla → Web search su fiscozen.it
        │             ├── LLM estrae keyword dalla domanda (no dati personali)
        │             ├── DuckDuckGo cerca "site:fiscozen.it {keyword}"
        │             ├── Filtro hard urlparse: scarta URL senza "fiscozen" nel netloc
        │             └── Scraping testo pulito dalle top-2 pagine (BeautifulSoup, senza nav/footer/script)
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
| System prompt | `configs/prompts/system_prompt.txt` | Regole operative, formato risposta |
| Dati cliente | `data/customer_data.xlsx` | Estratti per nome+cognome e aggiunti al user prompt |
| Knowledge fiscale | `data/tax_knowledge_*.docx` | RAG: recupera i chunk più rilevanti per ogni domanda |
| Web search | DuckDuckGo (`ddgs`) + scraping con BeautifulSoup su `fiscozen.it` | Fallback se RAG non trova contesto rilevante — nessuna API key richiesta |
| Escalation | Solo nel codice (`main.py`) | Rimanda al consulente se nessuna fonte copre la domanda, senza chiamare l'LLM |

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
├── docs/
│   ├── architettura.docx       # file di spiegazione del progetto
├── storage/             # indice RAG persistito (auto-generato)
├── run.py               # entry point CLI
├── requirements.txt
└── .env.example
```

## Setup

### 1. Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Popola file `.env`

Apri il file `.env` copiato e imposta:

```env
OPENAI_API_KEY=your_openai_api_key
```

## Utilizzo

**Modalità interattiva:**
```bash
python run.py
```

**Modalità CLI:**
```bash
python run.py --nome Mario --cognome Rossi --domanda "Cos'è il regime forfettario?"
```

## Note operative

- **Primo avvio:** l'indice RAG viene costruito dai file `.docx` e salvato in `storage/`. Gli avvii successivi caricano l'indice dal disco (molto più veloci).
- **Aggiornamento knowledge base:** se modifichi i file `.docx`, elimina la cartella `storage/` per forzare la re-indicizzazione.
- **Aggiornamento prompt:** modifica i file in `configs/prompts/` senza toccare il codice.
- **Web search:** usa DuckDuckGo — nessuna API key richiesta. Cerca automaticamente `site:fiscozen.it {keyword}`, applica un filtro hard sull'URL con `urlparse`, e scrapa il testo pulito dalle top-2 pagine.


## Stack

- **LLM:** OpenAI `gpt-5.4-mini`
- **RAG:** LlamaIndex (retrieval puro, nessuna chiamata LLM interna), persistenza su disco (`storage/`)
- **Embedding:** HuggingFace `BAAI/bge-m3` (gratuito, locale, ottimizzato per italiano)
- **Web search:** DuckDuckGo (`ddgs`) + BeautifulSoup scraping — limitato a `fiscozen.it`, nessuna API key
- **Dati cliente:** pandas + openpyxl
