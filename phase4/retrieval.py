"""Offline, provenance-aware extractive document retrieval (stdlib only).

Every evidence quote is anchored to exact local file line numbers and a verified
SHA-256. Source content is UNTRUSTED data, never executable instructions.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / 'knowledge_manifest.json'
DOCS = ROOT / 'docs'
MAX_DOC_BYTES = 512_000
MAX_CHUNKS = 10_000
MAX_CHARS = 1000
WORD_RE = re.compile(r'[a-z0-9]+', re.I)
STOPWORDS = frozenset('the a an and or is are does do to for of on in with from by at as it its this that these those can could should would what which when where how why i we you your my our be been need use about there given please help me tell if has have been also than then one into must not all was were am'.split())


class SourceError(ValueError):
    pass


@dataclass(frozen=True)
class Chunk:
    source_id: str
    title: str
    revision: str
    status: str
    path: str
    sha256: str
    start_line: int
    end_line: int
    text: str

    @property
    def citation(self) -> str:
        return f'{self.source_id}:L{self.start_line}-L{self.end_line}'


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float
    shared_terms: int


def terms(text: str) -> list[str]:
    result = []
    for w in WORD_RE.findall(text.lower()):
        if w not in STOPWORDS and len(w) > 1:
            if len(w) > 5 and w.endswith('ies'):
                w = w[:-3] + 'y'
            elif len(w) > 4 and w.endswith('s') and not w.endswith('ss'):
                w = w[:-1]
            result.append(w)
    return result


def _manifest(path: Path):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceError(f'Cannot read valid manifest: {exc}') from exc
    if data.get('schema_version') != 1 or not isinstance(data.get('sources'), list):
        raise SourceError('Manifest needs schema_version=1 and sources array.')
    return data


def _resolve_source(item: dict, root: Path) -> Path:
    raw = item.get('path')
    if not isinstance(raw, str) or not raw or '\\' in raw:
        raise SourceError('Source path must be a relative forward-slash path.')
    pure = PurePosixPath(raw)
    if pure.is_absolute() or '..' in pure.parts or not pure.parts or pure.parts[0] != 'docs':
        raise SourceError(f'Unsafe document path: {raw}')
    path = (root / raw).resolve(strict=True)
    if not path.is_relative_to((root / 'docs').resolve()):
        raise SourceError(f'Document escapes the docs directory: {raw}')
    if path.suffix.lower() not in ('.md', '.txt') or not path.is_file():
        raise SourceError('Only plain .md and .txt local files are allowed.')
    return path


def _validate_approval(item: dict):
    status = item.get('status')
    if status not in ('public', 'draft', 'approved'):
        raise SourceError('Document status must be public, draft, or approved.')
    if status == 'approved':
        reviewer = item.get('reviewer')
        approval_date = item.get('approved_date')
        if not isinstance(reviewer, str) or len(reviewer.strip()) < 3:
            raise SourceError('An approved-labelled file must name its human reviewer.')
        try:
            date.fromisoformat(approval_date)
        except (ValueError, TypeError):
            raise SourceError('An approved-labelled file must have YYYY-MM-DD review date.')


def _paragraph_chunks(lines: list[str], meta: dict) -> list[Chunk]:
    # Paragraphs retain line intervals. Very long paragraphs split at line
    # boundaries. Single oversized lines are rejected to preserve citations.
    result = []
    batch = []
    start = 0

    def flush():
        nonlocal batch, start
        if not batch:
            return
        text = '\n'.join(batch).strip()
        if text and terms(text):
            result.append(Chunk(
                source_id=meta['id'], title=meta['title'], revision=meta['revision'],
                status=meta['status'], path=meta['path'], sha256=meta['sha256'],
                start_line=start, end_line=start + len(batch) - 1, text=text,
            ))
        batch = []
        start = 0

    for i, line in enumerate(lines, 1):
        if len(line) > MAX_CHARS:
            raise SourceError(f'{meta["id"]}: line {i} exceeds {MAX_CHARS} characters.')
        if not line.strip():
            flush()
        else:
            if batch and sum(len(x) + 1 for x in batch) + len(line) > MAX_CHARS:
                flush()
            if not batch:
                start = i
            batch.append(line)
    flush()
    return result


def load_corpus(root: Path = ROOT, strict: bool = True) -> list[Chunk]:
    """Validate every declared public or approved document.

    This ensures a changed checksum is never silently accepted. Default only
    includes sources operator-labelled approved; software cannot verify reviewer.
    """
    data = _manifest(root / 'knowledge_manifest.json')
    seen_ids = set()
    seen_paths = set()
    chunks: list[Chunk] = []
    for item in data['sources']:
        if not isinstance(item, dict):
            raise SourceError('All sources must be metadata objects.')
        sid = item.get('id')
        if not isinstance(sid, str) or not re.fullmatch(r'[A-Z0-9][A-Z0-9_-]{2,63}', sid):
            raise SourceError('Source IDs must be unique uppercase ASCII identifiers.')
        if sid in seen_ids:
            raise SourceError(f'Duplicate source ID: {sid}')
        seen_ids.add(sid)
        _validate_approval(item)
        for k in ('title', 'revision', 'sha256'):
            if not isinstance(item.get(k), str) or not item[k]:
                raise SourceError(f'{sid} missing {k}.')
        if not re.fullmatch(r'[a-f0-9]{64}', item['sha256']):
            raise SourceError(f'{sid} has an invalid sha256.')
        try:
            path = _resolve_source(item, root)
            if path in seen_paths:
                raise SourceError(f'Duplicate file in manifest: {path.name}')
            seen_paths.add(path)
            content = path.read_bytes()
        except OSError as exc:
            raise SourceError(f'Cannot load source {sid}: {exc}') from exc
        if len(content) > MAX_DOC_BYTES:
            raise SourceError(f'{sid} exceeds size limit.')
        digest = hashlib.sha256(content).hexdigest()
        if digest != item['sha256']:
            raise SourceError(f'{sid} checksum mismatch: source changed since registration; re-review and re-index.')
        try:
            body = content.decode('utf-8')
        except UnicodeDecodeError as exc:
            raise SourceError(f'{sid} is not UTF-8.') from exc
        if item['status'] in ('public', 'approved'):
            chunks.extend(_paragraph_chunks(body.splitlines(), item))
            if len(chunks) > MAX_CHUNKS:
                raise SourceError('Index exceeded 10,000 chunks.')
    return chunks


def search(question: str, chunks: list[Chunk], top_k: int = 3) -> list[Hit]:
    """Small transparent BM25 retrieval, conservative lexical evidence threshold."""
    q_terms = set(terms(question))
    if not q_terms or not chunks or top_k < 1:
        return []
    tokenized = [Counter(terms(c.text)) for c in chunks]
    doc_freq = Counter(word for tf in tokenized for word in tf)
    avg_len = sum(sum(tf.values()) for tf in tokenized) / len(tokenized)
    results = []
    for chunk, tf in zip(chunks, tokenized):
        overlap = q_terms.intersection(tf)
        # Refuse vague single-term associations, even when BM25 is high.
        if len(overlap) < 2:
            continue
        coverage = len(overlap) / len(q_terms)
        if coverage < 0.30:
            continue
        score = 0.0
        dl = sum(tf.values())
        for t in overlap:
            idf = math.log1p((len(chunks) - doc_freq[t] + 0.5) / (doc_freq[t] + 0.5))
            score += idf * tf[t] * (2.2) / (tf[t] + 1.2 * (0.25 + 0.75 * dl / max(avg_len, 1)))
        if score < 0.75:
            continue
        results.append(Hit(chunk=chunk, score=round(score, 5), shared_terms=len(overlap)))
    results.sort(key=lambda h: (-h.score, h.chunk.source_id, h.chunk.start_line))
    # Return the top distinct paragraphs; a multi-source answer cannot be assumed
    # to establish a single harmonized procedure.
    chosen = []
    for hit in results:
        if any(h.chunk.citation == hit.chunk.citation for h in chosen):
            continue
        chosen.append(hit)
        if len(chosen) == top_k:
            break
    return chosen
