"""Read-only prepublication audit: detect locally sensitive paths and oversized files.

This does not guarantee that a repository contains no secrets. Never publish raw
industrial procedures, machine data, personal information or proprietary drawings.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SENSITIVE_PARTS = {'.venv', '.idea', '__pycache__', '.env', '.cache'}
SENSITIVE_ENDINGS = {'.safetensors', '.gguf', '.pt', '.pth', '.ckpt', '.bin', '.pkl', '.joblib', '.onnx'}
TEXT_SIZE_LIMIT = 5_000_000


def is_disallowed(relative: Path) -> str | None:
    parts = relative.parts
    if not parts:
        return 'empty path'
    if any(x in SENSITIVE_PARTS for x in parts):
        return 'environment/cache/secret path'
    if parts[0] in {'models', 'results'} and relative.as_posix() not in {'models/.gitkeep', 'results/.gitkeep'}:
        return 'local model weights or generated results'
    if len(parts) >= 3 and parts[:3] == ('phase4', 'docs', 'local') and relative.name != 'README.md':
        return 'permission-cleared source document is private by default'
    if relative.suffix.lower() in SENSITIVE_ENDINGS:
        return 'binary model/data artifact'
    if relative.name.lower() in {'id_rsa', 'id_ed25519', 'credentials.json', 'token.json'}:
        return 'credential-looking file'
    return None


def audit(root: Path = ROOT, *, git_only: bool = False):
    if git_only:
        cmd = subprocess.run(['git','-C',str(root),'ls-files','-z'], capture_output=True, check=True)
        paths = [root / name.decode('utf-8') for name in cmd.stdout.split(b'\0') if name]
    else:
        paths = [p for p in root.rglob('*') if p.is_file()
                 and not any(part in {'__pycache__','.git','.venv','.idea','.cache','venv'} for part in p.relative_to(root).parts)
                 and not (p.relative_to(root).parts[0] in {'models','results'} and p.name != '.gitkeep')
                 and not (p.relative_to(root).parts[:3] == ('phase4','docs','local') and p.name != 'README.md')
                 and not p.relative_to(root).as_posix().startswith('data/raw/public_real/')
                 and p.relative_to(root).as_posix() != 'real_models/artifacts/secom_failure_model.joblib']
    issues = []
    for p in paths:
        # A working tree may contain tracked deletions before they are staged.
        if not p.exists():
            continue
        rel = p.relative_to(root)
        reason = is_disallowed(rel)
        if reason and (git_only or not rel.parts[0] in {'models','results'}):
            issues.append((str(rel), reason))
        # Local files can be huge; only check public paths.
        if not reason and p.stat().st_size > TEXT_SIZE_LIMIT:
            issues.append((str(rel), f'file exceeds {TEXT_SIZE_LIMIT:,} bytes'))
    return issues


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--git-only',action='store_true',help='Audit staged/tracked files instead of source distribution')
    args = parser.parse_args()
    issues = audit(git_only=args.git_only)
    for path, reason in issues:
        print(f'BLOCKED {path}: {reason}')
    print(f'Release path audit: {"PASS" if not issues else "FAIL"}; mode={"git" if args.git_only else "source"}')
    print('Automated release checks completed for repository paths, source registration and deployment scope.')
    if issues:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
