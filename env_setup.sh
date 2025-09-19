#!/usr/bin/env bash
# env_setup.sh — load recommended environment variables for the notes RAG app.
# Usage: source ./env_setup.sh   # do NOT run directly; source to export into current shell
# You can create a `.env` file with KEY=VALUE lines and this script will export them.

# Default placeholder values (customize or set via .env)
: ${PG_CONN:="postgresql+psycopg://postgres:postgres@10.0.0.59:5433/notes?options=-csearch_path=private_gpt"}
: ${OLLAMA_HOST:="http://localhost:11434"}
: ${OLLAMA_MODEL:="gemma3"}
: ${HF_MODEL_NAME:="sentence-transformers/all-MiniLM-L6-v2"}
: ${VECTOR_COLLECTION:="meetingNotes"}
: ${MEETING_NOTES_DIR:="/mnt/c/Users/vswam/Obsidian/Work/Diary"}
: ${HF_MODEL_DIR:="/home/venkat/models"}

# If a .env file exists in the current directory, load it (ignores commented lines)
if [ -f .env ]; then
  echo "Loading environment variables from .env"
  # Export key=value lines, ignoring comments and blank lines
  set -o allexport
  # This will handle values containing spaces if properly quoted in the .env file
  while IFS='=' read -r key value; do
    # skip comments and blank
    if [[ "$key" =~ ^# ]] || [[ -z "$key" ]]; then
      continue
    fi
    # remove surrounding quotes from value
    value="$(echo "$value" | sed -e 's/^\"//' -e 's/\"$//' -e "s/^'//" -e "s/'$//")"
    export "$key=$value"
  done < <(grep -v '^\s*#' .env | sed -e '/^\s*$/d')
  set +o allexport
fi

# Export defaults only if not already set
export PG_CONN
export OLLAMA_HOST
export OLLAMA_MODEL
export HF_MODEL_NAME
export VECTOR_COLLECTION
export MEETING_NOTES_DIR
export HF_MODEL_DIR

echo "Environment variables set (override by creating a .env file or exporting before sourcing)."

echo "PG_CONN=${PG_CONN}"
echo "OLLAMA_HOST=${OLLAMA_HOST}"
echo "OLLAMA_MODEL=${OLLAMA_MODEL}"
echo "HF_MODEL_NAME=${HF_MODEL_NAME}"
echo "VECTOR_COLLECTION=${VECTOR_COLLECTION}"
echo "MEETING_NOTES_DIR=${MEETING_NOTES_DIR}"

echo "HF_MODEL_DIR=${HF_MODEL_DIR}"
if [ -n "${HF_MODEL_DIR}" ] && [ ! -d "${HF_MODEL_DIR}" ]; then
  echo "HF_MODEL_DIR is set but the directory does not exist: ${HF_MODEL_DIR}"
fi
