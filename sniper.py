import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path
import pytz
import requests
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# Load environment variables from .env file (for local testing)
load_dotenv()

# --- CONFIGURATION ---
# These can be overridden via .env file for easy adjustment

# Courts to check in priority order (comma-separated in .env, e.g., "Wood 3,Wood 1,Wood 2")
_court_env = os.environ.get("TARGET_COURTS", "")
if _court_env:
    TARGET_COURT_KEYWORDS = [c.strip() for c in _court_env.split(",")]
else:
    TARGET_COURT_KEYWORDS = ["Wood 1", "Wood 2", "Wood 3", "Wood 4", "Wood 5", "Wood 6"]

# Target time slot (24-hour format in .env, e.g., TARGET_START_HOUR=19 for 7PM)
TARGET_START_HOUR = int(os.environ.get("TARGET_START_HOUR", "19"))   # Default: 7 PM
TARGET_END_HOUR = int(os.environ.get("TARGET_END_HOUR", "21"))       # Default: 9 PM
TARGET_DURATION_MINS = int(os.environ.get("TARGET_DURATION_MINS", "120"))  # Default: 2 hours

# Alternative slots: start checking from this hour (e.g., 17 = 5:00 PM)
ALT_START_HOUR = int(os.environ.get("ALT_START_HOUR", "17"))  # Default: 5 PM

# Booking window: How many days ahead to check/book
# The Zone only allows booking 4 days ahead
DAYS_AHEAD_LIMIT = int(os.environ.get("DAYS_AHEAD_LIMIT", "4"))

# Target day of week: Wednesday (0=Monday, 1=Tuesday, 2=Wednesday, etc.)
# NOTE: With a 4-day limit, to book Wednesday you must run on SATURDAY night
# (Saturday midnight -> Sunday, Sunday + 3 days = Wednesday... or Sat + 4 = Wed)
# Schedule mapping for 4-day window:
#   To book Monday    -> Run on Thursday night (Fri + 3 days = Mon)
#   To book Tuesday   -> Run on Friday night (Sat + 3 days = Tue)
#   To book Wednesday -> Run on Saturday night (Sun + 3 days = Wed)
#   To book Thursday  -> Run on Sunday night (Mon + 3 days = Thu)
#   To book Friday    -> Run on Monday night (Tue + 3 days = Fri)
#   To book Saturday  -> Run on Tuesday night (Wed + 3 days = Sat)
#   To book Sunday    -> Run on Wednesday night (Thu + 3 days = Sun)
TARGET_DAY_OF_WEEK = 2  # Wednesday (desired booking day)

MANILA_TZ = pytz.timezone('Asia/Manila')
URL_BOOKING = "https://zonemakati.skedda.com/booking"

# Enable waiting for midnight (set to True for production)
# Read from env: ENABLE_WAIT_FOR_MIDNIGHT=true
ENABLE_WAIT_FOR_MIDNIGHT = os.environ.get("ENABLE_WAIT_FOR_MIDNIGHT", "false").lower() == "true"

# Run with visible browser for local testing (set to True for GitHub Actions)
# Read from env: HEADLESS_MODE=true
HEADLESS_MODE = os.environ.get("HEADLESS_MODE", "false").lower() == "true"

# Session storage path (for persistent login)
SESSION_DIR = Path(__file__).parent / "session_data"

# Slack notifications (optional)
# Set SLACK_WEBHOOK_URL in .env or GitHub Secrets to enable
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")


def send_slack_message(message: str, blocks: list = None):
    """Send a message to Slack via webhook."""
    if not SLACK_WEBHOOK_URL:
        print("Slack webhook not configured, skipping notification")
        return False

    try:
        payload = {"text": message}
        if blocks:
            payload["blocks"] = blocks

        response = requests.post(
            SLACK_WEBHOOK_URL,
            json=payload,
            timeout=10
        )
        if response.status_code == 200:
            print("Slack notification sent successfully")
            return True
        else:
            print(f"Slack notification failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error sending Slack notification: {e}")
        return False


def format_availability_message(target_date: str, target_day: str, results: dict):
    """Format a Slack message with availability details for a single day."""
    # Build the message blocks for rich formatting
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🏓 Pickleball Court Availability - {target_day}, {target_date}",
                "emoji": True
            }
        },
        {
            "type": "divider"
        }
    ]

    # Add results for each court
    for court, status in results.items():
        if status.get("booked"):
            emoji = "✅"
            text = f"*{court}*: BOOKED at {status.get('time', 'N/A')}"
        elif status.get("available_times"):
            emoji = "🟢"
            times = ", ".join(status["available_times"][:5])  # Limit to 5 times
            text = f"*{court}*: Available - {times}"
        else:
            emoji = "🔴"
            text = f"*{court}*: No 7-9 PM slots available"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{emoji} {text}"
            }
        })

    # Add footer with timestamp
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"Checked at {datetime.now(MANILA_TZ).strftime('%Y-%m-%d %H:%M:%S')} Manila Time"
            }
        ]
    })

    # Create plain text fallback
    plain_text = f"Pickleball Availability for {target_day}, {target_date}\n"
    for court, status in results.items():
        if status.get("booked"):
            plain_text += f"✅ {court}: BOOKED at {status.get('time', 'N/A')}\n"
        elif status.get("available_times"):
            plain_text += f"🟢 {court}: Available - {', '.join(status['available_times'][:5])}\n"
        else:
            plain_text += f"🔴 {court}: No 7-9 PM slots\n"

    return plain_text, blocks


