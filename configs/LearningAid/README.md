# Learning experiment configuration

`protocol.json` records the three experiment groups, full-sequence splits,
training seeds, model settings and figure settings for `20261107_cpu_v1`.
Its contents are unchanged from the server experiment.

`requirements-linux.lock.txt` records the server package versions. Use Python
3.12 and the CPU PyTorch index. The original local TASGNSS installation path
was removed; install the pinned checkout with `--no-deps` after fetching sources.
The installed Linux environment is not a Windows environment.

`requirements-plot.txt` is the smaller dependency list for validation and plotting.
Times New Roman must be available locally. Font files are not redistributed.
