"""
Google Workspace tool functions and Claude tool schemas.
13 tools: Gmail (4), Calendar (4), Drive (5).

All functions use asyncio.to_thread() to wrap the synchronous google-api-python-client.
"""

import asyncio
import base64
import logging
import time
from datetime import UTC, datetime, timedelta
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

# Timeout for read operations (list, get, search)
_READ_TIMEOUT = 30
# Timeout for write operations (create, update, send)
_WRITE_TIMEOUT = 45


async def _with_timeout(coro, timeout: int):
    """Wrap an async call with a timeout."""
    return await asyncio.wait_for(coro, timeout=timeout)


def _retry_on_google_error(func, max_retries: int = 3):
    """Decorator-style wrapper: retry sync Google API calls on 429/500/503."""

    def wrapper(*args, **kwargs):
        last_error = None
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                status = None
                # googleapiclient.errors.HttpError has resp.status
                if hasattr(e, "resp") and hasattr(e.resp, "status"):
                    status = e.resp.status
                elif hasattr(e, "status_code"):
                    status = e.status_code
                if status in (429, 500, 503) and attempt < max_retries - 1:
                    wait = (2**attempt) * 1.0
                    logger.warning(f"Google API {status}, retrying in {wait}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait)
                    continue
                raise
        raise last_error

    return wrapper


# =====================================================================
# Service builders (lazy, cached per call)
# =====================================================================


def _gmail_service():
    from googleapiclient.discovery import build

    from realize_core.tools.google_auth import get_credentials

    creds = get_credentials()
    if not creds:
        raise RuntimeError("Google credentials not available. See docs for OAuth setup.")
    return build("gmail", "v1", credentials=creds)


def _calendar_service():
    from googleapiclient.discovery import build

    from realize_core.tools.google_auth import get_credentials

    creds = get_credentials()
    if not creds:
        raise RuntimeError("Google credentials not available. See docs for OAuth setup.")
    return build("calendar", "v3", credentials=creds)


def _drive_service():
    from googleapiclient.discovery import build

    from realize_core.tools.google_auth import get_credentials

    creds = get_credentials()
    if not creds:
        raise RuntimeError("Google credentials not available. See docs for OAuth setup.")
    return build("drive", "v3", credentials=creds)


# =====================================================================
# Gmail Tools
# =====================================================================


def _gmail_search_sync(query: str, max_results: int = 5) -> list[dict]:
    service = _gmail_service()
    results = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    messages = results.get("messages", [])
    output = []
    for msg_stub in messages:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=msg_stub["id"], format="metadata", metadataHeaders=["From", "To", "Subject", "Date"])
            .execute()
        )
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        output.append(
            {
                "id": msg["id"],
                "from": headers.get("From", ""),
                "to": headers.get("To", ""),
                "subject": headers.get("Subject", ""),
                "snippet": msg.get("snippet", ""),
                "date": headers.get("Date", ""),
            }
        )
    return output


async def gmail_search(query: str, max_results: int = 5) -> list[dict]:
    return await _with_timeout(
        asyncio.to_thread(_retry_on_google_error(_gmail_search_sync), query, max_results), _READ_TIMEOUT
    )


def _gmail_read_sync(message_id: str) -> dict:
    service = _gmail_service()
    msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
    body = ""
    payload = msg.get("payload", {})
    if payload.get("body", {}).get("data"):
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    elif payload.get("parts"):
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                break
    return {
        "id": msg["id"],
        "from": headers.get("From", ""),
        "to": headers.get("To", ""),
        "subject": headers.get("Subject", ""),
        "date": headers.get("Date", ""),
        "body": body[:3000],
    }


async def gmail_read(message_id: str) -> dict:
    return await _with_timeout(asyncio.to_thread(_retry_on_google_error(_gmail_read_sync), message_id), _READ_TIMEOUT)


def _gmail_send_sync(to: str, subject: str, body: str, cc: str = None) -> dict:
    service = _gmail_service()
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    if cc:
        message["cc"] = cc
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return {"id": result.get("id"), "threadId": result.get("threadId"), "status": "sent"}


