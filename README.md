# Fiscal Agent — Assistente Fiscale AI

Assistente intelligente per rispondere a domande fiscali dei clienti Fiscozen, basato su LLM con RAG sui documenti aziendali.

## Come funziona

```
Domanda + Nome cliente
        │
        ├── [utils.py] Lookup dati cliente dal file Excel
        │
        ├── [main.py]  RAG sui documenti fiscali (LlamaIndex + HuggingFace embeddings)
        │
        └── [main.py]  Chiamata OpenAI con:
                        ├── system prompt → tono di voce (statico)
                        └── user prompt   → dati cliente + contesto fiscale (dinamici)
```

| Strato | Sorgente | Come viene usato |
|---|---|---|
| Tono di voce | `configs/tone_of_voice.txt` | Scritto nel system prompt, non cambia mai |
| Dati cliente | `data/customer_data.xlsx` | Estratti per nome+cognome e aggiunti al user prompt |
| Knowledge fiscale | `data/tax_knowledge_*.docx` | RAG: recupera i chunk più rilevanti per ogni domanda |
| Escalation | Regole nel system prompt | Il modello rimanda al Customer Success Consultant assegnato quando la domanda è complessa |

## Struttura del progetto

```
├── app/
│   ├── main.py          # core: RAG, system prompt, chiamata LLM
│   └── utils.py         # lookup cliente, formattazione prompt
├── configs/
│   └── tone_of_voice.txt
├── data/
│   ├── customer_data.xlsx
│   ├── tax_knowledge_1.docx
│   └── tax_knowledge_2.docx
├── tests/
│   └── test_agent.py
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
# aggiungi la tua chiave in .env: OPENAI_API_KEY=sk-...
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

## Stack

- **LLM:** OpenAI `gpt-5.4-mini`
- **RAG:** LlamaIndex con embedding locali (`paraphrase-multilingual-MiniLM-L12-v2`)
- **Dati cliente:** pandas + openpyxl
- **Embedding:** HuggingFace (gratuiti, nessuna quota OpenAI consumata per il RAG)