def format_multi_day_availability(all_days_results: dict, include_buttons: bool = True):
    """Format a Slack message with availability for multiple days, with inline booking buttons."""

    # Format target time for display
    if TARGET_START_HOUR < 12:
        target_display = f"{TARGET_START_HOUR}:00 AM"
    elif TARGET_START_HOUR == 12:
        target_display = "12:00 PM"
    else:
        target_display = f"{TARGET_START_HOUR - 12}:00 PM"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🏓 Pickleball Court Availability",
                "emoji": True
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"📅 Target: *{target_display}* | Tap a button to book"
                }
            ]
        }
    ]

    plain_text = "🏓 Pickleball Court Availability\n\n"

    def make_button(court, time_slot, date_str, day_name):
        """Helper to create a booking button."""
        value = f"{date_str}|{court}|{time_slot}"
        court_abbrev = court.replace('Wood ', 'W')
        button_text = f"{court_abbrev} {time_slot}"
        return {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": button_text[:24],
                "emoji": True
            },
            "value": value,
            "action_id": f"book_slot_{value.replace('|', '_').replace(' ', '_').replace(':', '')}"
        }

    for date_info, day_results in all_days_results.items():
        date_str, day_name = date_info

        # Collect target time slots and alternative slots
        target_slots = []  # Courts with target time available
        other_slots = []   # Other available time slots

        for court, status in day_results.items():
            available_slots = status.get("available", [])

            if status.get("has_target"):
                target_slots.append({
                    "court": court,
                    "time": target_display,
                    "date": date_str,
                    "day": day_name
                })

            # Collect alternative slots (not target time)
            for slot in available_slots:
                if slot != target_display:
                    other_slots.append({
                        "court": court,
                        "time": slot,
                        "date": date_str,
                        "day": day_name
                    })

        # Determine status emoji
        if target_slots:
            emoji = "✅"
        elif other_slots:
            emoji = "🟡"
        else:
            emoji = "🔴"

        # Add divider before each day
        blocks.append({"type": "divider"})

        # Line 1: Date header
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{emoji} *{day_name}, {date_str}*"
            }
        })

        plain_text += f"{emoji} {day_name}, {date_str}\n"

        # Line 2: Target time buttons (if any available)
        if target_slots and include_buttons:
            target_buttons = [make_button(s['court'], s['time'], s['date'], s['day']) for s in target_slots[:5]]
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"*{target_display}:*"}]
            })
            blocks.append({
                "type": "actions",
                "elements": target_buttons
            })
        elif not target_slots and not other_slots:
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": "_No slots available_"}]
            })

        # Line 3: Alternative time buttons (if any)
        if other_slots and include_buttons:
            alt_buttons = [make_button(s['court'], s['time'], s['date'], s['day']) for s in other_slots[:5]]
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": "*Other times:*"}]
            })
            blocks.append({
                "type": "actions",
                "elements": alt_buttons
            })

    # Add footer
    blocks.append({
        "type": "divider"
    })
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"Checked at {datetime.now(MANILA_TZ).strftime('%Y-%m-%d %H:%M:%S')} Manila Time"
            }
        ]
    })

    return plain_text, blocks


async def save_session(page, context):
    """Save browser session for reuse."""
    SESSION_DIR.mkdir(exist_ok=True)
    storage = await context.storage_state(path=str(SESSION_DIR / "auth.json"))
    print(f"Session saved to {SESSION_DIR / 'auth.json'}")
    return storage


