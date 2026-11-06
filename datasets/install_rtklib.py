"""Install only the six pinned RTKLIB files, outside the repository."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen


def install(project):
    entries = json.loads((project/"datasets/rtklib_binaries.json").read_text())
    target = project.parent/"external/RTKLIB_bin"
    target.mkdir(parents=True, exist_ok=True)
    for item in entries:
        name = item["file"]
        if Path(name).name != name or not item["url"].startswith(
                "https://raw.githubusercontent.com/tomojitakasu/RTKLIB_bin/rtklib_2.4.3/bin/"):
            raise ValueError("Unexpected RTKLIB manifest entry.")
        path = target/name
        if path.exists():
            if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
                raise ValueError(f"Existing {name} differs from the pinned version; inspect it first.")
            continue
        temporary = target/(name+".partial")
        h = hashlib.sha256()
        size = 0
        with urlopen(item["url"], timeout=120) as response, temporary.open("wb") as out:
            for block in iter(lambda: response.read(2**20), b""):
                size += len(block)
                h.update(block)
                out.write(block)
        if h.hexdigest() != item["sha256"] or size != item["bytes"]:
            temporary.unlink()
            raise ValueError(f"Checksum or size mismatch: {name}")
        temporary.replace(path)
        print(f"Installed {name} ({size} bytes).", flush=True)
    print("Pinned RTKLIB files are ready.")
