#!/usr/bin/env python3
"""Prepare only reviewed cloud source files for Vercel's source deployment API."""
import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLOUD = ROOT / 'cloud'
ROOT_FILES = ('package.json', 'package-lock.json', 'tsconfig.json', 'next-env.d.ts', 'next.config.ts', 'vercel.json')
SOURCE_DIRS = ('app', 'lib', 'components')


def manifest():
    paths = [CLOUD / name for name in ROOT_FILES]
    for directory in SOURCE_DIRS:
        paths.extend(p for p in (CLOUD / directory).rglob('*') if p.is_file() and p.suffix in ('.ts', '.tsx', '.css'))
    result = []
    for path in sorted(set(paths)):
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(CLOUD.resolve()):
            raise ValueError('Unexpected deployment source path.')
        content = path.read_bytes()
        if len(content) > 2 * 1024 * 1024:
            raise ValueError('Unexpected deployment file size.')
        result.append({'file': path.relative_to(CLOUD).as_posix(), 'data': base64.b64encode(content).decode('ascii'), 'encoding': 'base64'})
    return result


if __name__ == '__main__':
    output = ROOT / '.runtime' / 'deploy-manifest.json'
    output.parent.mkdir(mode=0o700, exist_ok=True)
    data = manifest()
    output.write_text(json.dumps(data))
    output.chmod(0o600)
    print(f'Prepared {len(data)} reviewed cloud source files. No local configuration, credentials, fixtures, database scripts, or raw activity files included.')
