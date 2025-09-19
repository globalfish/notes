Environment setup for the RAG notes app

This project uses environment variables to configure the vector DB, LLM host, and model names. You can set them in your shell, or create a `.env` file and source `env_setup.sh` to load them.

Recommended variables

- PG_CONN: Postgres connection string used by PGVector, e.g.
  postgresq+psycopg://<user>:<pass>@<host>:<port>/<db>?options=-csearch_path=private_gpt

- OLLAMA_HOST: HTTP base URL for Ollama (if running locally), e.g. `http://localhost:11434`
- OLLAMA_MODEL: Ollama model name to use, e.g. `gemma3`
- HF_MODEL_NAME: HuggingFace model to use for local embeddings. Default: `sentence-transformers/all-MiniLM-L6-v2`
- VECTOR_COLLECTION: Name of the Postgres vector collection/table. Default: `meetingNotes`
- MEETING_NOTES_DIR: Path to your notes directory. Example: `/mnt/c/Users/vswam/Obsidian/Work/Diary/`
 - HF_MODEL_DIR: Optional local path where a HuggingFace embeddings model is downloaded. If set, the app will use this directory instead of fetching models at runtime.

Usage

1. Create a `.env` file in the project root (optional):

   PG_CONN="postgresql+psycopg://postgres:postgres@10.0.0.59:5433/notes?options=-csearch_path=private_gpt"
   OLLAMA_HOST="http://localhost:11434"
   OLLAMA_MODEL="gemma3"
   HF_MODEL_NAME="sentence-transformers/all-MiniLM-L6-v2"
   VECTOR_COLLECTION="meetingNotes"
   MEETING_NOTES_DIR="/path/to/your/notes"

2. Load the variables into your shell:

   source env_setup.sh

   This will export the variables into your current shell session. `env_setup.sh` will respect any values already exported and will load variables from `.env` if present.

3. Pre-download the HF embeddings model to avoid redownloading each run:

```bash
# example download path
mkdir -p ~/.cache/hf/all-MiniLM-L6-v2
python download_hf_model.py --model sentence-transformers/all-MiniLM-L6-v2 --out ~/.cache/hf/all-MiniLM-L6-v2

# set HF_MODEL_DIR (or add to .env)
export HF_MODEL_DIR=$HOME/.cache/hf/all-MiniLM-L6-v2
```

4. Load env and start the app:

```bash
source env_setup.sh
python main.py
```

Quick health checks

- Test Postgres connection (script provided):

```bash
./check_pg_conn.py
```

- Test Ollama host reachable (simple curl):

```bash
curl -sSf "$OLLAMA_HOST"/v1/engines || echo "Ollama host not reachable"
```