async def gmail_send(to: str, subject: str, body: str, cc: str = None) -> dict:
    return await _with_timeout(
        asyncio.to_thread(_retry_on_google_error(_gmail_send_sync), to, subject, body, cc), _WRITE_TIMEOUT
    )


def _gmail_create_draft_sync(to: str, subject: str, body: str, cc: str = None) -> dict:
    service = _gmail_service()
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    if cc:
        message["cc"] = cc
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    result = service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
    return {"id": result.get("id"), "message_id": result.get("message", {}).get("id"), "status": "draft_created"}


async def gmail_create_draft(to: str, subject: str, body: str, cc: str = None) -> dict:
    return await _with_timeout(
        asyncio.to_thread(_retry_on_google_error(_gmail_create_draft_sync), to, subject, body, cc), _WRITE_TIMEOUT
    )


# =====================================================================
# Calendar Tools
# =====================================================================


def _calendar_list_events_sync(
    time_min: str = None, time_max: str = None, calendar_id: str = "primary", max_results: int = 10
) -> list[dict]:
    service = _calendar_service()
    now = datetime.now(UTC)
    if not time_min:
        time_min = now.isoformat()
    if not time_max:
        time_max = (now + timedelta(days=7)).isoformat()
    results = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = []
    for event in results.get("items", []):
        start = event.get("start", {}).get("dateTime", event.get("start", {}).get("date", ""))
        end = event.get("end", {}).get("dateTime", event.get("end", {}).get("date", ""))
        attendees = [a.get("email", "") for a in event.get("attendees", [])]
        events.append(
            {
                "id": event.get("id"),
                "summary": event.get("summary", "(No title)"),
                "start": start,
                "end": end,
                "location": event.get("location", ""),
                "attendees": attendees,
                "status": event.get("status", ""),
            }
        )
    return events


async def calendar_list_events(
    time_min: str = None, time_max: str = None, calendar_id: str = "primary", max_results: int = 10
) -> list[dict]:
    return await _with_timeout(
        asyncio.to_thread(
            _retry_on_google_error(_calendar_list_events_sync), time_min, time_max, calendar_id, max_results
        ),
        _READ_TIMEOUT,
    )


def _calendar_create_event_sync(
    summary: str,
    start: str,
    end: str,
    description: str = None,
    attendees: list[str] = None,
    calendar_id: str = "primary",
) -> dict:
    service = _calendar_service()
    event_body = {"summary": summary, "start": {"dateTime": start}, "end": {"dateTime": end}}
    if description:
        event_body["description"] = description
    if attendees:
        event_body["attendees"] = [{"email": e} for e in attendees]
    result = service.events().insert(calendarId=calendar_id, body=event_body).execute()
    return {
        "id": result.get("id"),
        "summary": result.get("summary"),
        "start": result.get("start", {}).get("dateTime", ""),
        "end": result.get("end", {}).get("dateTime", ""),
        "htmlLink": result.get("htmlLink", ""),
    }


async def calendar_create_event(
    summary: str,
    start: str,
    end: str,
    description: str = None,
    attendees: list[str] = None,
    calendar_id: str = "primary",
) -> dict:
    return await _with_timeout(
        asyncio.to_thread(
            _retry_on_google_error(_calendar_create_event_sync),
            summary,
            start,
            end,
            description,
            attendees,
            calendar_id,
        ),
        _WRITE_TIMEOUT,
    )


def _calendar_update_event_sync(event_id: str, calendar_id: str = "primary", **updates) -> dict:
    service = _calendar_service()
    event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
    for key, value in updates.items():
        if key in ("start", "end") and isinstance(value, str):
            event[key] = {"dateTime": value}
        elif key == "attendees" and isinstance(value, list):
            event["attendees"] = [{"email": e} for e in value]
        else:
            event[key] = value
    result = service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()
    return {
        "id": result.get("id"),
        "summary": result.get("summary"),
        "start": result.get("start", {}).get("dateTime", ""),
        "end": result.get("end", {}).get("dateTime", ""),
        "status": "updated",
    }


async def calendar_update_event(event_id: str, calendar_id: str = "primary", **updates) -> dict:
    return await _with_timeout(
        asyncio.to_thread(_retry_on_google_error(_calendar_update_event_sync), event_id, calendar_id, **updates),
        _WRITE_TIMEOUT,
    )


