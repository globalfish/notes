# RAG Notes — Local Retrieval-Augmented Notes App

Lightweight desktop app to index and query your meeting notes using a local LLM + vector store. It parses meeting notes (Markdown), chunks them, stores embeddings in a vector database (Postgres + pgvector), and provides a small Kivy UI for asking questions and running incremental indexing.

## Features
- Parse meeting notes from a directory (configurable).
- Chunk text, extract metadata (title, date, attendees, action items).
- Store embeddings in Postgres via pgvector.
- Use a local or remote LLM (Ollama or other) through LangChain for Q&A chains.
- Simple Kivy-based UI for ad-hoc queries and indexing operations.

## Quick links
- Code: this repo
- Config: `settings.json`
- Env helpers: `env_setup.sh`, `README_ENV.md`
- Pre-download helper: `download_hf_model.py`
- Sample meeting note: `meeting_2025-09-17_Sample_Meeting_Title.md`

## Requirements
- Python 3.11+
- See `requirements.txt` for the Python dependencies (LangChain, Kivy, sentence-transformers, SQLAlchemy, psycopg2-binary, etc.).

## Quick start (recommended)
1. Create and activate a virtualenv:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

3. Configure environment variables. You can use the provided `env_setup.sh` to load values from a `.env` file:

```bash
cp env_setup.sh .env          # edit .env and set vars like PG_CONN, OLLAMA_HOST, HF_MODEL_DIR
source env_setup.sh
```

4. (Optional) Pre-download the Hugging Face embeddings model to avoid repeated downloads:

```bash
python download_hf_model.py --model sentence-transformers/all-MiniLM-L6-v2 --out ~/.cache/hf/all-MiniLM-L6-v2
export HF_MODEL_DIR=$HOME/.cache/hf/all-MiniLM-L6-v2
```

5. Run the app:

```bash
python main.py
```

## Configuration
- `settings.json` contains the default path for your meeting notes directory. Current value:

```
meeting_notes_dir: "/mnt/c/Users/vswam/Obsidian/Work/Diary/"
```

Override configuration using environment variables (preferred):
- `PG_CONN` — Postgres connection string (required for pgvector storage)
- `OLLAMA_HOST` — URL for Ollama if using a local LLM
- `MODEL_NAME` — model name for Ollama/LLM
- `HF_MODEL_DIR` — local path to a pre-downloaded HF embeddings model

Check `README_ENV.md` for more detailed steps on environment setup and troubleshooting.

## Development notes
- The codebase uses lazy initialization for heavy runtime resources (embeddings, LLM, vector store) to avoid import-time failures.
- `note_parser.py` contains the parsing logic for meeting notes — it extracts title, date, attendees, bullets, and action items.
- `indexer.py` performs incremental indexing and writes to the vector store.
- `rag_pipeline.py` wires embeddings, vector store, and the chain used by the UI.

## Troubleshooting
- If imports fail at runtime, make sure you installed the dependencies in an activated virtual environment.
- If the app can't reach the vector store, verify `PG_CONN` and that the Postgres server has the `pgvector` extension installed.
- To check DB connectivity, use the included `check_pg_conn.py` script.
- If embeddings appear to re-download each run, set `HF_MODEL_DIR` to a local copy of the model (see `download_hf_model.py`).


## License
- See `LICENSE`.

## Author
- Venkat Swaminathan (c) 2025  
