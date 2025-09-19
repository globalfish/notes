"""Small helper to download a HuggingFace model's files into a local directory.

Usage:
    python download_hf_model.py --model sentence-transformers/all-MiniLM-L6-v2 --out /path/to/local/model

Requires: huggingface_hub, transformers, sentence-transformers
"""
import argparse
from huggingface_hub import snapshot_download


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True, help="HF model id, e.g. sentence-transformers/all-MiniLM-L6-v2")
    p.add_argument("--out", required=True, help="Local directory to store model files")
    args = p.parse_args()

    print(f"Downloading model {args.model} to {args.out}...")
    snapshot_download(repo_id=args.model, local_dir=args.out, allow_patterns=["*"], local_dir_use_symlinks=False)
    print("Download complete.")

if __name__ == '__main__':
    main()
