# Automated Book Generation System

## Problem Statement

This system automates book writing by accepting a title and editor notes, generating an outline and chapters using AI, and compiling the final draft into `.docx` and `.txt`. It implements **human-in-the-loop gating** at every stage — no step proceeds without editor approval via the database.

---

## System Architecture

```
  Excel Input --> input_handler --> Supabase DB
                                       |
                       outline_stage (LLM + Gate)
                                       |
                       chapter_stage (LLM + Context Chaining + Gate)
                                       |
                       compile_stage --> .docx / .txt + Supabase Storage
                                       |
                       notifications --> Email / Console
```

**Gating at every stage:**
```
  Pipeline runs --> generates content --> PAUSES --> sends email
                                                        |
  Editor reviews in Supabase --> approves/adds notes --> re-run
                                                        |
                                             Pipeline continues
```

Each gate uses a 3-way status field (`yes` / `no` / `no_notes_needed`):
- `no_notes_needed` — approved, proceed
- `yes` — editor wants to add feedback, regenerate with notes
- `no` / empty — paused, waiting for editor decision

---

## Tech Stack

| Component | Tool |
|---|---|
| Language | Python 3.11 |
| Database | Supabase (PostgreSQL) |
| AI (Primary) | Gemini 2.0 Flash (free) |
| AI (Fallback) | OpenAI GPT-4o-mini (auto-switches if Gemini quota exhausted) |
| Output | .docx (python-docx) + .txt |
| Notifications | SMTP Email + Console |
| Input | Excel (.xlsx) |

---

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        # fill in your API keys
```

Run `supabase_schema.sql` in your Supabase SQL Editor to create the tables.

---

## File Descriptions

| File | Purpose |
|---|---|
| `config.py` | Loads `.env` variables, validates API keys based on LLM provider |
| `db.py` | Supabase client + CRUD operations for books, chapters, and logs |
| `input_handler.py` | Reads Excel input and creates book records in Supabase |
| `llm_service.py` | Gemini/OpenAI wrapper with auto-fallback and retry logic |
| `outline_stage.py` | Generates outline via LLM, gates on `notes_before` and `status_outline_notes` |
| `chapter_stage.py` | Generates chapters with context chaining (summaries of previous chapters), per-chapter gate |
| `compile_stage.py` | Compiles .docx and .txt, uploads to Supabase Storage, gates on `final_review_notes_status` |
| `notifications.py` | Sends email notifications and logs to Supabase at each gate |
| `main.py` | CLI orchestrator for full pipeline, individual stages, and book management |
| `supabase_schema.sql` | PostgreSQL schema: `books`, `chapters`, `notification_logs` tables |

---

## CLI Commands

```bash
python main.py --input input/books_input.xlsx        # Full pipeline
python main.py --stage outline --book-id <uuid>      # Run one stage
python main.py --stage chapters --book-id <uuid>
python main.py --stage compile --book-id <uuid>
python main.py --list                                # List all books
python main.py --delete <uuid>                       # Delete a book
python main.py --delete-all                          # Delete all books
```

---

## Results

Tested end-to-end with "The Future of Artificial Intelligence":

- **5 chapters** generated with context chaining (~44,000 characters)
- **`.docx`** (50 KB) with title page, TOC, formatted chapters
- **`.txt`** (44 KB) plain text version
- **All gates tested** — outline pause, chapter pause, compile pause
- **Email notifications** sent at each stage
- **Supabase Storage** — files uploaded to `book-outputs` bucket
- **LLM fallback** — Gemini quota exhausted, auto-switched to OpenAI