def _calendar_find_free_time_sync(time_min: str, time_max: str, calendar_ids: list[str] = None) -> list[dict]:
    service = _calendar_service()
    if not calendar_ids:
        calendar_ids = ["primary"]
    body = {"timeMin": time_min, "timeMax": time_max, "items": [{"id": cid} for cid in calendar_ids]}
    result = service.freebusy().query(body=body).execute()
    busy_slots = []
    for cal_id, cal_data in result.get("calendars", {}).items():
        for busy in cal_data.get("busy", []):
            busy_slots.append({"start": busy["start"], "end": busy["end"], "calendar": cal_id})
    return busy_slots


async def calendar_find_free_time(time_min: str, time_max: str, calendar_ids: list[str] = None) -> list[dict]:
    return await _with_timeout(
        asyncio.to_thread(_retry_on_google_error(_calendar_find_free_time_sync), time_min, time_max, calendar_ids),
        _READ_TIMEOUT,
    )


# =====================================================================
# Drive Tools
# =====================================================================


def _drive_search_sync(query: str, max_results: int = 10) -> list[dict]:
    service = _drive_service()
    safe_query = query.replace("\\", "\\\\").replace("'", "\\'")
    results = (
        service.files()
        .list(
            q=f"fullText contains '{safe_query}' and trashed = false",
            pageSize=max_results,
            fields="files(id, name, mimeType, modifiedTime, webViewLink)",
            orderBy="modifiedTime desc",
        )
        .execute()
    )
    return [
        {
            "id": f.get("id"),
            "name": f.get("name"),
            "mimeType": f.get("mimeType", ""),
            "modifiedTime": f.get("modifiedTime", ""),
            "webViewLink": f.get("webViewLink", ""),
        }
        for f in results.get("files", [])
    ]


async def drive_search(query: str, max_results: int = 10) -> list[dict]:
    return await _with_timeout(
        asyncio.to_thread(_retry_on_google_error(_drive_search_sync), query, max_results), _READ_TIMEOUT
    )


def _drive_list_folder_sync(folder_id: str = "root", max_results: int = 20) -> list[dict]:
    service = _drive_service()
    results = (
        service.files()
        .list(
            q=f"'{folder_id}' in parents and trashed = false",
            pageSize=max_results,
            fields="files(id, name, mimeType, modifiedTime)",
            orderBy="name",
        )
        .execute()
    )
    return [
        {
            "id": f.get("id"),
            "name": f.get("name"),
            "mimeType": f.get("mimeType", ""),
            "modifiedTime": f.get("modifiedTime", ""),
        }
        for f in results.get("files", [])
    ]


async def drive_list_folder(folder_id: str = "root", max_results: int = 20) -> list[dict]:
    return await _with_timeout(
        asyncio.to_thread(_retry_on_google_error(_drive_list_folder_sync), folder_id, max_results), _READ_TIMEOUT
    )


def _drive_read_content_sync(file_id: str) -> dict:
    service = _drive_service()
    meta = service.files().get(fileId=file_id, fields="id, name, mimeType").execute()
    mime_type = meta.get("mimeType", "")
    name = meta.get("name", "")
    export_map = {
        "application/vnd.google-apps.document": ("text/plain", "text"),
        "application/vnd.google-apps.spreadsheet": ("text/csv", "csv"),
        "application/vnd.google-apps.presentation": ("text/plain", "text"),
    }
    if mime_type in export_map:
        export_mime, fmt = export_map[mime_type]
        content = service.files().export(fileId=file_id, mimeType=export_mime).execute()
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        if len(content) > 8000:
            content = content[:8000] + "\n\n... (truncated)"
        return {"id": file_id, "name": name, "mimeType": mime_type, "format": fmt, "content": content}
    try:
        content = service.files().get_media(fileId=file_id).execute()
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        if len(content) > 8000:
            content = content[:8000] + "\n\n... (truncated)"
        return {"id": file_id, "name": name, "mimeType": mime_type, "format": "raw", "content": content}
    except Exception:
        return {"id": file_id, "name": name, "mimeType": mime_type, "error": "Cannot read content of this file type"}


