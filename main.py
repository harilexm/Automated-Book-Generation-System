# CLI orchestrator for the Automated Book Generation System.
import argparse
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    parser = argparse.ArgumentParser(
        description="Automated Book Generation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
                Examples:
                python main.py --create-sample                       Create sample input Excel
                python main.py --input input/books_input.xlsx        Full pipeline (input → outline → chapters → compile)
                python main.py --stage outline --book-id <uuid>      Run outline stage only
                python main.py --stage chapters --book-id <uuid>     Generate chapters only
                python main.py --stage compile --book-id <uuid>      Compile final book
                python main.py --list                                List all books in database
                        """
    )

    parser.add_argument("--input", type=str, help="Path to input Excel file (.xlsx)")
    parser.add_argument("--stage", type=str, choices=["outline", "chapters", "compile"], help="Run a specific stage")
    parser.add_argument("--book-id", type=str, help="Book ID (UUID) for stage-specific runs")
    parser.add_argument("--list", action="store_true", help="List all books in database")
    parser.add_argument("--create-sample", action="store_true", help="Create a sample input Excel file")
    parser.add_argument("--delete", type=str, metavar="BOOK_ID", help="Delete a book by ID (also deletes its chapters)")
    parser.add_argument("--delete-all", action="store_true", help="Delete ALL books from database")

    args = parser.parse_args()

    # Create sample input
    if args.create_sample:
        from input_handler import create_sample_input
        create_sample_input("input/books_input.xlsx")
        return

    # Delete a single book
    if args.delete:
        import db
        book = db.get_book(args.delete)
        if not book:
            print(f"[ERROR] Book not found: {args.delete}")
            return
        title = book["title"]
        db.delete_book(args.delete)
        print(f"  [DELETED] '{title}' ({args.delete})")
        return

    # Delete all books
    if args.delete_all:
        import db
        books = db.get_all_books()
        if not books:
            print("  No books to delete.")
            return
        confirm = input(f"  Are you sure you want to delete ALL {len(books)} books? (yes/no): ")
        if confirm.lower() != "yes":
            print("  Cancelled.")
            return
        for b in books:
            db.delete_book(b["id"])
            print(f"  [DELETED] '{b['title']}' ({b['id']})")
        print(f"\n  Deleted {len(books)} book(s).")
        return

    # List books
    if args.list:
        import db
        books = db.get_all_books()
        if not books:
            print("\n  No books found in database.")
            return

        print(f"\n  Books in Database ({len(books)}):")
        print(f"  {'-'*70}")
        for b in books:
            status = b.get('book_output_status', 'unknown')
            print(f"  ID: {b['id']}")
            print(f"     Title:  {b['title']}")
            print(f"     Status: {status}")
            print(f"     Created: {b['created_at']}")
            print(f"  {'-'*70}")
        return

    # Run specific stage
    if args.stage:
        if not args.book_id:
            print("[ERROR] --book-id is required when using --stage")
            sys.exit(1)

        _run_stage(args.stage, args.book_id)
        return

    # Full pipeline
    if args.input:
        _run_full_pipeline(args.input)
        return

    # No arguments: show help
    parser.print_help()


def _run_stage(stage: str, book_id: str) -> dict:
    """Run a single stage and return the result."""
    if stage == "outline":
        from outline_stage import run_outline_stage
        return run_outline_stage(book_id)
    elif stage == "chapters":
        from chapter_stage import run_chapter_stage
        return run_chapter_stage(book_id)
    elif stage == "compile":
        from compile_stage import run_compile_stage
        return run_compile_stage(book_id)


def _run_full_pipeline(input_path: str):
    """Run the complete pipeline: input → outline → chapters → compile."""
    print("\n" + "=" * 60)
    print("  AUTOMATED BOOK GENERATION SYSTEM")
    print("  Full Pipeline Run")
    print("=" * 60)

    # Step 1: Read input
    print("\n\n>> STEP 1: Reading input file...")
    from input_handler import read_input
    books = read_input(input_path)

    if not books:
        print("[ERROR] No books loaded from input file.")
        return

    # Process each book
    for book in books:
        book_id = book["id"]
        title = book["title"]
        print(f"\n\n{'='*60}")
        print(f"  Processing: {title}")
        print(f"  Book ID: {book_id}")
        print(f"{'='*60}")

        # Step 2: Outline stage
        print("\n\n>> STEP 2: Outline Generation...")
        from outline_stage import run_outline_stage
        result = run_outline_stage(book_id)
        print(f"\n  Result: {result['status']}")
        print(f"  Message: {result['message']}")

        if result["status"] != "completed":
            print(f"\n  [PAUSED] Pipeline paused at OUTLINE stage.")
            print(f"     Fix the issue in Supabase, then re-run:")
            print(f"     python main.py --stage outline --book-id {book_id}")
            continue

        # Step 3: Chapter generation
        print("\n\n>> STEP 3: Chapter Generation...")
        from chapter_stage import run_chapter_stage
        result = run_chapter_stage(book_id)
        print(f"\n  Result: {result['status']}")
        print(f"  Message: {result['message']}")

        if result["status"] != "completed":
            print(f"\n  [PAUSED] Pipeline paused at CHAPTER stage.")
            print(f"     Fix the issue in Supabase, then re-run:")
            print(f"     python main.py --stage chapters --book-id {book_id}")
            continue

        # Step 4: Compile
        print("\n\n>> STEP 4: Final Compilation...")

        from compile_stage import run_compile_stage
        result = run_compile_stage(book_id)
        print(f"\n  Result: {result['status']}")
        print(f"  Message: {result['message']}")

        if result["status"] == "completed":
            print(f"\n  [DONE] Book '{title}' is complete!")
            print(f"     DOCX: {result.get('docx_path', 'N/A')}")
            print(f"     TXT:  {result.get('txt_path', 'N/A')}")
        else:
            print(f"\n  [PAUSED] Pipeline paused at COMPILE stage.")
            print(f"     python main.py --stage compile --book-id {book_id}")

    print("\n\n" + "=" * 60)
    print("  PIPELINE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()