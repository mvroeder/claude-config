---
name: cora-email
description: Use when the user asks about their email, inbox, briefs, email todos, or wants to interact with Cora — an AI email assistant. Covers checking briefs, managing todos, drafting replies, and chatting with Cora via the CLI.
---

# Cora CLI — AI Email Assistant

Cora is an AI-powered email assistant that processes Gmail, generates daily briefs, manages todos, and drafts replies. You interact with Cora through the `cora` command-line tool.

## Quick Start

Before running any command, verify you're authenticated:

```
cora whoami
```

If not authenticated, log in with your API token:

```
cora login --token=<your_token>
```

## Commands Reference

### Check Status
```
cora status    # Account status, brief settings, usage stats
cora whoami    # Current user and account info
```

### Email Briefs
Cora processes your Gmail and generates AI-powered summaries:
```
cora brief              # List recent briefs (default 10)
cora brief show         # Show latest brief details
cora brief show <id>    # Show specific brief
cora brief show --open  # Show and open in browser
cora brief read <id>    # Mark brief as read
cora brief unread <id>  # Mark brief as unread
cora brief --format json  # JSON output for parsing
```

### Todos
Manage email-related todos:
```
cora todo list                                        # List pending todos
cora todo list --all                                  # Include completed
cora todo show <id>                                   # View details
cora todo create "Title"                              # Create new todo
cora todo create "Title" --priority high --due tomorrow  # With options
cora todo edit <id> --title "New" --priority low      # Update
cora todo complete <id>                               # Mark done
cora todo uncomplete <id>                             # Mark pending
cora todo delete <id> --force                         # Delete
cora todo delete-completed --force                    # Delete all completed
cora todo list --format json                          # JSON output
```

### Chat with Cora
Have conversations with Cora's AI assistant:
```
cora chat send "message"              # Start new conversation
cora chat send "message" --chat <id>  # Continue existing conversation
cora chat send "message" --no-stream  # Wait for complete response
cora chat list                        # List recent conversations
cora chat show <id>                   # View full chat history
```

### Other
```
cora open     # Open Cora dashboard in browser
cora prime    # Show full agent instructions
cora help     # List all commands
cora login    # Authenticate
cora logout   # Clear session
```

## Best Practices

- **Always verify auth first** — run `cora whoami` before other commands
- **Wait for each command to complete** — don't run commands in rapid succession
- **Use `--format json`** when you need to parse output programmatically
- **Don't retry failures more than once** — ask the user for guidance instead
- **Use `cora status`** to understand the user's current email setup and state

## Error Codes

- `0` — Success
- `1` — General error
- `2` — Authentication required (run `cora login`)
- `3` — Resource not found
- `4` — Validation error

## What Cora Does

Cora connects to the user's Gmail and:
1. Classifies emails by importance and category
2. Generates AI-powered briefs summarizing important emails
3. Can draft responses to emails
4. Manages email-related todos

The CLI provides read access to briefs, todos, and account status, plus the ability to chat with Cora's AI assistant.
