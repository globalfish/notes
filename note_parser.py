"""Note parsing utilities for meeting notes files.

Provides parse_multiple_notes(path) -> list[Document].
The parser is tolerant to a few markdown variants and attempts a useful
fallback when a file contains a single unstructured meeting.
"""
from typing import List
import os
import re
import hashlib
from langchain_core.documents import Document

# Patterns we accept for bullets and headings
_BULLET_RE = r"^[ \t]*[-*]\s+(.*)"  # accepts '- item' or '* item' with optional indent
_HEADER_RE = r"^#{1,6}\s*(.+)"  # capture markdown headings


def _file_mtime_hash(path: str) -> str:
    """Return a stable-ish id for a file using path + mtime."""
    try:
        stat = os.stat(path)
        base = f"{path}:{stat.st_mtime}"
    except Exception:
        base = path
    return hashlib.md5(base.encode()).hexdigest()


def _safe_extract_field(text: str, patterns: List[str]) -> str:
    """Try a list of regex patterns and return the first capture or empty string."""
    for p in patterns:
        m = re.search(p, text, flags=re.IGNORECASE | re.MULTILINE)
        if m:
            return (m.group(1) or "").strip()
    return ""


def _extract_bulleted_block(text: str, label_variants: List[str]) -> str:
    """Search for a header named one of label_variants and return the bullet lines under it.
    The function tolerates a header like '## Notes' or '### Topics' and collects subsequent
    lines that look like bullets (- or *). Returns a joined string (one item per line) or '' if none.
    """
    for label in label_variants:
        # header like: ## Notes or ## Notes:
        # use a single optional colon and optional trailing whitespace
        hdr_re = rf"^#{2,4}\s*{re.escape(label)}\s*:?[ \t]*$"
        match = re.search(hdr_re, text, flags=re.IGNORECASE | re.MULTILINE)
        if not match:
            # try looser header match (any heading containing the label)
            match = re.search(rf"^#{2,4}.*{re.escape(label)}.*$", text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            # start scanning lines after the header
            start = match.end()
            following = text[start:]
            lines = []
            for line in following.splitlines():
                if re.match(r"^#{1,6}\s+", line):
                    # next header - stop collecting
                    break
                m = re.match(_BULLET_RE, line)
                if m:
                    lines.append(m.group(1).strip())
                elif line.strip() == "":
                    # blank lines are OK; keep going
                    continue
                else:
                    # non-bullet, non-empty: stop collecting
                    break
            if lines:
                return "\n".join(lines)
    return ""


def _extract_action_items(text: str) -> List[dict]:
    """Extract action items. Accept lines like '- [ ] Task (Due: yyyy-mm-dd)' or '- Task | 2025-08-03'.
    Returns list of dicts {task, dueDate}.
    """
    items = []
    # collect both from an Action Items header and any checkbox-style bullets
    block = _extract_bulleted_block(text, ["Action Items", "Actions", "Action"]) or ""
    if not block:
        # fallback: find any bullet that starts with '[ ]' or '[x]'
        candidates = re.findall(r"^[-*]\s*\[.?\]\s*(.+)$", text, flags=re.IGNORECASE | re.MULTILINE)
    else:
        candidates = block.splitlines()

    for line in candidates:
        # try pipe separated 'task | due'
        if isinstance(line, str):
            raw = line.strip()
        else:
            raw = str(line).strip()
        if not raw:
            continue
        parts = [p.strip() for p in re.split(r"\||\(Due:|_?Due:?\s", raw, maxsplit=1) if p and p.strip()]
        task = parts[0]
        due = parts[1] if len(parts) > 1 else ""
        # normalize due date (keep original if not parseable here)
        items.append({"task": task, "dueDate": due})
    return items


def parse_multiple_notes(path: str) -> List[Document]:
    """Parse a markdown file that may contain one or more meeting sections.

    Expected structured section starts with a heading like '\n## Meeting Title: <title>' or a standalone
    '## <title>' followed by '### Attendees' and '### Notes' blocks. The parser attempts a sensible
    fallback for unstructured single-meeting files (uses filename for title and extracts bullets).
    Returns a list of langchain Document objects with metadata including file_id, path, source, title,
    date, attendees and topic.
    """
    if not os.path.exists(path):
        return []

    raw = ""
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    except Exception:
        return []

    docs: List[Document] = []

    # Heuristic: split by a line that looks like '## Meeting Title' or '## <some title>' using a positive lookahead
    # split by heading; avoid using inline (?m) flags inside the pattern string to prevent
    # 'global flags not at the start' errors on some Python regex engines.
    # build a compiled split pattern to respect MULTILINE flags
    split_pat = re.compile(r"^##\s+Meeting Title\s*:|^##\s+(?=[A-Za-z0-9].*)", flags=re.MULTILINE)
    sections = split_pat.split(raw)
    # The split above will produce an initial preamble plus alternating title/body fragments; normalize
    if len(sections) <= 1:
        # fallback: treat the entire file as a single meeting
        title = _safe_extract_field(raw, [r"^#\s*(.+)", r"##\s*Meeting Title\s*:?"])
        # fallback to filename if no title found
        if not title:
            title = os.path.splitext(os.path.basename(path))[0]
        date = _safe_extract_field(raw, [r"\*\*Date\*\*\s*[:\-]?\s*(.+)", r"Date\s*[:\-]?\s*(.+)", r"(\d{4}-\d{2}-\d{2})"]) or _safe_extract_field(path, [r"(\d{4}-\d{2}-\d{2})"]) or ""
        attendees_raw = _safe_extract_field(raw, [r"\*\*Attendees\*\*\s*[:\-]?\s*(.+)", r"Attendees\s*[:\-]?\s*(.+)"])
        attendees = [a.strip() for a in re.split(r"[,;]\s*", attendees_raw) if a.strip()]
        notes = _extract_bulleted_block(raw, ["Notes", "Topics"]) or "\n".join(re.findall(_BULLET_RE, raw, flags=re.MULTILINE))
        actions = _extract_action_items(raw)
        file_id = _file_mtime_hash(path)
        content = f"Meeting Title: {title}\n\nAttendees:\n" + ("\n".join(attendees) if attendees else "(none)") + f"\n\nNotes:\n{notes or raw.strip()}"
        metadata = {"file_id": file_id, "path": path, "source": os.path.basename(path), "title": title, "date": date, "attendees": attendees, "topic": os.path.basename(os.path.dirname(path))}
        docs.append(Document(page_content=content, metadata=metadata))
        return docs

    # If we get here, try to parse multiple sections; normalize sections: some entries may be preamble
    # and others are 'title' then 'body' depending on how split worked.
    # Re-scan for explicit '## Meeting Title' anchors instead of relying on split fragility.
    # We'll find all headings that look like '## <title>' and capture the body until next '##'
    # compile with flags instead of inline modifiers
    pattern = re.compile(r"^##\s+(?P<title>.+)\s*$\n(?P<body>.*?)(?=^##\s+|\Z)", flags=re.DOTALL | re.MULTILINE)
    for m in pattern.finditer(raw):
        title = m.group("title").strip()
        body = m.group("body").strip()
        attendees_raw = _safe_extract_field(body, [r"\*\*Attendees\*\*\s*[:\-]?\s*(.+)", r"Attendees\s*[:\-]?\s*(.+)"])
        attendees = [a.strip() for a in re.split(r"[,;]\s*", attendees_raw) if a.strip()]
        notes = _extract_bulleted_block(body, ["Notes", "Topics"]) or ""
        actions = _extract_action_items(body)
        date = _safe_extract_field(body, [r"\*\*Date\*\*\s*[:\-]?\s*(.+)", r"Date\s*[:\-]?\s*(.+)", r"(\d{4}-\d{2}-\d{2})"]) or _safe_extract_field(title, [r"(\d{4}-\d{2}-\d{2})"]) or ""
        file_id = hashlib.md5(f"{path}:{title}:{date}".encode()).hexdigest()
        if not notes and not actions:
            # skip empty meeting sections
            continue
        content = f"Meeting Title: {title}\n\nAttendees:\n" + ("\n".join(attendees) if attendees else "(none)") + f"\n\nNotes:\n{notes}"
        metadata = {"file_id": file_id, "path": path, "source": os.path.basename(path), "title": title, "date": date, "attendees": attendees, "topic": os.path.basename(os.path.dirname(path))}
        docs.append(Document(page_content=content, metadata=metadata))

    return docs