async def manual_login_setup():
    """
    Run this once to log in and save the session.
    Usage: python sniper.py --setup
    """
    print("=" * 60)
    print("LOGIN SETUP")
    print("=" * 60)
    print("\nAttempting to log in with credentials from .env file...")
    print(f"Email: {os.environ.get('SKEDDA_EMAIL', 'NOT SET')}")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()

        # Step 1: Go to booking page
        print("\n[1/5] Loading booking page...")
        await page.goto(URL_BOOKING)
        await page.wait_for_load_state('networkidle')
        await page.screenshot(path="setup_01_initial.png")

        # Step 2: Click LOG IN
        print("[2/5] Clicking LOG IN...")
        try:
            login_btn = await page.wait_for_selector('text="LOG IN"', timeout=5000)
            await login_btn.click()
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)
            await page.screenshot(path="setup_02_after_login_click.png")
        except Exception as e:
            print(f"Could not find LOG IN button: {e}")

        # Step 3: Look for "Go to the login page" link (if on reset page)
        print("[3/5] Looking for email/password login option...")
        try:
            go_to_login = await page.wait_for_selector('text="Go to the login page"', timeout=3000)
            print("  Found 'Go to the login page' - clicking...")
            await go_to_login.click()
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)
            await page.screenshot(path="setup_03_login_page.png")
        except:
            print("  Not on reset page, continuing...")

        # Step 4: Fill in email and password
        print("[4/5] Entering credentials...")
        current_url = page.url
        print(f"  Current URL: {current_url}")
        await page.screenshot(path="setup_04_before_credentials.png")

        # Try to find and fill email field
        email_filled = False
        email_selectors = [
            'input[type="email"]',
            'input[name="email"]',
            'input[placeholder*="email" i]',
            'input[id*="email" i]',
            '#email'
        ]
        for selector in email_selectors:
            try:
                email_input = await page.wait_for_selector(selector, timeout=2000)
                if email_input:
                    await email_input.fill(os.environ["SKEDDA_EMAIL"])
                    print(f"  Entered email using: {selector}")
                    email_filled = True
                    break
            except:
                continue

        if not email_filled:
            print("  Could not find email field automatically.")
            print("  Please enter your credentials manually in the browser.")
            print("  You have 3 minutes to complete login...")

            # Wait for manual login
            for i in range(36):  # 36 * 5 = 180 seconds (3 minutes)
                await asyncio.sleep(5)
                remaining = 180 - (i + 1) * 5

                # Check if logged in
                if "zonemakati.skedda.com" in page.url:
                    page_content = await page.content()
                    if "LOG IN" not in page_content and "VISITOR MODE" not in page_content:
                        print("\n  Login detected!")
                        break
                print(f"  {remaining}s remaining...")
        else:
            # Try to find and fill password field
            password_selectors = [
                'input[type="password"]',
                'input[name="password"]',
                '#password'
            ]
            for selector in password_selectors:
                try:
                    password_input = await page.wait_for_selector(selector, timeout=2000)
                    if password_input:
                        await password_input.fill(os.environ["SKEDDA_PASSWORD"])
                        print(f"  Entered password using: {selector}")
                        break
                except:
                    continue

            await page.screenshot(path="setup_05_credentials_filled.png")

            # Try to submit
            print("[5/5] Submitting login...")
            submit_selectors = [
                'button[type="submit"]',
                'button:has-text("Log in")',
                'button:has-text("Login")',
                'button:has-text("Sign in")',
                'input[type="submit"]'
            ]
            for selector in submit_selectors:
                try:
                    submit_btn = await page.wait_for_selector(selector, timeout=2000)
                    if submit_btn:
                        await submit_btn.click()
                        print(f"  Clicked submit using: {selector}")
                        break
                except:
                    continue

            # Wait for login to complete
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)

        # Verify login
        await page.goto(URL_BOOKING)
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(2)
        await page.screenshot(path="setup_final.png")

        print(f"\nFinal URL: {page.url}")

        page_content = await page.content()
        if "VISITOR MODE" in page_content or "LOG IN" in page_content:
            print("\n" + "!" * 60)
            print("Login did not complete automatically.")
            print("The browser will stay open for 3 more minutes.")
            print("Please complete the login manually, then wait.")
            print("!" * 60)

            # Give user more time
            for i in range(36):  # 3 more minutes
                await asyncio.sleep(5)
                remaining = 180 - (i + 1) * 5

                if "zonemakati.skedda.com" in page.url:
                    page_content = await page.content()
                    if "LOG IN" not in page_content and "VISITOR MODE" not in page_content:
                        print("\nLogin detected!")
                        break
                print(f"  {remaining}s remaining...")

            # Final check
            await page.goto(URL_BOOKING)
            await page.wait_for_load_state('networkidle')
            page_content = await page.content()

        if "VISITOR MODE" not in page_content and "LOG IN" not in page_content:
            print("\n" + "=" * 60)
            print("LOGIN SUCCESSFUL!")
            print("=" * 60)
            await save_session(page, context)
            print("\nSetup complete! You can now run: python3 sniper.py")
        else:
            print("\nLogin failed. Please try again.")
            await page.screenshot(path="setup_failed.png")

        await browser.close()


