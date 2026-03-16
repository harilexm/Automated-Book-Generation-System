"""
Chapter generation with context chaining and review gates.

Logic:
1. Parse outline into chapter list
2. For each chapter N:
   a. Fetch summaries of chapters 1..N-1 from DB
   b. Generate chapter content via LLM (with context)
   c. Summarize the chapter for context chaining
   d. Save chapter + summary to DB
   e. Check chapter_notes_status gate
3. After all chapters: set book_output_status = 'chapters_done'
"""

import re
import db
import llm_service
import notifications


def parse_outline_chapters(outline: str) -> list[str]:
    """
    Parse a structured outline into a list of chapter titles.
    Looks for patterns like "Chapter 1: Title" or "Chapter 1 - Title".
    """
    # Match patterns like "Chapter 1: Title", "Chapter 1 - Title", "Chapter 1. Title"
    pattern = r"Chapter\s+(\d+)\s*[:\-\.]\s*(.+)"
    matches = re.findall(pattern, outline, re.IGNORECASE)

    if matches:
        # Sort by chapter number and return titles
        chapters = sorted(matches, key=lambda x: int(x[0]))
        return [title.strip() for _, title in chapters]

    # Fallback: split by numbered items or lines
    lines = [line.strip() for line in outline.split("\n") if line.strip()]
    chapters = []
    for line in lines:
        # Match "1. Title" or "1) Title"
        match = re.match(r"^\d+[\.\)]\s*(.+)", line)
        if match:
            chapters.append(match.group(1).strip())

    if chapters:
        return chapters

    # Last resort: treat non-empty lines as chapter titles
    print("  [WARNING] Could not parse chapter structure from outline. Using line-by-line.")
    return [line for line in lines if len(line) > 10][:8]


def run_chapter_stage(book_id: str) -> dict:
    """
    Run the chapter generation stage for a book.

    Returns a dict with:
      - status: "completed", "paused_waiting_chapter_notes", "paused_no_status"
      - chapters_generated: number of chapters successfully generated
      - message: human-readable status
    """
    print(f"\n{'='*60}")
    print(f"  📖 CHAPTER GENERATION STAGE — Book: {book_id}")
    print(f"{'='*60}")

    # Fetch book
    book = db.get_book(book_id)
    if not book:
        return {"status": "error", "message": f"Book not found: {book_id}"}

    title = book["title"]
    outline = book.get("outline")

    if not outline:
        msg = f"Book '{title}' has no outline. Run the outline stage first."
        return {"status": "error", "message": msg}

    # Parse chapter titles from outline
    chapter_titles = parse_outline_chapters(outline)
    if not chapter_titles:
        return {"status": "error", "message": "Could not parse chapters from outline."}

    print(f"\n  Found {len(chapter_titles)} chapters to generate:")
    for i, ct in enumerate(chapter_titles, 1):
        print(f"    {i}. {ct}")

    # Check existing chapters (in case of resume)
    existing_chapters = db.get_chapters(book_id)
    existing_nums = {ch["chapter_number"] for ch in existing_chapters}

    chapters_generated = len(existing_nums)

    # Generate each chapter
    for idx, chapter_title in enumerate(chapter_titles, 1):
        print(f"\n{'─'*50}")
        print(f"  📝 Chapter {idx}/{len(chapter_titles)}: {chapter_title}")
        print(f"{'─'*50}")

        # Skip already generated chapters
        if idx in existing_nums:
            ch = next(c for c in existing_chapters if c["chapter_number"] == idx)
            if ch.get("content") and ch.get("status") in ("generated", "approved"):
                print(f"  ⏭️  Chapter {idx} already generated. Skipping.")
                continue

        # Gather summaries of all previous chapters for context
        all_chapters = db.get_chapters(book_id)
        previous_summaries = []
        for ch in all_chapters:
            if ch["chapter_number"] < idx and ch.get("summary"):
                previous_summaries.append(ch["summary"])

        # Check for per-chapter notes
        chapter_record = next(
            (c for c in all_chapters if c["chapter_number"] == idx), None
        )
        chapter_notes = chapter_record.get("chapter_notes") if chapter_record else None

        # Generate chapter content
        content = llm_service.generate_chapter(
            book_title=title,
            outline=outline,
            chapter_number=idx,
            chapter_title=chapter_title,
            previous_summaries=previous_summaries,
            chapter_notes=chapter_notes,
        )

        # Generate summary for context chaining
        summary = llm_service.summarize_chapter(content)

        # Save or update chapter in DB
        if chapter_record:
            db.update_chapter(chapter_record["id"], {
                "title": chapter_title,
                "content": content,
                "summary": summary,
                "status": "generated",
            })
        else:
            ch = db.create_chapter(book_id, idx, chapter_title)
            db.update_chapter(ch["id"], {
                "content": content,
                "summary": summary,
                "status": "generated",
            })

        chapters_generated += 1
        print(f"  ✅ Chapter {idx} generated ({len(content)} chars)")
        print(f"     Summary: {summary[:100]}...")

        # GATE: Check chapter_notes_status
        # Re-fetch the book for the latest status
        book = db.get_book(book_id)
        chapter_notes_status = book.get("chapter_notes_status", "no_notes_needed")

        if chapter_notes_status == "yes":
            msg = (
                f"Chapter {idx}: '{chapter_title}' generated.\n"
                f"chapter_notes_status = 'yes' → Pausing for review.\n"
                f"Add notes to the chapter in the chapters table,\n"
                f"then set chapter_notes_status to 'no_notes_needed' and re-run."
            )
            notifications.notify(book_id, "chapter_waiting_notes", msg)
            return {
                "status": "paused_waiting_chapter_notes",
                "chapters_generated": chapters_generated,
                "paused_at_chapter": idx,
                "message": msg,
            }
        elif chapter_notes_status == "no" or not chapter_notes_status:
            msg = (
                f"Chapter {idx} generated but chapter_notes_status = '{chapter_notes_status}'.\n"
                f"Set to 'no_notes_needed' to continue, or 'yes' to add notes."
            )
            notifications.notify(book_id, "chapter_paused", msg)
            return {
                "status": "paused_no_status",
                "chapters_generated": chapters_generated,
                "paused_at_chapter": idx,
                "message": msg,
            }
        # else: no_notes_needed → continue to next chapter

        # Notify progress
        notifications.notify(
            book_id,
            "chapter_generated",
            f"Chapter {idx}/{len(chapter_titles)} '{chapter_title}' generated successfully."
        )

    # All chapters done
    db.update_book(book_id, {"book_output_status": "chapters_done"})
    msg = f"All {len(chapter_titles)} chapters generated for '{title}'!"
    notifications.notify(book_id, "all_chapters_done", msg)

    return {"status": "completed", "chapters_generated": chapters_generated, "message": msg}