"""Fetch the pinned GLIO source outside the upload tree and apply its patch."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

here=Path(__file__).resolve().parent
project=here.parent.parent
lock=json.loads((here/'source_lock.json').read_text(encoding='utf-8'))
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--destination',type=Path,default=project.parent/'external/GLIO')
args=parser.parse_args()
destination=args.destination.resolve()
if destination==project or project in destination.parents:
    raise SystemExit('Use a destination outside the publication repository.')
patch=here/lock['patch']
if hashlib.sha256(patch.read_bytes()).hexdigest()!=lock['patch_sha256']:
    raise SystemExit('Patch checksum mismatch.')
def git(*arguments,check=True):
    return subprocess.run(['git','-C',str(destination),*arguments],check=check,text=True,capture_output=True)
if not destination.exists():
    destination.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(['git','clone',lock['upstream_url'],str(destination)],check=True)
    git('checkout','--detach',lock['base_commit'])
elif not (destination/'.git').exists():
    raise SystemExit('Existing destination is not a Git checkout; no files were changed.')
if git('rev-parse','HEAD').stdout.strip()!=lock['base_commit']:
    raise SystemExit('Existing checkout has a different revision; no files were changed.')
if git('status','--porcelain').stdout.strip():
    raise SystemExit('Existing checkout has changes; inspect them before applying a patch.')
git('apply','--check',str(patch))
git('apply',str(patch))
print('Prepared GLIO source:',destination)
print('Modes: LC, TC_Pose and TC_Surface. No model training is required.')
