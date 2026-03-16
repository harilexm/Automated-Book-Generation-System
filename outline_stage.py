"""
Outline generation with human-in-the-loop gating.

Logic:
1. Check notes_on_outline_before exists → if not, pause + notify
2. Generate outline via LLM
3. Save to DB, notify "outline ready"
4. Check status_outline_notes:
   - "yes" → pause, wait for notes_on_outline_after
   - "no_notes_needed" → proceed
   - "no"/empty → pause
5. If notes_after exist → regenerate outline
"""

import db
import llm_service
import notifications


def run_outline_stage(book_id: str) -> dict:
    """
    Run the outline generation stage for a book.

    Returns a dict with:
      - status: "completed", "paused_waiting_notes_before",
                "paused_waiting_outline_notes", "paused_no_status"
      - outline: the generated outline text (if generated)
      - message: human-readable status
    """
    print(f"\n{'='*60}")
    print(f"  [OUTLINE STAGE] Book: {book_id}")
    print(f"{'='*60}")

    # Fetch book
    book = db.get_book(book_id)
    if not book:
        return {"status": "error", "message": f"Book not found: {book_id}"}

    title = book["title"]
    notes_before = book.get("notes_on_outline_before")
    notes_after = book.get("notes_on_outline_after")
    status_notes = book.get("status_outline_notes", "no")

    # GATE 1: Check notes_on_outline_before
    if not notes_before:
        msg = f"Book '{title}' is missing 'notes_on_outline_before'. Cannot generate outline."
        notifications.notify(book_id, "outline_paused", msg)
        db.update_book(book_id, {"book_output_status": "paused"})
        return {
            "status": "paused_waiting_notes_before",
            "message": msg,
        }

    # Generate or regenerate outline
    existing_outline = book.get("outline")

    if existing_outline and not notes_after:
        # Outline already exists and no new notes — skip regeneration
        print(f"  [OK] Outline already exists for '{title}'. Skipping regeneration.")
        outline = existing_outline
    else:
        # Generate new outline (or regenerate with notes_after)
        outline = llm_service.generate_outline(title, notes_before, notes_after)

        # Save outline to DB
        db.update_book(book_id, {
            "outline": outline,
            "book_output_status": "outline_done",
        })
        print(f"\n  [OK] Outline generated and saved for '{title}'")

    # Notify: outline ready
    notifications.notify(
        book_id,
        "outline_ready",
        f"Outline for '{title}' is ready for review.\n\n"
        f"To add notes: update 'notes_on_outline_after' in the books table.\n"
        f"Then set 'status_outline_notes' to 'no_notes_needed' to proceed, "
        f"or 'yes' if you want to add notes first."
    )

    # GATE 2: Check status_outline_notes
    # Re-fetch book to get latest status (in case it was updated)
    book = db.get_book(book_id)
    status_notes = book.get("status_outline_notes", "no")

    if status_notes == "no_notes_needed":
        print(f"  [>>] status_outline_notes = 'no_notes_needed' -> Proceeding to chapters.")
        return {
            "status": "completed",
            "outline": outline,
            "message": f"Outline for '{title}' is complete. Ready for chapter generation.",
        }

    elif status_notes == "yes":
        # Check if notes_after already exist (maybe editor already filled them)
        notes_after = book.get("notes_on_outline_after")
        if notes_after:
            print(f"  [REGEN] Found notes_on_outline_after. Regenerating outline...")
            # Regenerate with the notes
            outline = llm_service.generate_outline(title, notes_before, notes_after)
            db.update_book(book_id, {
                "outline": outline,
                "status_outline_notes": "no_notes_needed",
            })
            notifications.notify(
                book_id,
                "outline_regenerated",
                f"Outline for '{title}' has been regenerated with editor notes."
            )
            return {
                "status": "completed",
                "outline": outline,
                "message": f"Outline regenerated with notes. Ready for chapters.",
            }
        else:
            msg = (
                f"status_outline_notes = 'yes' but no notes found yet.\n"
                f"Please add 'notes_on_outline_after' in the books table,\n"
                f"then re-run the outline stage."
            )
            notifications.notify(book_id, "outline_waiting_notes", msg)
            db.update_book(book_id, {"book_output_status": "paused"})
            return {
                "status": "paused_waiting_outline_notes",
                "outline": outline,
                "message": msg,
            }

    else:
        # status is "no" or empty → pause
        msg = (
            f"status_outline_notes = '{status_notes}' -> Pausing.\n"
            f"Set 'status_outline_notes' to 'no_notes_needed' to proceed,\n"
            f"or 'yes' to provide notes."
        )
        notifications.notify(book_id, "outline_paused", msg)
        db.update_book(book_id, {"book_output_status": "paused"})
        return {
            "status": "paused_no_status",
            "outline": outline,
            "message": msg,
        }