async def drive_read_content(file_id: str) -> dict:
    return await _with_timeout(
        asyncio.to_thread(_retry_on_google_error(_drive_read_content_sync), file_id), _READ_TIMEOUT
    )


def _drive_create_doc_sync(title: str, content: str = "", folder_id: str = None) -> dict:
    from googleapiclient.discovery import build as _build

    from realize_core.tools.google_auth import get_credentials

    service = _drive_service()
    file_metadata = {"name": title, "mimeType": "application/vnd.google-apps.document"}
    if folder_id:
        file_metadata["parents"] = [folder_id]
    doc = service.files().create(body=file_metadata, fields="id, name, webViewLink").execute()
    if content:
        creds = get_credentials()
        docs_service = _build("docs", "v1", credentials=creds)
        docs_service.documents().batchUpdate(
            documentId=doc["id"],
            body={"requests": [{"insertText": {"location": {"index": 1}, "text": content}}]},
        ).execute()
    return {"id": doc["id"], "name": doc["name"], "webViewLink": doc.get("webViewLink", ""), "status": "created"}


async def drive_create_doc(title: str, content: str = "", folder_id: str = None) -> dict:
    return await _with_timeout(
        asyncio.to_thread(_retry_on_google_error(_drive_create_doc_sync), title, content, folder_id), _WRITE_TIMEOUT
    )


def _drive_append_doc_sync(file_id: str, content: str) -> dict:
    from googleapiclient.discovery import build as _build

    from realize_core.tools.google_auth import get_credentials

    creds = get_credentials()
    docs_service = _build("docs", "v1", credentials=creds)
    doc = docs_service.documents().get(documentId=file_id).execute()
    end_index = doc["body"]["content"][-1]["endIndex"] - 1
    docs_service.documents().batchUpdate(
        documentId=file_id,
        body={"requests": [{"insertText": {"location": {"index": end_index}, "text": "\n" + content}}]},
    ).execute()
    return {"id": file_id, "title": doc.get("title", ""), "status": "appended", "chars_added": len(content)}


async def drive_append_doc(file_id: str, content: str) -> dict:
    return await _with_timeout(
        asyncio.to_thread(_retry_on_google_error(_drive_append_doc_sync), file_id, content), _WRITE_TIMEOUT
    )


# =====================================================================
# Tool Schemas + Registry
# =====================================================================

