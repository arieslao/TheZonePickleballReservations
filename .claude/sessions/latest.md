# Session Handoff Notes

> Update this file at the end of significant sessions to maintain continuity.
> Previous sessions are archived in this directory with date prefixes.

## Current Session: 2026-01-30

### What Was Accomplished

#### Full Booking Workflow Implemented
- **Availability Checker** (`python sniper.py --check`): Checks all 6 Wood courts for the next 4 days
- **Booking Bot** (`python sniper.py`): Automatically books available slots
- **Login Setup** (`python sniper.py --setup`): Interactive login session saver

#### Key Features Working
1. **Day View Navigation**: Reliably switches to Day view and navigates forward by days
2. **Time Slot Detection**: Uses JavaScript DOM evaluation to find court columns and time rows
3. **Booking Flow**: Click slot → Click "Book" → Click "Confirm booking" → Success!
4. **Slack Notifications**: Sends availability reports and booking confirmations
5. **Configurable via .env**: All settings can be changed without editing code

#### Configuration Made Flexible
All key parameters now read from `.env`:
```bash
TARGET_START_HOUR=6      # 24-hour format (6=6AM, 19=7PM)
TARGET_END_HOUR=8        # End hour for display
TARGET_COURTS=Wood 3,Wood 2,Wood 4,Wood 6,Wood 1,Wood 5  # Priority order
DAYS_AHEAD_LIMIT=3       # Days ahead to book
```

### Current State
- **Script Location**: `/Users/arieslao/Desktop/TheZonePickleballReservations/sniper.py`
- **Session Auth**: Saved in `session_data/auth.json`
- **Test Booking Made**: Wood 3 at 6:30 AM on Monday, February 2, 2026 (NEEDS CANCELLATION)
- **Slack Configured**: Webhook working and sending notifications

### Script Commands
```bash
python sniper.py           # Run booking bot (books target time on target date)
python sniper.py --check   # Check availability only (no booking)
python sniper.py --setup   # Interactive login to save session
```

### How the Booking Works
1. Load saved session from `session_data/auth.json`
2. Navigate to Skedda booking page
3. Switch to Day view
4. Navigate forward N days (DAYS_AHEAD_LIMIT)
5. Use JavaScript to find court column positions and time row Y coordinate
6. Try each court in TARGET_COURTS order:
   - Click on slot position
   - If "Book" button appears → slot is available
   - Click "Book" → opens confirmation form
   - Click "Confirm booking" → completes reservation
7. Send Slack notification with results

### Next Steps
1. **Cancel test booking**: Manually cancel Wood 3, 6:30 AM, Monday Feb 2
2. **Update .env for production**: Change to TARGET_START_HOUR=19 for 7 PM target
3. **Create GitHub Actions workflow**: Automate daily checks
4. **Implement Slack interactive buttons**: Allow selecting alternatives from Slack (Option A design)

### Open Questions
- What time should the bot run daily? (Suggested: Just before midnight Manila time)
- Should it auto-book or just notify about availability?
- Should multiple time slots be checked in parallel?

### Important Context for Next Session
- The booking flow is **fully working** - tested successfully
- Detection relies on DOM positions, may need adjustment if Skedda UI changes
- Skedda has no public API - all interaction is via browser automation
- Zone allows booking 4 days ahead only

### Files Changed This Session
- **Modified**: `sniper.py` - Complete rewrite of booking workflow
- **Modified**: `.env` - Added booking configuration options
- **Modified**: `.env.example` - Added all configurable options with documentation
- **Created**: Multiple debug screenshots in project root

### Technical Notes

#### JavaScript DOM Detection (in sniper.py)
- Court columns found by searching for elements containing "Wood X Pickleball"
- Time rows found by matching regex `/^(1?[0-9]):00\s*(AM|PM)$/i`
- Click position = intersection of column centerX and time row Y

#### Key Selectors
- Day view tab: `button:has-text("Day")`
- Next day arrow: `button:has-text("›")`
- Book button: `button:has-text("Book")` (exact match "Book")
- Confirm button: `button:has-text("Confirm booking")`

---

## Session Archive
- 2026-01-29: Initial project setup, context management system
- 2026-01-30: Full booking workflow implementation (this session)
