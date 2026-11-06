# Upstream source access

The original checkout is not embedded in this English-only upload tree.
From the main repository root, run:

```text
python algorithms/GLIO/fetch_upstream.py
```

The source is fetched into the sibling external/GLIO folder at the exact revision
recorded in ../source_lock.json, then the verified estimator patch is applied.
See ../README.md for details. This folder is a regular documentation folder,
not a Git submodule in the manual publication export.