async def run():
    """Main sniper bot function."""
    async with async_playwright() as p:
        # Check if we have a saved session
        session_file = SESSION_DIR / "auth.json"

        if session_file.exists():
            print("Loading saved session...")
            browser = await p.chromium.launch(headless=HEADLESS_MODE)
            context = await browser.new_context(
                storage_state=str(session_file),
                viewport={'width': 1280, 'height': 800}
            )
        else:
            print("No saved session found. Running without authentication.")
            print("TIP: Run 'python sniper.py --setup' to save your login session.")
            browser = await p.chromium.launch(headless=HEADLESS_MODE)
            context = await browser.new_context(viewport={'width': 1280, 'height': 800})

        page = await context.new_page()

        print("\n" + "=" * 60)
        print("PICKLEBALL SNIPER BOT")
        print("=" * 60)
        print(f"Target Courts: {TARGET_COURT_KEYWORDS}")
        print(f"Target Time: {TARGET_START_HOUR}:00")
        print(f"Headless Mode: {HEADLESS_MODE}")
        print(f"Wait for Midnight: {ENABLE_WAIT_FOR_MIDNIGHT}")
        print("=" * 60)

        # 1. NAVIGATE TO BOOKING PAGE
        print("\n[STEP 1] Navigating to booking page...")
        await page.goto(URL_BOOKING)
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(1)

        await page.screenshot(path="01_booking_page.png")
        print(f"Page loaded. URL: {page.url}")

        # Check if we're logged in
        # Logged in = "USER MODE" appears, or "Profile" button exists
        # Not logged in = "VISITOR MODE" appears, or "LOG IN" button exists
        page_content = await page.content()

        is_logged_in = "USER MODE" in page_content or "Profile" in page_content
        is_visitor = "VISITOR MODE" in page_content or ">LOG IN<" in page_content

        if is_visitor and not is_logged_in:
            print("\n" + "!" * 60)
            print("WARNING: Not logged in!")
            print("Please run this command in your terminal:")
            print("  python3 sniper.py --setup")
            print("!" * 60)
            await page.screenshot(path="not_logged_in.png")
            await context.close()
            return
        else:
            print("Login session valid. Logged in as user.")

        # 2. CALCULATE TARGET DATE
        print("\n[STEP 2] Calculating target date...")
        now_manila = datetime.now(MANILA_TZ)
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        # The site only allows booking up to DAYS_AHEAD_LIMIT days in advance
        # So we target exactly that many days ahead (the furthest bookable date)
        target_date_obj = now_manila + timedelta(days=DAYS_AHEAD_LIMIT)
        target_date_str = target_date_obj.strftime("%Y-%m-%d")
        target_day_name = day_names[target_date_obj.weekday()]

        print(f"Current Manila Time: {now_manila.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Booking Window: {DAYS_AHEAD_LIMIT} days ahead")
        print(f"Targeting Date: {target_date_str} ({target_day_name})")
        print(f"Target Time: {TARGET_START_HOUR}:00 - {TARGET_END_HOUR}:00 (7-9 PM)")

        # Warn if the target day doesn't match expected day of week
        if target_date_obj.weekday() != TARGET_DAY_OF_WEEK:
            expected_day = day_names[TARGET_DAY_OF_WEEK]
            print(f"\n⚠️  NOTE: Target date is {target_day_name}, not {expected_day}")
            print(f"    To book {expected_day}, run the script on a different night.")
            print(f"    See schedule mapping in configuration comments.")

        # 3. WAIT FOR MIDNIGHT (Production Mode)
        if ENABLE_WAIT_FOR_MIDNIGHT:
            print("\n[STEP 3] Waiting for booking window to open...")

            # Target: 23:59:59.5 Manila time
            target_wait_time = now_manila.replace(
                hour=23, minute=59, second=59, microsecond=500000
            )

            while True:
                current_time = datetime.now(MANILA_TZ)

                if current_time >= target_wait_time:
                    print(f"GO TIME! Current: {current_time.strftime('%H:%M:%S.%f')}")
                    break

                # Log every 30 seconds
                if current_time.second % 30 == 0 and current_time.microsecond < 100000:
                    remaining = (target_wait_time - current_time).total_seconds()
                    print(f"Waiting... {remaining:.1f}s remaining ({current_time.strftime('%H:%M:%S')})")

                await asyncio.sleep(0.1)
        else:
            print("\n[STEP 3] Skipping wait (test mode)...")

        # 4. NAVIGATE TO TARGET DATE (Day View)
        print("\n[STEP 4] Loading target date...")

        # Navigate to booking page
        await page.goto(URL_BOOKING)
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(1)

        # Switch to Day view (more reliable for booking)
        try:
            day_tab = page.locator('button:has-text("Day"), [role="tab"]:has-text("Day")').first
            await day_tab.click(timeout=3000)
        except:
            await page.mouse.click(100, 38)  # Fallback coordinate click
        await asyncio.sleep(1)
        print("Switched to Day view")

        # Navigate forward using the arrow buttons to reach the target date
        # This is more reliable than URL parameters when the site has date restrictions
        print(f"Navigating {DAYS_AHEAD_LIMIT} days forward using date controls...")

        for day in range(DAYS_AHEAD_LIMIT):
            try:
                # Click the ">" next button to go to next day
                next_btn = page.locator('button:has-text("›")').first
                await next_btn.click(timeout=2000)
            except:
                # Fallback: coordinate click on the ">" arrow (around x=443, y=38)
                await page.mouse.click(443, 38)
            await asyncio.sleep(0.5)
            print(f"  Advanced to day {day + 1}")

        await asyncio.sleep(1)

        # Verify the date shown matches our target
        page_content = await page.content()
        target_date_display = target_date_obj.strftime("%B %d").upper()  # e.g., "FEBRUARY 04"
        target_day_upper = target_day_name.upper()

        if target_day_upper in page_content.upper() or target_date_display in page_content.upper():
            print(f"Confirmed: Page showing target date ({target_date_str} - {target_day_name})")
        else:
            print(f"Warning: Page may not be showing target date. Check screenshot.")

        await page.screenshot(path="02_day_view.png")
        print(f"Day view loaded. Screenshot saved to 02_day_view.png")

        # 5. ATTEMPT TO BOOK SLOT (Day View approach)
        print("\n[STEP 5] Attempting to book...")

        booked_successfully = False
        booked_court = None
        booked_time = None

        # Track results for each court (for Slack notification)
        court_results = {}

        # Build time label for display
        if TARGET_START_HOUR < 12:
            start_hour_12 = TARGET_START_HOUR
            start_period = "AM"
        else:
            start_hour_12 = TARGET_START_HOUR - 12 if TARGET_START_HOUR > 12 else 12
            start_period = "PM"

        target_time_label = f"{start_hour_12}:00 {start_period}"
        print(f"Looking for time slot: {target_time_label}")

        # Use JavaScript to find clickable positions for each court at the target time
        # Simply find column centers and time row position - let clicking determine availability
        click_positions = await page.evaluate('''(targetHour) => {
            const positions = {};

            // Find column headers (Wood 1-6 Pickleball)
            const courtColumns = {};
            document.querySelectorAll('*').forEach(el => {
                const text = (el.innerText || '').trim();
                if (text.length < 25 && text.includes('Pickleball')) {
                    for (let i = 1; i <= 6; i++) {
                        if (text.includes('Wood ' + i) && !courtColumns['Wood ' + i]) {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 50) {
                                courtColumns['Wood ' + i] = {
                                    x: rect.x,
                                    width: rect.width,
                                    centerX: rect.x + rect.width / 2
                                };
                            }
                        }
                    }
                }
            });

            // Find the time row for target hour
            let targetRowY = null;
            let nextRowY = null;
            document.querySelectorAll('*').forEach(el => {
                const text = (el.innerText || '').trim();
                const match = text.match(/^(1?[0-9]):00\\s*(AM|PM)$/i);
                if (match) {
                    const rect = el.getBoundingClientRect();
                    if (rect.x < 150 && rect.width < 100 && rect.height > 10 && rect.height < 50) {
                        let hour = parseInt(match[1]);
                        const period = match[2].toUpperCase();
                        if (period === 'PM' && hour !== 12) hour += 12;
                        if (period === 'AM' && hour === 12) hour = 0;

                        if (hour === targetHour) {
                            // Click in the middle of this row
                            targetRowY = rect.y + 25;
                        }
                        if (hour === targetHour + 1) {
                            nextRowY = rect.y;
                        }
                    }
                }
            });

            // If we found both rows, click in the middle
            if (targetRowY && nextRowY) {
                targetRowY = (targetRowY + nextRowY) / 2;
            }

            // Calculate click positions for each court (no availability check - just click and try)
            for (let i = 1; i <= 6; i++) {
                const courtName = 'Wood ' + i;
                const court = courtColumns[courtName];

                if (court && targetRowY) {
                    positions[courtName] = {
                        x: court.centerX,
                        y: targetRowY
                    };
                }
            }

            positions['_debug'] = {
                columns: Object.keys(courtColumns),
                targetRowY: targetRowY
            };

            return positions;
        }''', TARGET_START_HOUR)

        debug_info = click_positions.get('_debug', {})
        print(f"  Found columns: {debug_info.get('columns', [])}")
        print(f"  Target row Y: {debug_info.get('targetRowY', 'not found')}")

        # Try each court in priority order - click and try to book
        for court_name in TARGET_COURT_KEYWORDS:
            court_results[court_name] = {"available_times": [], "booked": False}
            if booked_successfully:
                break

            pos = click_positions.get(court_name, {})
            if not pos.get('x') or not pos.get('y'):
                print(f"\n{court_name}: Could not find position")
                continue

            print(f"\n{court_name}: Trying to book at ({pos['x']:.0f}, {pos['y']:.0f})")

            # Click on the slot
            print(f"  Clicking on {court_name} at {target_time_label}...")
            await page.mouse.click(pos['x'], pos['y'])
            await asyncio.sleep(1.5)

            await page.screenshot(path=f"03_clicked_{court_name.replace(' ', '_')}.png")

            # Check if a booking modal appeared - look for Book button in the header bar
            try:
                # The booking modal shows a Book button in the header
                book_btn = await page.wait_for_selector('button:has-text("Book")', timeout=2000)
                if book_btn:
                    btn_text = await book_btn.inner_text()
                    # Make sure it's the actual Book button (not "Booked" or other)
                    if btn_text.strip() == "Book":
                        print(f"  ✅ Slot is available! Found 'Book' button")

                        # Get the time from the modal header if possible
                        try:
                            header_text = await page.inner_text('[class*="header"], [class*="modal"]')
                            print(f"  Modal shows: {header_text[:100] if len(header_text) > 100 else header_text}")
                        except:
                            pass

                        # Click the Book button (opens confirmation form)
                        await book_btn.click()
                        await asyncio.sleep(1.5)

                        await page.screenshot(path=f"04_confirm_form_{court_name.replace(' ', '_')}.png")

                        # Now look for "Confirm booking" button to complete the booking
                        try:
                            confirm_btn = await page.wait_for_selector('button:has-text("Confirm booking")', timeout=3000)
                            if confirm_btn:
                                print(f"  Found 'Confirm booking' button - clicking...")
                                await confirm_btn.click()
                                await asyncio.sleep(2)

                                await page.screenshot(path=f"05_after_confirm_{court_name.replace(' ', '_')}.png")
                                print(f"  ✅ BOOKING CONFIRMED for {court_name}!")
                            else:
                                print(f"  Could not find Confirm booking button")
                        except Exception as confirm_err:
                            print(f"  No confirm button found (may already be booked): {confirm_err}")

                        booked_successfully = True
                        booked_court = court_name
                        booked_time = target_time_label
                        court_results[court_name]["booked"] = True
                        court_results[court_name]["time"] = target_time_label
                        break
                    else:
                        print(f"  Found button '{btn_text}' but not a booking button")
            except Exception as e:
                # No Book button found - slot might be booked or click missed
                page_content = await page.content()
                if "already" in page_content.lower() or "scheduled" in page_content.lower():
                    print(f"  ❌ Slot is already booked for {court_name}")
                else:
                    print(f"  No booking modal appeared - slot may be booked (error: {e})")

            # Close any modal before trying next court
            await page.keyboard.press('Escape')
            await asyncio.sleep(0.5)

        await page.screenshot(path="04_after_booking_attempt.png")

        # 6. REPORT RESULTS
        print("\n" + "=" * 60)
        if booked_successfully:
            print("SUCCESS! Booking submitted. Check your email for confirmation.")
            print(f"  Court: {booked_court}")
            print(f"  Time: {booked_time}")
        else:
            print("BOOKING NOT COMPLETED")
            print("Please check the screenshots and try manually:")
            print(f"  URL: {URL_BOOKING}?date={target_date_str}")
        print("=" * 60)

        # Print availability summary
        print("\n📋 Availability Summary:")
        for court, status in court_results.items():
            if status.get("booked"):
                print(f"  ✅ {court}: BOOKED at {status.get('time')}")
            elif status.get("available_times"):
                print(f"  🟢 {court}: Available times - {', '.join(status['available_times'][:5])}")
            else:
                print(f"  🔴 {court}: No {target_time_label} slots available")

        # 7. SEND SLACK NOTIFICATION
        print("\n[STEP 7] Sending Slack notification...")
        slack_message, slack_blocks = format_availability_message(
            target_date_str,
            target_day_name,
            court_results
        )

        if booked_successfully:
            # Add booking success to the message
            success_msg = f"🎉 *BOOKING CONFIRMED!*\n*Court:* {booked_court}\n*Time:* {booked_time}\n*Date:* {target_day_name}, {target_date_str}"
            slack_blocks.insert(1, {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": success_msg
                }
            })
            slack_message = f"🎉 BOOKING CONFIRMED! {booked_court} at {booked_time} on {target_day_name}, {target_date_str}\n\n{slack_message}"

        send_slack_message(slack_message, slack_blocks)

        await page.screenshot(path="final_state.png")
        await context.close()


