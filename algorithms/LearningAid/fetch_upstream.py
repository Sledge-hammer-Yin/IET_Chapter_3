"""Fetch and check the fixed upstream source versions outside the repository."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def verify(destination, source):
    for name, expected in source['files'].items():
        path = destination / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError(f'Source checksum mismatch: {source["name"]}/{name}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, default=REPO.parent / 'external/LearningAid')
    args = parser.parse_args()
    destination = args.destination.resolve()
    if destination == REPO or REPO in destination.parents:
        raise SystemExit('Keep upstream checkouts outside the publication repository.')
    lock = json.loads((HERE / 'source_lock.json').read_text(encoding='utf-8'))
    for source in lock['repositories']:
        if not source['runtime_required']:
            continue
        if not re.fullmatch(r'[A-Za-z0-9_-]+', source['name']):
            raise ValueError('Invalid source name.')
        path = destination / source['name']
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(['git', 'init', str(path)], check=True)
            subprocess.run(['git', '-C', str(path), 'remote', 'add', 'origin', source['url']], check=True)
            subprocess.run(['git', '-C', str(path), 'fetch', '--depth', '1', 'origin', source['commit']], check=True)
            subprocess.run(['git', '-C', str(path), 'checkout', '--detach', 'FETCH_HEAD'], check=True)
        if (path / '.git').exists():
            head = subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'], text=True).strip()
            if head != source['commit']:
                raise RuntimeError(f'Existing source has another revision: {path}')
        else:
            revision = path / 'UPSTREAM_REVISION.json'
            if not revision.is_file() or json.loads(revision.read_text())['commit'] != source['commit']:
                raise RuntimeError(f'Existing directory is not the recorded source: {path}')
        verify(path, source)
        print(f'Checked {source["name"]}: {source["commit"]}')
    print('Runtime source checks passed. No datasets were downloaded.')


if __name__ == '__main__':
    main()
