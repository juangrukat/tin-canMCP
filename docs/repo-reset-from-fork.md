# Reset GitHub Fork to a New Standalone Repo

Your local remotes currently point to the old fork chain. Use this to fully detach `tin-canMCP`.

## 1. Delete the accidental fork repo (GitHub)

GitHub UI:
- Open the fork repository in your browser.
- Go to `Settings`.
- Scroll to `Danger Zone`.
- Click `Delete this repository` and confirm.

Optional GitHub CLI (if authenticated):

```bash
gh repo delete <your-username>/<fork-repo-name> --yes
```

## 2. Remove old remotes locally

```bash
git remote remove upstream
git remote remove origin
```

## 3. Create a brand-new repo on GitHub

Create a new empty repo named `tin-canMCP` (no template, no README/license).

## 4. Attach new origin and push

```bash
git remote add origin https://github.com/<your-username>/tin-canMCP.git
git push -u origin <your-branch>
```

Tip: check your current branch with:

```bash
git branch --show-current
```

## 5. Verify remotes

```bash
git remote -v
```

Expected: only one remote (`origin`) pointing at your new `tin-canMCP` repo.
