"""Register permitted local plaintext source with explicit provenance metadata.

Records operator-provided approval claims; does NOT authenticate any human review.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import shutil

from phase4.retrieval import DOCS, MANIFEST, MAX_DOC_BYTES, SourceError, _manifest, _validate_approval


def register(source: Path, source_id: str, title: str, revision: str, status: str = 'draft',
             reviewer: str | None = None, approved_date: str | None = None,
             confirm_reviewed: bool = False, root: Path | None = None) -> Path:
    root = root or MANIFEST.parent
    if not re.fullmatch(r'[A-Z0-9][A-Z0-9_-]{2,63}', source_id):
        raise SourceError('Use a unique uppercase source ID, 3-64 chars (A-Z, 0-9, - or _).')
    if not title.strip() or not revision.strip():
        raise SourceError('A source title and revision are required.')
    source = source.expanduser().resolve(strict=True)
    if not source.is_file() or source.suffix.lower() not in ('.md', '.txt'):
        raise SourceError('Source must be an existing .md or .txt UTF-8 file.')
    raw = source.read_bytes()
    if len(raw) > MAX_DOC_BYTES:
        raise SourceError('Document larger than 512 KB; split it first.')
    raw.decode('utf-8')
    entry = {
        'id': source_id, 'path': f'docs/local/{source_id}{source.suffix.lower()}',
        'title': title.strip(), 'revision': revision.strip(), 'status': status,
        'reviewer': reviewer.strip() if reviewer else None, 'approved_date': approved_date,
        'sha256': hashlib.sha256(raw).hexdigest(),
    }
    _validate_approval(entry)
    if status == 'approved' and not confirm_reviewed:
        raise SourceError('To record an approved status, a real human must have reviewed it; explicitly pass --confirm-reviewed.')
    data = _manifest(root / 'knowledge_manifest.json')
    if any(it['id'] == source_id for it in data['sources']):
        raise SourceError('Source ID already exists; revision changes require a new source registration process.')
    target = root / entry['path']
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise SourceError('Target document already exists; refusing overwrite.')
    target.write_bytes(raw)
    data['sources'].append(entry)
    manifest = root / 'knowledge_manifest.json'
    temp = manifest.with_suffix('.tmp')
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    temp.replace(manifest)
    return target


def main():
    p = argparse.ArgumentParser(description='Add a permission-cleared UTF-8 .md or .txt to Phase 4 source manifest')
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--id', required=True)
    p.add_argument('--title', required=True)
    p.add_argument('--revision', required=True)
    p.add_argument('--status', choices=('draft', 'approved'), default='draft')
    p.add_argument('--reviewer', help='Full name of actual reviewer, only for approved sources')
    p.add_argument('--approved-date', help='Actual approval date YYYY-MM-DD, only for approved sources')
    p.add_argument('--confirm-reviewed', action='store_true', help='Confirm human review actually happened')
    a = p.parse_args()
    try:
        target = register(a.source, a.id, a.title, a.revision, a.status,
                          a.reviewer, a.approved_date, a.confirm_reviewed)
    except (SourceError, ValueError, OSError, UnicodeError) as exc:
        p.error(str(exc))
    print('Registered', target)
    print('Status is operator-provided metadata, NOT independently verified.')
    print('Retrieval will check the file SHA-256 before quoting it.')


if __name__ == '__main__':
    main()
