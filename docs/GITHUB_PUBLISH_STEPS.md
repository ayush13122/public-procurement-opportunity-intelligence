# Publish to GitHub (Windows)

The ZIP package is a complete local project snapshot. The remote GitHub repository has not been created by this file bundle.

1. Sign in to GitHub and create an empty **public** repository named `public-procurement-opportunity-intelligence`. Do not add a README, `.gitignore`, or license on GitHub—the project already includes them.
2. Extract the project ZIP and open PowerShell in the extracted project root.
3. Run:

```powershell
git init -b main
git add .
git commit -m "Add historical procurement analysis pipeline"
git remote add origin https://github.com/ayush13122/public-procurement-opportunity-intelligence.git
git push -u origin main
```

4. Open the repo page to verify `README.md` renders, code and reports are present, and the source attribution is visible.
5. Pin the repository to your GitHub profile. Once the repository URL is live, the CV can be updated to link directly to it instead of only to the GitHub profile.

If PowerShell says `git` is not recognized, install Git for Windows and restart the terminal. If `remote origin already exists`, use `git remote -v` to inspect it before changing it.
