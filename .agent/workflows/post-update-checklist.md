---
description: Always update .gitignore and README.md when the project is updated
---

# Post-Update Checklist

Whenever any structural change is made to the `telecom-test-toolkit` project (new files, deleted files, new dependencies, new plugins, config changes), you **must** update the following files before considering the work complete:

## 1. Update `.gitignore`

- Review newly added file types, build artifacts, or output directories
- Add entries for any new generated files (e.g. new report formats, cache files)
- Keep the file organized by category with clear section headers

## 2. Update `README.md`

- **Project Structure** section must reflect the actual directory tree
- **Plugins table** must list all registered plugins with correct names, types, and descriptions
- **Installation** instructions must list any new dependencies or install extras
- **Usage** examples must cover any new CLI commands or flags
- **Ecosystem Repositories** table must include any new tool repos

## 3. Verify consistency

- Confirm `pyproject.toml` entry-points match the actual plugin files in `ttt/plugins/`
- Confirm the project structure in README matches the real file tree
- Confirm `.gitignore` covers all build/output artifacts present in the repo