async def book_slot_direct(target_date: str, target_court: str, target_time: str):
    """
    Book a specific slot directly. Used by Slack interactive callbacks.

    Args:
        target_date: Date string like "2026-02-02"
        target_court: Court name like "Wood 3"
        target_time: Time string like "6:00 AM" or "7:00 PM"

    Returns:
        Tuple of (success: bool, message: str)
    """
    from pathlib import Path
    from datetime import datetime

    session_file = SESSION_DIR / "auth.json"
    if not session_file.exists():
        return False, "No saved session. Run 'python sniper.py --setup' first."

    # Parse the target time to get the hour
    time_clean = target_time.replace(" ", "").upper()
    try:
        hour = int(time_clean.split(":")[0])
        if "PM" in time_clean and hour != 12:
            hour += 12
        elif "AM" in time_clean and hour == 12:
            hour = 0
    except:
        return False, f"Could not parse time: {target_time}"

    # Calculate days from today to target date
    try:
        target_date_obj = datetime.strptime(target_date, "%Y-%m-%d")
        now = datetime.now(MANILA_TZ)
        days_ahead = (target_date_obj.date() - now.date()).days
        if days_ahead < 0:
            return False, f"Date {target_date} is in the past"
        if days_ahead > 4:
            return False, f"Date {target_date} is more than 4 days ahead (booking limit)"
    except:
        return False, f"Could not parse date: {target_date}"

    print(f"\n[Direct Booking] {target_court} at {target_time} on {target_date}")
    print(f"  Days ahead: {days_ahead}, Hour: {hour}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # Headless for server use
        context = await browser.new_context(
            storage_state=str(session_file),
            viewport={'width': 1400, 'height': 900}
        )
        page = await context.new_page()

        try:
            # Navigate to booking page
            await page.goto(URL_BOOKING)
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(1)

            # Switch to Day view
            try:
                day_tab = page.locator('button:has-text("Day")').first
                await day_tab.click(timeout=3000)
            except:
                await page.mouse.click(100, 38)
            await asyncio.sleep(1)

            # Navigate to target date
            for _ in range(days_ahead):
                try:
                    next_btn = page.locator('button:has-text("›")').first
                    await next_btn.click(timeout=2000)
                except:
                    await page.mouse.click(443, 38)
                await asyncio.sleep(0.5)

            await asyncio.sleep(1)

            # Find click position for the specific court and time
            court_num = target_court.split()[-1]  # Get "3" from "Wood 3"

            click_pos = await page.evaluate('''(params) => {
                const { courtNum, targetHour } = params;

                // Find the court column
                let courtCenterX = null;
                document.querySelectorAll('*').forEach(el => {
                    const text = (el.innerText || '').trim();
                    if (text.length < 25 && text.includes('Wood ' + courtNum) && text.includes('Pickleball')) {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 50) {
                            courtCenterX = rect.x + rect.width / 2;
                        }
                    }
                });

                // Find the time row
                let targetRowY = null;
                document.querySelectorAll('*').forEach(el => {
                    const text = (el.innerText || '').trim();
                    const match = text.match(/^(1?[0-9]):00\\s*(AM|PM)$/i);
                    if (match) {
                        const rect = el.getBoundingClientRect();
                        if (rect.x < 150 && rect.width < 100) {
                            let hour = parseInt(match[1]);
                            const period = match[2].toUpperCase();
                            if (period === 'PM' && hour !== 12) hour += 12;
                            if (period === 'AM' && hour === 12) hour = 0;

                            if (hour === targetHour) {
                                targetRowY = rect.y + 25;
                            }
                        }
                    }
                });

                return { x: courtCenterX, y: targetRowY };
            }''', {"courtNum": court_num, "targetHour": hour})

            if not click_pos.get('x') or not click_pos.get('y'):
                await context.close()
                return False, f"Could not find position for {target_court} at {target_time}"

            # Click on the slot
            await page.mouse.click(click_pos['x'], click_pos['y'])
            await asyncio.sleep(1.5)

            # Look for Book button
            try:
                book_btn = await page.wait_for_selector('button:has-text("Book")', timeout=3000)
                if book_btn:
                    btn_text = await book_btn.inner_text()
                    if btn_text.strip() == "Book":
                        await book_btn.click()
                        await asyncio.sleep(1.5)

                        # Click Confirm booking
                        try:
                            confirm_btn = await page.wait_for_selector('button:has-text("Confirm booking")', timeout=3000)
                            if confirm_btn:
                                await confirm_btn.click()
                                await asyncio.sleep(2)

                                await page.screenshot(path=f"direct_booking_{target_court.replace(' ', '_')}.png")
                                await context.close()
                                return True, f"Successfully booked {target_court} at {target_time} on {target_date}"
                        except:
                            pass
            except:
                pass

            await context.close()
            return False, f"Slot {target_court} at {target_time} may already be booked"

        except Exception as e:
            await context.close()
            return False, f"Booking error: {str(e)}"


async def check_availability():
    """
    Check court availability for the next 4 days using Day view.

    Workflow:
    1. Navigate to booking page with target date in URL
    2. Switch to Day view
    3. Parse the schedule grid to find bookings
    4. Report findings to Slack
    """
    import re

    def time_to_hour(time_str):
        """Convert time string like '7:00PM' to 24-hour format (19)"""
        clean = time_str.replace(" ", "").upper()
        try:
            hour = int(clean.split(":")[0])
            if "PM" in clean and hour != 12:
                hour += 12
            elif "AM" in clean and hour == 12:
                hour = 0
            return hour
        except:
            return -1

    def covers_7pm(start_time, end_time):
        """Check if a booking time range covers 7PM (19:00)"""
        start_hour = time_to_hour(start_time)
        end_hour = time_to_hour(end_time)
        if start_hour < 0 or end_hour < 0:
            return False
        if end_hour <= start_hour:
            end_hour += 24
        return start_hour <= 19 < end_hour

    async with async_playwright() as p:
        # Load saved session
        session_file = SESSION_DIR / "auth.json"
        if not session_file.exists():
            print("No saved session. Run 'python sniper.py --setup' first.")
            return

        print("Loading session...")
        browser = await p.chromium.launch(headless=HEADLESS_MODE)
        context = await browser.new_context(
            storage_state=str(session_file),
            viewport={'width': 1400, 'height': 900}
        )
        page = await context.new_page()

        print("\n" + "=" * 60)
        print("PICKLEBALL AVAILABILITY CHECKER")
        print("=" * 60)
        # Format target time for display
        if TARGET_START_HOUR < 12:
            target_display = f"{TARGET_START_HOUR}:00 AM"
        elif TARGET_START_HOUR == 12:
            target_display = "12:00 PM"
        else:
            target_display = f"{TARGET_START_HOUR - 12}:00 PM"

        print(f"Courts: {', '.join(TARGET_COURT_KEYWORDS)}")
        print(f"Target Time: {target_display}")
        print(f"Days: Today + next {DAYS_AHEAD_LIMIT} days")
        print("=" * 60)

        now_manila = datetime.now(MANILA_TZ)
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        all_results = {}

        # Navigate to booking page once and switch to Day view
        print("\nLoading booking page...")
        await page.goto(URL_BOOKING)
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(1)

        # Switch to Day view first
        try:
            day_tab = page.locator('button:has-text("Day"), [role="tab"]:has-text("Day")').first
            await day_tab.click(timeout=3000)
        except:
            await page.mouse.click(100, 38)
        await asyncio.sleep(1)
        print("Switched to Day view")

        for days_ahead in range(DAYS_AHEAD_LIMIT + 1):
            target_date = now_manila + timedelta(days=days_ahead)
            date_str = target_date.strftime("%Y-%m-%d")
            day_name = day_names[target_date.weekday()]

            print(f"\n[Day {days_ahead}] {day_name}, {date_str}")

            # For days after today, click the next arrow to advance
            if days_ahead > 0:
                try:
                    # Click the ">" next button to go to next day
                    next_btn = page.locator('button:has-text("›")').first
                    await next_btn.click(timeout=2000)
                except:
                    # Fallback: coordinate click on the ">" arrow (around x=443, y=38)
                    await page.mouse.click(443, 38)
                await asyncio.sleep(1)

            print(f"  Viewing {day_name} in Day view")

            # Take screenshot for debugging
            await page.screenshot(path=f"day_{days_ahead}_{date_str}.png")

            # Initialize results for this day - all 6 Wood courts
            day_results = {}
            for court in TARGET_COURT_KEYWORDS:
                day_results[court] = {"available": [], "booked": []}

            # Use JavaScript to detect availability for multiple time slots
            # Check from ALT_START_HOUR onwards for alternatives
            booking_data = await page.evaluate('''(params) => {
                const { targetHour, altStartHour } = params;
                const results = {};

                // Find column headers (Wood 1-6 Pickleball)
                const courtColumns = {};
                document.querySelectorAll('*').forEach(el => {
                    const text = (el.innerText || '').trim();
                    if (text.length < 25 && text.includes('Pickleball')) {
                        for (let i = 1; i <= 6; i++) {
                            if (text.includes('Wood ' + i) && !courtColumns['Wood ' + i]) {
                                const rect = el.getBoundingClientRect();
                                if (rect.width > 50) {
                                    courtColumns['Wood ' + i] = {
                                        x: rect.x,
                                        width: rect.width,
                                        centerX: rect.x + rect.width / 2
                                    };
                                }
                            }
                        }
                    }
                });

                // Find the time labels on the left to get Y positions for each hour
                const timeRows = {};
                document.querySelectorAll('*').forEach(el => {
                    const text = (el.innerText || '').trim();
                    // Match time labels like "7:00PM", "7:00 PM"
                    const match = text.match(/^(1?[0-9]):00\\s*(AM|PM)$/i);
                    if (match) {
                        const rect = el.getBoundingClientRect();
                        if (rect.x < 150 && rect.width < 100 && rect.height > 10 && rect.height < 50) {
                            let hour = parseInt(match[1]);
                            const period = match[2].toUpperCase();
                            if (period === 'PM' && hour !== 12) hour += 12;
                            if (period === 'AM' && hour === 12) hour = 0;
                            if (!timeRows[hour]) {
                                timeRows[hour] = { y: rect.y, height: rect.height };
                            }
                        }
                    }
                });

                // Find all booking blocks
                const bookingBlocks = [];
                document.querySelectorAll('*').forEach(el => {
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    const bgColor = style.backgroundColor;
                    const text = (el.innerText || '').trim();

                    const isColoredBg = bgColor &&
                        bgColor !== 'rgba(0, 0, 0, 0)' &&
                        bgColor !== 'transparent' &&
                        bgColor !== 'rgb(255, 255, 255)';

                    const hasBookingText = text.length > 3 &&
                        (text.includes('PM') || text.includes('AM') ||
                         text.includes('Pickleball') || text.includes('booking') ||
                         text.includes('Reclub') || text.includes('Open Play') ||
                         text.includes('player') || text.includes('User'));

                    if (rect.x > 100 && rect.width > 50 && rect.height > 30 &&
                        (isColoredBg || hasBookingText)) {
                        const isDupe = bookingBlocks.some(b =>
                            Math.abs(b.x - rect.x) < 20 &&
                            Math.abs(b.y - rect.y) < 20 &&
                            Math.abs(b.height - rect.height) < 10
                        );
                        if (!isDupe && text.length < 200) {
                            bookingBlocks.push({
                                x: rect.x,
                                y: rect.y,
                                width: rect.width,
                                height: rect.height,
                                centerX: rect.x + rect.width / 2,
                                bottom: rect.y + rect.height,
                                text: text.substring(0, 100)
                            });
                        }
                    }
                });

                // Check availability for each court at multiple time slots
                // Check from altStartHour to closing time (11 PM)
                const checkHours = [];
                for (let h = altStartHour; h <= 23; h++) {
                    checkHours.push(h);
                }

                for (let i = 1; i <= 6; i++) {
                    const courtName = 'Wood ' + i;
                    results[courtName] = {
                        slots: {},
                        availableSlots: [],
                        bookedSlots: []
                    };

                    const court = courtColumns[courtName];
                    if (!court) continue;

                    checkHours.forEach(hour => {
                        const timeRow = timeRows[hour];
                        if (!timeRow) return;

                        let isBooked = false;
                        let bookingText = '';

                        // Check if any booking block overlaps this time slot
                        bookingBlocks.forEach(block => {
                            const xOverlap = Math.abs(block.centerX - court.centerX) < court.width * 0.7;
                            const yOverlap = block.y <= timeRow.y + 20 && block.bottom > timeRow.y;

                            if (xOverlap && yOverlap) {
                                isBooked = true;
                                bookingText = block.text;
                            }
                        });

                        const hourLabel = hour > 12 ? (hour - 12) + ':00 PM' : hour + ':00 AM';
                        results[courtName].slots[hour] = { booked: isBooked, text: bookingText };

                        if (isBooked) {
                            results[courtName].bookedSlots.push(hourLabel);
                        } else {
                            results[courtName].availableSlots.push(hourLabel);
                        }
                    });

                    // Check primary slot (target hour)
                    results[courtName].isTargetBooked = results[courtName].slots[targetHour]?.booked || false;
                }

                // Debug info
                results['_columns'] = Object.keys(courtColumns);
                results['_timeRows'] = Object.keys(timeRows).map(h => parseInt(h));
                results['_bookingBlockCount'] = bookingBlocks.length;

                return results;
            }''', {"targetHour": TARGET_START_HOUR, "altStartHour": ALT_START_HOUR})

            found_columns = booking_data.get('_columns', [])
            time_rows = booking_data.get('_timeRows', [])
            block_count = booking_data.get('_bookingBlockCount', 0)
            print(f"  Columns: {found_columns}, Time rows: {time_rows}, Blocks: {block_count}")

            # Check each court for availability
            has_target_available = False
            alternatives = []

            for court in TARGET_COURT_KEYWORDS:
                court_data = booking_data.get(court, {})
                is_target_booked = court_data.get('isTargetBooked', False)
                available_slots = court_data.get('availableSlots', [])
                booked_slots = court_data.get('bookedSlots', [])

                day_results[court]["available"] = available_slots
                day_results[court]["booked"] = booked_slots

                if is_target_booked:
                    print(f"    {court}: {target_display} BOOKED")
                    # Show alternatives for this court
                    if available_slots:
                        alt_str = ", ".join(available_slots)
                        print(f"      Alternatives: {alt_str}")
                        for slot in available_slots:
                            alternatives.append({"court": court, "time": slot, "date": date_str, "day": day_name})
                else:
                    has_target_available = True
                    day_results[court]["has_target"] = True
                    print(f"    {court}: {target_display} AVAILABLE ✓")

            # Summary for this day
            if has_target_available:
                print(f"  ✅ {target_display} slots available!")
            else:
                print(f"  ❌ No {target_display} slots - {len(alternatives)} alternative slots found")

            all_results[(date_str, day_name)] = day_results

        # Send Slack notification
        print("\n[Sending Slack notification...]")
        message, blocks = format_multi_day_availability(all_results)
        send_slack_message(message, blocks)

        print("\n" + "=" * 60)
        print("CHECK COMPLETE")
        print("=" * 60)

        await context.close()


async def check_all_days():
    """Alias for check_availability for backward compatibility."""
    await check_availability()


async def main():
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "--setup":
            await manual_login_setup()
        elif sys.argv[1] == "--check":
            await check_all_days()
        else:
            print("Usage:")
            print("  python sniper.py          # Run the booking bot")
            print("  python sniper.py --setup  # Set up login session")
            print("  python sniper.py --check  # Check availability for all days")
    else:
        await run()


if __name__ == "__main__":
    asyncio.run(main())