GOOGLE_TOOL_SCHEMAS = [
    {
        "name": "gmail_search",
        "description": "Search emails in Gmail. Use this to find emails by sender, subject, keywords, labels, or date. Supports full Gmail search syntax.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Gmail search query (e.g., 'from:name subject:budget', 'is:unread after:2025/01/01')",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results to return (default: 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "gmail_read",
        "description": "Read the full content of a specific email by its message ID. Use after gmail_search to read a found email.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {"type": "string", "description": "Gmail message ID (from gmail_search results)"}
            },
            "required": ["message_id"],
        },
    },
    {
        "name": "gmail_send",
        "description": "Send an email from the user's Gmail account. DESTRUCTIVE: sends immediately. Requires user confirmation before calling.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Email body text (plain text)"},
                "cc": {"type": "string", "description": "CC email address (optional)"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "gmail_create_draft",
        "description": "Create a draft email (not sent). Use this when you want user review before sending. Safer than gmail_send.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Email body text (plain text)"},
                "cc": {"type": "string", "description": "CC email address (optional)"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "calendar_list_events",
        "description": "List upcoming calendar events within a time range. Defaults to the next 7 days if no range specified.",
        "input_schema": {
            "type": "object",
            "properties": {
                "time_min": {
                    "type": "string",
                    "description": "Start of range in ISO 8601 format (e.g., '2025-03-30T00:00:00Z'). Defaults to now.",
                },
                "time_max": {
                    "type": "string",
                    "description": "End of range in ISO 8601 format. Defaults to 7 days from now.",
                },
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar ID (default: 'primary')",
                    "default": "primary",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum events to return (default: 10)",
                    "default": 10,
                },
            },
        },
    },
    {
        "name": "calendar_create_event",
        "description": "Create a new calendar event. DESTRUCTIVE: creates immediately. Include attendees to send invitations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Event title"},
                "start": {
                    "type": "string",
                    "description": "Start time in ISO 8601 format (e.g., '2025-03-30T10:00:00+01:00')",
                },
                "end": {"type": "string", "description": "End time in ISO 8601 format"},
                "description": {"type": "string", "description": "Event description/notes (optional)"},
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of attendee email addresses (optional)",
                },
                "calendar_id": {"type": "string", "description": "Calendar ID (default: 'primary')"},
            },
            "required": ["summary", "start", "end"],
        },
    },
    {
        "name": "calendar_update_event",
        "description": "Update an existing calendar event by ID. DESTRUCTIVE: modifies the event immediately.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "Event ID (from calendar_list_events results)"},
                "summary": {"type": "string", "description": "New event title (optional)"},
                "start": {"type": "string", "description": "New start time in ISO 8601 format (optional)"},
                "end": {"type": "string", "description": "New end time in ISO 8601 format (optional)"},
                "calendar_id": {"type": "string", "description": "Calendar ID (default: 'primary')"},
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "calendar_find_free_time",
        "description": "Find busy time slots across one or more calendars. Use this to check availability before scheduling.",
        "input_schema": {
            "type": "object",
            "properties": {
                "time_min": {"type": "string", "description": "Start of range in ISO 8601 format"},
                "time_max": {"type": "string", "description": "End of range in ISO 8601 format"},
                "calendar_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Calendar IDs to check (default: ['primary'])",
                },
            },
            "required": ["time_min", "time_max"],
        },
    },
    {
        "name": "drive_search",
        "description": "Search for files in Google Drive by name or content. Returns file metadata with links.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keywords (searches file names and contents)"},
                "max_results": {
                    "type": "integer",
                    "description": "Maximum files to return (default: 10)",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "drive_list_folder",
        "description": "List files and subfolders in a Google Drive folder. Use 'root' for the top-level Drive.",
        "input_schema": {
            "type": "object",
            "properties": {
                "folder_id": {
                    "type": "string",
                    "description": "Folder ID, or 'root' for top-level Drive (default: 'root')",
                    "default": "root",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum items to return (default: 20)",
                    "default": 20,
                },
            },
        },
    },
    {
        "name": "drive_read_content",
        "description": "Read the text content of a Google Doc, Sheet (as CSV), or plain text file. Content is truncated at 8000 chars.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "Google Drive file ID (from drive_search or drive_list_folder results)",
                }
            },
            "required": ["file_id"],
        },
    },
    {
        "name": "drive_create_doc",
        "description": "Create a new Google Doc in Drive. DESTRUCTIVE: creates immediately. Optionally pre-populate with content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Document title"},
                "content": {"type": "string", "description": "Initial text content (optional)"},
                "folder_id": {"type": "string", "description": "Parent folder ID (optional, defaults to root)"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "drive_append_doc",
        "description": "Append text to the end of an existing Google Doc. DESTRUCTIVE: modifies the document immediately.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "Google Doc file ID"},
                "content": {"type": "string", "description": "Text to append at the end of the document"},
            },
            "required": ["file_id", "content"],
        },
    },
]

WRITE_TOOLS = {
    "gmail_send",
    "gmail_create_draft",
    "calendar_create_event",
    "calendar_update_event",
    "drive_create_doc",
    "drive_append_doc",
}
READ_TOOLS = {
    "gmail_search",
    "gmail_read",
    "calendar_list_events",
    "calendar_find_free_time",
    "drive_search",
    "drive_list_folder",
    "drive_read_content",
}

TOOL_FUNCTIONS = {
    "gmail_search": gmail_search,
    "gmail_read": gmail_read,
    "gmail_send": gmail_send,
    "gmail_create_draft": gmail_create_draft,
    "calendar_list_events": calendar_list_events,
    "calendar_create_event": calendar_create_event,
    "calendar_update_event": calendar_update_event,
    "calendar_find_free_time": calendar_find_free_time,
    "drive_search": drive_search,
    "drive_list_folder": drive_list_folder,
    "drive_read_content": drive_read_content,
    "drive_create_doc": drive_create_doc,
    "drive_append_doc": drive_append_doc,
}
