"""Check local models or download them when a public asset is available."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import urllib.request

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def main():
    manifest = json.loads((HERE / 'models.json').read_text(encoding='utf-8'))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, default=REPO.parent / 'models/Chapter3_3.5' / manifest['run_id'])
    args = parser.parse_args()
    destination = args.destination.resolve()
    if destination == REPO or REPO in destination.parents:
        raise SystemExit('Keep model files outside the publication repository.')
    for name, expected in manifest['files'].items():
        path = destination / name
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit(f'Existing model differs; no files were replaced: {path}')
    if all((destination / name).is_file() for name in manifest['files']):
        print('Recorded models are already present and checked.')
        return
    if not manifest.get('url'):
        raise SystemExit('Recorded weights are not publicly hosted. Restore a local copy or train with a new model directory.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='learning_models_', dir=destination.parent) as temp:
        archive = Path(temp) / 'models.tar.gz'
        with urllib.request.urlopen(manifest['url']) as source, archive.open('wb') as out:
            shutil.copyfileobj(source, out)
        with archive.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != manifest['sha256']:
                raise ValueError('Model archive checksum mismatch.')
        with tarfile.open(archive) as tar:
            members = [m for m in tar if m.isfile()]
            if len(members) != len(manifest['files']):
                raise ValueError('Unexpected model archive size.')
            for member in members:
                if member.name not in manifest['files']:
                    raise ValueError('Unexpected archive entry.')
                path = (destination / member.name).resolve()
                if not path.is_relative_to(destination):
                    raise ValueError('Unsafe archive path.')
                content = tar.extractfile(member).read()
                if hashlib.sha256(content).hexdigest() != manifest['files'][member.name]:
                    raise ValueError('Model checksum mismatch.')
            for member in members:
                path = destination / member.name
                if not path.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(tar.extractfile(member).read())
    print('Trained models downloaded and checked. No sensor data were downloaded.')


if __name__ == '__main__':
    main()
