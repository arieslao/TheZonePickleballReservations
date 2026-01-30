# Project Decisions Log

> Document significant architectural, technical, and design decisions here.
> Use the ADR (Architecture Decision Record) format for major decisions.

## How to Use This Log

For each significant decision, document:
1. **Context:** What situation prompted this decision?
2. **Decision:** What did we decide?
3. **Rationale:** Why did we choose this option?
4. **Consequences:** What are the implications?
5. **Alternatives Considered:** What other options were evaluated?

---

## Decisions

### 2026-01-29: Context Management System

**Context:** Need to maintain continuity across Claude Code chat sessions for long-term project development.

**Decision:** Implement a structured context system using:
- `CLAUDE.md` at project root (auto-read by Claude)
- `.claude/` directory for detailed documentation
- Standards documents for DevOps, HCD, and UI/UX
- Session handoff notes for continuity

**Rationale:**
- Claude Code automatically reads CLAUDE.md, making it ideal for essential context
- Structured documentation ensures consistent practices
- Session handoffs prevent context loss between conversations

**Consequences:**
- Must maintain documentation as project evolves
- Team members should update relevant docs after significant changes
- Provides single source of truth for project standards

**Alternatives Considered:**
- Single large context file (rejected: harder to maintain)
- External documentation only (rejected: not auto-read by Claude)

---

### 2026-01-30: Browser Automation with Playwright

**Context:** Need to automate booking on Skedda platform which has no public API.

**Decision:** Use Playwright for browser automation with saved session state.

**Rationale:**
- Skedda has no public API (only one-way webhooks)
- Playwright supports async operations and session persistence
- Can save login state to avoid re-authentication each run
- Cross-browser support if needed

**Consequences:**
- Dependent on Skedda's DOM structure (may break if UI changes)
- Requires browser installation (chromium)
- Session cookies may expire, requiring re-login

**Alternatives Considered:**
- Selenium (rejected: Playwright has better async support)
- Direct API calls (not possible: no public API)
- Manual booking (rejected: defeats automation purpose)

---

### 2026-01-30: Day View for Booking Detection

**Context:** Skedda offers multiple views (Day, Month, Grid, List, Map) for the booking calendar.

**Decision:** Use Day view exclusively for both availability checking and booking.

**Rationale:**
- Day view shows all courts side-by-side with clear time rows
- Easier to calculate click positions using column headers and time labels
- Visual consistency between check and book operations
- More reliable than Map view which has overlapping elements

**Consequences:**
- Navigation requires clicking forward one day at a time
- Detection relies on DOM element positions

**Alternatives Considered:**
- Map view (rejected: harder to detect availability, overlapping elements)
- Grid view (rejected: less intuitive for time-based detection)
- List view (rejected: doesn't show all courts simultaneously)

---

### 2026-01-30: Configuration via Environment Variables

**Context:** Need to easily change target time, courts, and days without editing code.

**Decision:** All configurable parameters read from `.env` file with sensible defaults.

**Rationale:**
- Easy to change settings without code knowledge
- Supports different environments (local vs GitHub Actions)
- Secrets (credentials) kept separate from code
- python-dotenv handles loading automatically

**Consequences:**
- Must keep `.env.example` updated with all options
- `.env` must not be committed (contains credentials)
- GitHub Actions will use repository secrets instead

**Alternatives Considered:**
- Command-line arguments (rejected: less convenient for scheduled runs)
- Config file (YAML/JSON) (rejected: adds complexity, .env is sufficient)
- Hardcoded values (rejected: inflexible)

---

### [Template for Future Decisions]

**Context:** [Describe the situation]

**Decision:** [What was decided]

**Rationale:** [Why this choice]

**Consequences:** [Implications and trade-offs]

**Alternatives Considered:** [Other options evaluated]

---
