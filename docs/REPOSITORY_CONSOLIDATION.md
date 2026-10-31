# Repository Consolidation Guide

## Goal

`D:\GitHub\public-procurement-opportunity-intelligence` is the single source of truth for the procurement project. The older folder at `D:\b2b_opportunity_intelligence\b2b_opportunity_intelligence` remains an untouched backup. No Git history is copied or deleted by the consolidation helper.

## Apply the consolidation patch

1. Extract the supplied consolidation patch ZIP into the existing GitHub project root, merging/overwriting the listed files when prompted. Do **not** delete the existing project folder and do not replace `.git`.
2. Open PowerShell/IntelliJ Terminal at the GitHub project root and run the helper in merge-only mode:

```powershell
.\tools\consolidate_legacy_work.ps1
```

3. Test using the Python interpreter already used successfully for this project. In this machine's previous setup it was:

```powershell
& "D:\b2b_opportunity_intelligence\b2b_opportunity_intelligence\.venv\Scripts\python.exe" -m pytest tests -q
```

Historical note: the original consolidation snapshot reported 100 passing tests. The current release-candidate snapshot is separately validated at 192 passing tests; see `docs/RELEASE_CANDIDATE_STATUS.md` and `docs/FINAL_TESTING_GUIDE.md`. If the interpreter path differs, use the path shown by the known-good interpreter in IntelliJ.

4. Once tests pass, remove only the known temporary patch artifacts (not source files) by running:

```powershell
.\tools\consolidate_legacy_work.ps1 -RemoveTemporaryPatchArtifacts
```

5. Verify the root and Git state:

```powershell
git rev-parse --show-toplevel
git branch --show-current
git status --short
```

If an old file has the same destination name but different content, it preserves that distinct version under `docs/project_history/local_variants/` or `reports/archive/legacy_variants/` and does not overwrite the current canonical file. Identical content is skipped. The helper never commits or pushes. Review the changes before committing.

## What the helper carries forward

- Local-only `src/config.py` and `src/__init__.py`, if present and not duplicates.
- Local `app/README.md` (moved to `docs/app/APP_MODULE_NOTES.md`), `data/README.md`, `notebooks/README.md`, and `tests/README.md` if they contain unique content.
- The EDA missing/zero-value review PDF if present.
- Unique `reports/terminal_checks` files moved under `reports/archive/terminal_checks/`, deduplicated by SHA-256.
- The original cleaning, EDA, taxonomy and initial planning notes, into clearly named and organized documentation paths.

The helper does not copy nested versions of `clean_assam_procurement.py`, `review_niche_taxonomy.py`, or the older milestone trainer because the current canonical scripts already replace those functions. The smaller taxonomy keyword-fix test is covered by the broader refinement test and is not copied as a second test file.

Temporary patch notes and the duplicate `milestone1_missing_files_patch` directory are removed only when `-RemoveTemporaryPatchArtifacts` is specified and required canonical files are present. It does not touch the old folder, `.git`, `.venv`, or the existing GitHub history.

## Canonical places to look

Start at `README.md`, then use `docs/PROJECT_FILE_INDEX.md` to find source scripts, reports, tests, historical planning notes, ML artifacts and application modules. The current release status is in `docs/FINAL_PROJECT_STATUS.md`; the initial charter and execution plan are historical context, not a claim that every originally planned feature was built.
