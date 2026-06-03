# Connecting Jarvis to Gmail and Google Calendar

This guide walks you through connecting Jarvis to your real Gmail inbox and Google Calendar using OAuth 2.0. Both services work with **free @gmail.com personal accounts** — no Google Workspace (enterprise) subscription needed.

---

## 1. Overview

### What is Google Workspace?

"Google Workspace" is Google's paid enterprise product (formerly G Suite). You may see it mentioned in Google's documentation — ignore it for this project. The **Gmail API** and **Google Calendar API** are available to any Google account, including free `@gmail.com` accounts.

### The Google Workspace CLI (new, March 2026)

Google released a "Google Workspace CLI" in early 2026. This is a command-line and MCP tool for interacting with Google services from a terminal — it is **not a Python library** and not relevant to this project. Do not install it thinking it replaces the Python stack.

### The correct Python stack

Jarvis uses the standard Google client libraries, which are already listed in `requirements.txt`:

- `google-api-python-client` — makes API calls to Gmail, Calendar, etc.
- `google-auth-oauthlib` — handles the OAuth 2.0 consent flow
- `google-auth` — manages credentials and token refresh

---

## 2. How Google OAuth 2.0 Works

OAuth 2.0 is how your app proves to Google that a user has granted it permission to access their account. Here's the mental model:

```
credentials.json          OAuth consent screen        token.json
(who your app is)    →    (user clicks "Allow")   →   (proof they said yes)
```

**Step by step:**

1. You register your app in Google Cloud Console and download `credentials.json`. This file identifies your app to Google (client ID + client secret).
2. The first time Jarvis needs to access Gmail or Calendar, it opens a browser tab. You log in and click **Allow**.
3. Google sends back tokens. Jarvis saves them in `token.json`.
4. On every subsequent request, Jarvis uses the saved token — **no browser prompt again**.
5. Access tokens expire after 1 hour, but the token file also contains a refresh token. Jarvis automatically exchanges it for a new access token without any action from you.

### The "Google hasn't verified this app" warning

When you click Allow for the first time, Google may show a warning screen saying the app isn't verified. This is normal for personal projects in test mode. Click **"Continue"** — it is safe when you are the developer and the only user.

---

## 3. Google Cloud Console Setup (shared for Gmail and Calendar)

Both Gmail and Calendar use the same Google Cloud project and the same `credentials.json` file.

### Step 1 — Create a project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click the project dropdown at the top → **New Project**
3. Name it something like `jarvis-assistant` → **Create**
4. Make sure the new project is selected in the dropdown before continuing

### Step 2 — Enable the APIs

1. In the left sidebar, go to **APIs & Services → Library**
2. Search for **Gmail API** → click it → **Enable**
3. Go back to the Library, search for **Google Calendar API** → click it → **Enable**

Both APIs must be enabled even if you only plan to use one right now.

### Step 3 — Configure the OAuth consent screen

1. Go to **APIs & Services → OAuth consent screen**
2. Select **External** → **Create**
3. Fill in the required fields:
   - App name: `Jarvis` (or any name you like)
   - User support email: your Gmail address
   - Developer contact email: your Gmail address
4. Click **Save and Continue** through the Scopes screen (you can leave scopes empty here)
5. On the **Test users** screen, click **Add users** and add your own Gmail address
6. Click **Save and Continue** → **Back to Dashboard**

> **Why test mode?** Publishing an app requires Google verification (a lengthy process). Keeping it in test mode is fine for personal use. Test mode supports up to 100 users.

### Step 4 — Create OAuth credentials

1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth client ID**
3. Application type: **Desktop app**
4. Name it anything (e.g., `jarvis-desktop`) → **Create**
5. Click **Download JSON** on the confirmation dialog
6. Rename the downloaded file to `credentials.json`

### Step 5 — Place credentials.json in the project

Move `credentials.json` to the root of the Jarvis project directory (same level as `backend/`).

Confirm it is in `.gitignore` — it should already be there. Never commit this file to version control.

---

## 4. Gmail Setup

### Environment variables

Add these two lines to your `.env` file:

```
GMAIL_CREDENTIALS_FILE=credentials.json
GMAIL_TOKEN_FILE=token_gmail.json
```

- `GMAIL_CREDENTIALS_FILE` — path to the credentials file you downloaded
- `GMAIL_TOKEN_FILE` — path where Jarvis will save your Gmail token after first auth

### How the first run works

The first time you ask Jarvis anything Gmail-related (e.g., "what's in my inbox?"), it will:

1. Read `credentials.json` to identify the app
2. Open a browser tab to `accounts.google.com`
3. Ask you to select your Google account and click **Allow**
4. Save the resulting tokens to `token_gmail.json`
5. Complete your original request

After this, `token_gmail.json` exists and the browser will not open again.

### OAuth scopes used

The Gmail tool in `backend/tools/email.py` requests two scopes:

| Scope | Why |
|---|---|
| `gmail.readonly` | Needed to list and read emails (`list_emails`, `get_email`, `search_emails`) |
| `gmail.send` | Needed to send emails (`send_email`) |

These are the minimum scopes required. If you only need read access, you could remove `gmail.send` — but then `send_email` will fail.

### Quick test

Start Jarvis and send this message:

```
What's in my inbox?
```

If everything is configured correctly, Jarvis will list your recent emails.

### Troubleshooting Gmail

