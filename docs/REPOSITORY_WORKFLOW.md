# Repository Workflow (Existing GitHub Repository)

Use this from `D:\GitHub\public-procurement-opportunity-intelligence`. Do not run `git init` again because this is already an existing repository.

```powershell
git rev-parse --show-toplevel
git branch --show-current
git status --short
python -m pytest tests -q
```

After reviewing changes:

```powershell
git add .
git commit -m "Consolidate procurement project sources and documentation"
git push origin main
```

Before committing, confirm no `.env`, API key, local virtual environment, cache, raw private company documents or unnecessary generated model artifacts are staged. `git status --short` shows changed and untracked files. The consolidation helper does not commit or push automatically.
