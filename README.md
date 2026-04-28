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
| System prompt | `configs/prompts/system_prompt.txt` | Regole operative, formato risposta |
| Dati cliente | `data/customer_data.xlsx` | Estratti per nome+cognome e aggiunti al user prompt |
| Knowledge fiscale | `data/tax_knowledge_*.docx` | RAG: recupera i chunk più rilevanti per ogni domanda |
| Web search | Google Custom Search su `fiscozen.it` | Fallback se RAG non trova contesto rilevante |
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
├── storage/             # indice RAG persistito (auto-generato, ignorato da git)
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

### 2. Google Custom Search Engine (CSE) — get your `GOOGLE_CSE_ID`

The web-search fallback queries only `fiscozen.it`. You need to create a Custom Search Engine and restrict it to that domain:

1. Go to **https://programmablesearchengine.google.com/** and click **"Add"** (or **"New search engine"**).
2. In the **"Sites to search"** field enter: `www.fiscozen.it/*`
3. Give the engine any name (e.g. `Fiscozen Search`) and click **Create**.
4. On the next screen click **"Customize"** → open the **"Basics"** tab.
5. Copy the **Search engine ID** (looks like `50393eb5610d64f0d`). This is your `GOOGLE_CSE_ID`.
6. Still in the Customize panel, make sure **"Search the entire web"** is **OFF** — the engine should search only the site you entered above.

### 3. Google API Key — get your `GOOGLE_API_KEY`

1. Go to **https://console.cloud.google.com/apis/credentials** (create a project if you don't have one).
2. Click **"Create credentials" → "API key"**. Copy the key that appears.
3. In the left menu go to **"Library"**, search for **"Custom Search API"** and click **Enable**.
4. (Optional but recommended) Restrict the key to the **Custom Search API** only via the key's settings.

### 4. Fill in `.env`

Open the `.env` file you copied above and set:

```env
OPENAI_API_KEY=your_openai_api_key
GOOGLE_API_KEY=your_google_api_key   # from step 3
GOOGLE_CSE_ID=your_search_engine_id  # from step 2
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
- **Logging:** il sistema logga su console a livello `DEBUG` per default. I log mostrano ogni passo del flusso (RAG, web search, escalation) e il contenuto completo dello user prompt. Per ridurre il rumore in produzione, imposta `LOG_LEVEL=INFO` nel `.env` o modificalo direttamente in `main.py`.

## Stack

- **LLM:** OpenAI `gpt-5.4-mini`
- **RAG:** LlamaIndex (retrieval puro, nessuna chiamata LLM interna), persistenza su disco (`storage/`)
- **Embedding:** HuggingFace `BAAI/bge-m3` (gratuito, locale, ottimizzato per italiano)
- **Web search:** Google Custom Search API limitata a `fiscozen.it`
- **Dati cliente:** pandas + openpyxl
- **Logging:** stdlib `logging` — `DEBUG` per user prompt e dettagli tecnici, `INFO` per il flusso principale, `WARNING`/`ERROR` per configurazione mancante o errori di rete
