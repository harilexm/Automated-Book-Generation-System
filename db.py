"""
Supabase (PostgreSQL) client and CRUD helpers.
Provides a singleton Supabase client and convenient functions for creating, reading, and updating books, chapters, and logs.
"""

from supabase import create_client, Client
import config

# Singleton client 
_client: Client | None = None

def get_client() -> Client:
    """Return a singleton Supabase client."""
    global _client
    if _client is None:
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return _client

# BOOKS CRUD
def create_book(title: str, notes_before: str | None = None) -> dict:
    """Insert a new book and return its record."""
    data = {"title": title}
    if notes_before:
        data["notes_on_outline_before"] = notes_before
    result = get_client().table("books").insert(data).execute()
    return result.data[0]

def get_book(book_id: str) -> dict | None:
    """Fetch a single book by ID."""
    result = get_client().table("books").select("*").eq("id", book_id).execute()
    return result.data[0] if result.data else None

def update_book(book_id: str, data: dict) -> dict:
    """Update a book record. Returns updated record."""
    result = get_client().table("books").update(data).eq("id", book_id).execute()
    return result.data[0]

def get_all_books() -> list[dict]:
    """Fetch all books ordered by creation date."""
    result = get_client().table("books").select("*").order("created_at", desc=True).execute()
    return result.data

def delete_book(book_id: str) -> None:
    """Delete a book and all its chapters (CASCADE)."""
    get_client().table("books").delete().eq("id", book_id).execute()

# CHAPTERS CRUD
def create_chapter(book_id: str, chapter_number: int, title: str) -> dict:
    """Insert a new chapter record."""
    data = {
        "book_id": book_id,
        "chapter_number": chapter_number,
        "title": title,
        "chapter_notes_status": "no_notes_needed",
    }
    result = get_client().table("chapters").insert(data).execute()
    return result.data[0]

def get_chapter(chapter_id: str) -> dict | None:
    """Fetch a single chapter by ID."""
    result = get_client().table("chapters").select("*").eq("id", chapter_id).execute()
    return result.data[0] if result.data else None

def get_chapters(book_id: str) -> list[dict]:
    """Fetch all chapters for a book, ordered by chapter_number."""
    result = (
        get_client()
        .table("chapters")
        .select("*")
        .eq("book_id", book_id)
        .order("chapter_number")
        .execute()
    )
    return result.data

def update_chapter(chapter_id: str, data: dict) -> dict:
    """Update a chapter record. Returns updated record."""
    result = get_client().table("chapters").update(data).eq("id", chapter_id).execute()
    return result.data[0]

def delete_chapters(book_id: str) -> None:
    """Delete all chapters for a book (useful for regeneration)."""
    get_client().table("chapters").delete().eq("book_id", book_id).execute()

# NOTIFICATION LOG
def log_notification(book_id: str | None, event_type: str, message: str, channel: str) -> dict:
    """Insert a notification log entry."""
    data = {
        "event_type": event_type,
        "message": message,
        "channel": channel,
    }
    if book_id:
        data["book_id"] = book_id
    result = get_client().table("notification_logs").insert(data).execute()
    return result.data[0]