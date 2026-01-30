# The Zone Pickleball Reservations - Project Context

> This file is automatically read by Claude Code at the start of each session.
> Last updated: 2026-01-30

## Project Overview

**Project Name:** The Zone Pickleball Reservations
**Purpose:** Automated booking system for The Zone Sports Center pickleball courts
**Tech Stack:** Python 3, Playwright (browser automation), Slack webhooks

## Quick Start

```bash
# Check availability for next 4 days
python sniper.py --check

# Run booking bot (books target time slot)
python sniper.py

# Setup login session (interactive)
python sniper.py --setup
```

## Configuration (.env)

```bash
TARGET_START_HOUR=19     # 7 PM (24-hour format)
TARGET_END_HOUR=21       # 9 PM
TARGET_COURTS=Wood 3,Wood 2,Wood 4,Wood 6,Wood 1,Wood 5
DAYS_AHEAD_LIMIT=4       # Days ahead to book
```

## Quick Links to Context

- [Project Decisions Log](.claude/decisions.md)
- [Session Handoff Notes](.claude/sessions/latest.md)
- [DevOps Standards](.claude/standards/devops.md)

## Current Sprint/Focus

- [x] Full booking workflow implementation
- [x] Configurable via .env
- [x] Slack notifications
- [ ] Cancel test booking (Wood 3, 6:30 AM, Monday Feb 2)
- [ ] GitHub Actions workflow
- [ ] Slack interactive buttons for alternatives

## Architecture Overview

```
sniper.py
├── run()              # Main booking workflow
├── check_availability()  # Check-only mode
├── setup_session()    # Interactive login saver
├── send_slack_message()  # Notifications
└── format_*()         # Message formatting

session_data/
└── auth.json          # Saved browser session

.env                   # Configuration (not committed)
```

## Key Decisions Made

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-29 | Context management system | Enable continuity across chat sessions |
| 2026-01-30 | Playwright for automation | Skedda has no API, browser automation required |
| 2026-01-30 | Day view for detection | Most reliable for position-based slot detection |
| 2026-01-30 | Environment variables | Easy config without code changes |

## Code Standards

### General
- Follow established patterns in the codebase
- Write self-documenting code with minimal comments
- Keep functions small and focused

### Skedda Detection Notes
- Court columns: Find elements containing "Wood X Pickleball"
- Time rows: Match `/^(1?[0-9]):00\s*(AM|PM)$/i` in left margin
- Booking: Click slot → "Book" button → "Confirm booking" button

## Environment Notes

- **Branch Strategy:** main is the primary branch
- **Environment Files:** `.env` contains credentials and config (never commit)
- **Session State:** `session_data/auth.json` contains Skedda login cookies

## Session Continuity Instructions

At the **start** of each session, Claude should:
1. Read this CLAUDE.md file (automatic)
2. Check `.claude/sessions/latest.md` for handoff notes
3. Review recent decisions if relevant to the task

At the **end** of significant sessions, update:
1. `.claude/sessions/latest.md` with handoff notes
2. `.claude/decisions.md` with any new decisions
3. This file if architecture/overview changes

---
*For detailed standards and guidelines, see the `.claude/standards/` directory.*
