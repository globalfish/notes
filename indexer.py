import os, json, hashlib
from langchain.text_splitter import RecursiveCharacterTextSplitter
from rag_pipeline import _init_store
from note_parser import parse_multiple_notes

TRACK_FILE = "indexed_files.json"


def _load_settings(path: str = "settings.json") -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _get_docs_folder() -> str:
    settings = _load_settings()
    folder = settings.get("meeting_notes_dir") or settings.get("docs_folder")
    if not folder:
        # fallback to previous hard-coded location
        folder = "/mnt/c/Users/vswam/Obsidian/Work/Diary"
    # Normalize path and remove trailing spaces
    folder = os.path.expanduser(folder)
    folder = os.path.normpath(folder)
    return folder


DOCS_FOLDER = _get_docs_folder()

def get_file_id(path):
    try:
        stat = os.stat(path)
        base = f"{path}:{stat.st_mtime}"
    except Exception:
        # fallback to path-only hash
        base = path
    return hashlib.md5(base.encode()).hexdigest()

def load_seen_ids():
    if not os.path.exists(TRACK_FILE):
        return {}
    with open(TRACK_FILE) as f:
        return json.load(f)

def save_seen_ids(data):
    with open(TRACK_FILE, "w") as f:
        json.dump(data, f, indent=2)

def collect_docs(root, seen):
    updated, docs = {}, []
    if not os.path.exists(root):
        print(f"⚠️ Docs folder does not exist: {root}")
        return docs, updated

    for dirpath, _, files in os.walk(root):
        for f in files:
            if not f.lower().endswith(".md"):
                continue
            path = os.path.join(dirpath, f)
            try:
                fid = get_file_id(path)
            except Exception:
                # skip unreadable files
                continue
            updated[path] = fid
            if seen.get(path) != fid:
                try:
                    docs.extend(parse_multiple_notes(path))
                except Exception as e:
                    print(f"⚠️ Error parsing {path}: {e}")
    return docs, updated

def run_incremental_indexing():
    seen = load_seen_ids()
    docs, updated = collect_docs(DOCS_FOLDER, seen)
    if not docs:
        return 0, 0

    splitter = RecursiveCharacterTextSplitter(chunk_size=750, chunk_overlap=100)
    chunks = splitter.split_documents(docs)
    
    ids = [
        f"{doc.metadata['file_id']}_{i}"
        for i, doc in enumerate(chunks)
    ]
    # obtain store lazily from rag_pipeline
    store = _init_store()
    if store is None:
        print("⚠️ Vector store unavailable; skipping document push. Check PG_CONN and dependencies.")
        return len(docs), 0

    #store.add_documents(chunks, ids=[doc.metadata["file_id"] for doc in chunks])
    store.add_documents(chunks, ids=ids)
    save_seen_ids(updated)

    return len(docs), len(chunks)

