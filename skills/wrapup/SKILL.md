---
name: wrapup
description: Wrap up a coding session by committing, pushing, creating PRs, syncing docs, and saving open items to memory. Use at the end of a work session.
disable-model-invocation: true
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, AskUserQuestion
---

# Wrap Up Session

Ensure all work from the current session is committed, pushed, documented, and open items are persisted.

## Step 1: Assess Current State

Gather information about all repositories touched in this session:

```bash
git status
git diff --stat
git diff --cached --stat
git log --oneline -10
git branch --show-current
```

If not inside a git repo, ask the user which repo(s) to wrap up.

## Step 2: Stage and Commit Uncommitted Changes

For each set of uncommitted changes:

1. Show the user a summary of unstaged and staged changes
2. Group changes into logical commits (one logical step per commit)
3. Use Conventional Commits format (`feat:`, `fix:`, `refactor:`, `chore:`)
4. Ask the user for confirmation before each commit
5. Never commit `.env` files or secrets — warn if detected

If there are no uncommitted changes, skip to Step 3.

## Step 3: Push to Remote

1. Check if the current branch has an upstream:
   ```bash
   git rev-list --left-right --count origin/$(git branch --show-current)...HEAD 2>/dev/null
   ```
2. If there are unpushed commits, push:
   ```bash
   git push -u origin $(git branch --show-current)
   ```
3. If push fails (e.g. diverged), inform the user and ask how to proceed

## Step 4: Create or Update Pull Requests

1. Check if a PR already exists for this branch:
   ```bash
   gh pr list --head $(git branch --show-current) --json number,title,url
   ```
2. If no PR exists and the branch is not `main`/`master`:
   - Draft a PR title and summary based on all commits on this branch
   - Show the draft to the user for confirmation
   - Create the PR with `gh pr create`
3. If a PR already exists, check if it needs updating (new commits pushed)
4. Report the PR URL to the user

## Step 5: Sync Documentation

Check if documentation matches the current code state:

1. Look for common doc files:
   - `README.md`, `CHANGELOG.md`, `docs/` directory
   - API docs, config examples, architecture docs
2. Compare documented behavior with actual code changes from this session
3. If docs are out of sync:
   - Show the user what's outdated
   - Propose specific updates
   - Apply changes after confirmation
   - Commit doc changes separately: `docs: update [what] to reflect [change]`
   - Push the doc commit

If no documentation exists or docs are already in sync, skip to Step 6.

## Step 6: Save Open Items to Memory

Identify work that is still in progress or needs follow-up:

1. Check for:
   - TODO/FIXME comments added during this session
   - Failing tests or skipped tests
   - Branches with uncommitted work
   - Planned features mentioned but not implemented
   - Known issues discovered during the session
2. If open items exist:
   - Write a project memory file summarizing what's open, with context and next steps
   - Use absolute dates (not "tomorrow" or "next week")
   - Include branch names and file paths for easy pickup
3. Tell the user: "Offene Punkte wurden im Memory gespeichert."

## Step 7: Final Summary

Present a concise wrap-up to the user:

```
Session Wrap-Up:
- Commits: [count] new commits
- Pushed: [branch] -> origin
- PR: [URL or "none needed"]
- Docs: [updated / already in sync / none found]
- Open items: [count, brief list]
```

## Error Handling

- **Not a git repo**: Ask which directory to work in
- **No remote configured**: Warn and skip push/PR steps
- **gh CLI not available**: Warn and skip PR creation, suggest manual creation
- **Merge conflicts**: Do not auto-resolve — report to user
- **Permission denied on push**: Report and suggest checking credentials

## Self-Improvement Protocol

When you notice something that would improve this skill:
1. Append the insight to IMPROVEMENTS.md with date and context
2. Do NOT modify SKILL.md directly
3. Tell the user: "I logged a potential improvement for wrapup"
