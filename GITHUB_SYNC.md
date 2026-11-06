# Manual GitHub upload

Target: https://github.com/Sledge-hammer-Yin/IET_Chapter_3

Use the contents of `C:/UAV_Chapter3/github_upload/IET_Chapter_3` as the repository
root. This is the verified English-only publication export. Do not add another
outer IET_Chapter_3 folder when placing its contents in the remote repository.
Upload manually. No commit, push or remote change is performed by the export tool.
If using the GitHub website, upload root files and then folders in batches.
Check the existing remote tree before replacing files.

The export excludes `.git`, `.gitmodules`, the local upstream checkout, Python
bytecode, private archives, fonts, credentials and full datasets. It includes
the pinned GLIO source lock, checked patch and an English source fetcher.
The old local Git submodule is preserved in the working project, but the manual
upload export is a regular-file layout and does not depend on Git submodule metadata.

Before uploading, review PUBLICATION_AUDIT.json and UPLOAD_MANIFEST.sha256.
Do not upload the book Word file, GLIO_Server_Setup, _glio_remote_tools, data,
external checkouts, environment installations or backups.
After editing the working project, regenerate and recheck the publication export.
Keep this export separate from the working repository to prevent accidental
upload of local-only third-party comments or binary files.
