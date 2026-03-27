# Globale Präferenzen

## Sprache
- Antworten: Deutsch
- Code, Kommentare, Commits, Branch-Namen: Englisch

## Arbeitsweise
- Bei Unklarheiten: nachfragen statt Annahmen treffen
- Neue Dependencies: immer begründen warum

## Git
- Kleine Commits, ein logischer Schritt pro Commit
- Conventional Commits (feat:, fix:, refactor:, chore:)
- Branches als feature/<thema> oder bugfix/<thema>
- IMPORTANT: Secrets gehören in .env — nie committen, nie in Output zeigen

## Umgebung
- GitHub (Username: mvroeder)
- Keine absoluten Pfade in Configs — Projekte laufen auf mehreren Maschinen

## Datenquellen
- **Apple Erinnerungen**: Bidirektionaler Sync mit `~/Cowork/productivity/TASKS.md`
  - `~/reminders-export.json` — Rohdaten, alle 15 Min via launchd aktualisiert
  - `~/Cowork/productivity/reminders-mapping.json` — Name→ID Mapping für Rückkanal
  - Voller Sync (beide Richtungen): `python3 ~/.claude/tools/sync-reminders.py`
  - Einzelne Reminder updaten: `~/.claude/tools/update-reminder <id> <action> [value]`
    - Actions: `complete`, `uncomplete`, `due <YYYY-MM-DD>`, `due none`, `title <text>`, `note <text>`, `priority <0-9>`
  - Wenn Tasks in TASKS.md als erledigt markiert werden (`[x]`), wird das bei nächstem Sync an Apple Reminders gepusht

# Project rules

## General
- Be concise and precise.
- Prefer minimal, reversible changes.
- Explain major architectural decisions briefly before implementing.

## Security
- Do not read, print, copy, summarise or modify `.env` files unless explicitly instructed.
- Never expose secrets, API keys, tokens, passwords or credentials.
- Use `.env.example` for configuration structure, not `.env`.

## Code changes
- Prefer small diffs.
- Preserve the existing style unless there is a strong reason to improve it.
- When changing multiple files, state the plan first.

## Validation
- After code changes, suggest the exact command to test locally.
- Flag assumptions explicitly.