| Problem | Cause | Fix |
|---|---|---|
| Browser doesn't open | `GMAIL_CREDENTIALS_FILE` not set or file missing | Check `.env` and confirm `credentials.json` exists in the project root |
| `invalid_grant` error | Token revoked or corrupted | Delete `token_gmail.json` and re-authenticate |
| `insufficient authentication scopes` | Token was created with different scopes | Delete `token_gmail.json` and re-authenticate |
| `Access blocked: app not verified` | You are not on the test users list | Add your email in the OAuth consent screen → Test users |

---

## 5. Google Calendar Setup

> **Current state:** `backend/tools/calendar.py` stores events in a local JSON file (`data/calendar.json`). It does **not** connect to Google Calendar yet. This section explains how to add that integration.

### Environment variables

Add these to your `.env`:

```
GOOGLE_CALENDAR_CREDENTIALS_FILE=credentials.json
GOOGLE_CALENDAR_TOKEN_FILE=token_calendar.json
```

You can reuse the same `credentials.json` from the Gmail setup — both APIs are enabled on the same project.

### OAuth scope needed

Google Calendar requires this scope:

```
https://www.googleapis.com/auth/calendar
```

This grants read and write access to all calendars on the account. A narrower read-only scope (`calendar.readonly`) exists if you only need to view events.

### The `_get_calendar_service()` function

To connect `calendar.py` to real Google Calendar, you add a helper function that mirrors `_get_gmail_service()` in `email.py`:

```python
def _get_calendar_service():
    """Build and return an authenticated Google Calendar API service."""
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    import os

    SCOPES = ["https://www.googleapis.com/auth/calendar"]

    creds = None
    token_file = settings.google_calendar_token_file
    credentials_file = settings.google_calendar_credentials_file

    if token_file and os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif credentials_file:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        else:
            raise RuntimeError(
                "Calendar credentials not configured. Set GOOGLE_CALENDAR_CREDENTIALS_FILE in .env"
            )
        if token_file:
            with open(token_file, "w") as f:
                f.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)
```

This function is structurally identical to `_get_gmail_service()` — the only differences are the scope and the service name (`"calendar"`, `"v3"`).

### Updated tool signatures

Once `_get_calendar_service()` exists, each tool calls it instead of using `_store`. Example for `create_calendar_event`:

```python
@tool
def create_calendar_event(
    title: str,
    start_datetime: str,
    end_datetime: str,
    description: str = "",
    location: str = "",
) -> dict:
    """Create a Google Calendar event."""
    service = _get_calendar_service()
    event_body = {
        "summary": title,
        "description": description,
        "location": location,
        "start": {"dateTime": start_datetime, "timeZone": "UTC"},
        "end": {"dateTime": end_datetime, "timeZone": "UTC"},
    }
    result = service.events().insert(calendarId="primary", body=event_body).execute()
    return result
```

### Config changes needed

You also need to add the new settings to `backend/config.py`:

```python
# Google Calendar
google_calendar_credentials_file: str | None = Field(default=None, alias="GOOGLE_CALENDAR_CREDENTIALS_FILE")
google_calendar_token_file: str | None = Field(default=None, alias="GOOGLE_CALENDAR_TOKEN_FILE")
```

### Quick test

Once implemented, ask Jarvis:

```
Add a meeting tomorrow at 10am called "Team sync"
```

Then check your Google Calendar — the event should appear on the primary calendar.

---

## 6. Using Both Services Together

### Option A — Shared credentials, separate tokens (recommended)

Use the same `credentials.json` for both services, but separate token files. This is the setup described above.

```
GMAIL_CREDENTIALS_FILE=credentials.json
GMAIL_TOKEN_FILE=token_gmail.json
GOOGLE_CALENDAR_CREDENTIALS_FILE=credentials.json
GOOGLE_CALENDAR_TOKEN_FILE=token_calendar.json
```

Each service authenticates independently. The first Gmail request triggers the Gmail OAuth flow; the first Calendar request triggers the Calendar OAuth flow. You will click **Allow** twice total — once per service.

**Advantages:** Separate tokens mean you can revoke Calendar access without affecting Gmail, and vice versa. Easier to debug scope issues.

### Option B — Combined token

Request both scopes in a single OAuth flow and share one token file. This means one browser prompt instead of two. The downside is that revoking or re-authenticating resets access to both services at once.

This approach requires changing the scope list in both `_get_gmail_service()` and `_get_calendar_service()` to include all four scopes, and pointing both `token_file` settings to the same file.

**Recommendation:** Use Option A (separate tokens). The extra browser prompt is a one-time cost and easier to reason about.

---

## 7. Gotchas & Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| "Google hasn't verified this app" | App is in test mode | Click **Continue** — safe for personal use |
| Token expired / `invalid_grant` | Refresh token revoked (e.g., you changed your Google password) | Delete the token file and re-authenticate |
| "Access blocked: app not verified" | Email not in test users list | Go to OAuth consent screen → Test users → add your email |
| Too many test users | Test mode limit is 100 users | Only relevant if sharing with others; publish the app or add users individually |
| Rate limits hit | Too many API calls in a short window | Gmail: ~1 billion quota units/day; Calendar: ~1 million requests/day — very unlikely for personal use |
| `credentials.json` accidentally committed | Forgot to add to `.gitignore` | Rotate credentials immediately in Cloud Console (delete the OAuth client and create a new one); the committed file is now invalid |
| `ModuleNotFoundError: google` | Missing dependencies | Run `pip install -r requirements.txt` |
| Calendar events appear in wrong timezone | ISO datetime without timezone offset | Pass timezone-aware datetimes or set `timeZone` correctly in the event body |
