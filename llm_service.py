"""
LLM wrapper supporting Gemini (free) and OpenAI (fallback).
Provides functions for:
  - Outline generation
  - Chapter writing (with context from previous chapters)
  - Chapter summarization (for context chaining)
"""

import config
import google.generativeai as genai
from openai import OpenAI

# Initialize the correct LLM client
if config.LLM_PROVIDER == "gemini":
    genai.configure(api_key=config.GEMINI_API_KEY)
    _gemini_model = genai.GenerativeModel(config.GEMINI_MODEL)

elif config.LLM_PROVIDER == "openai":
    _openai_client = OpenAI(api_key=config.OPENAI_API_KEY)

def _call_llm(prompt: str, max_tokens: int = 4000) -> str:
    """
    Call the configured LLM provider and return the text response.
    Supports both Gemini and OpenAI.
    """
    try:
        if config.LLM_PROVIDER == "gemini":
            response = _gemini_model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=0.7,
                ),
            )
            return response.text.strip()

        elif config.LLM_PROVIDER == "openai":
            response = _openai_client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()

        else:
            raise ValueError(f"Unknown LLM provider: {config.LLM_PROVIDER}")
    except Exception as e:
        print(f"[ERROR] LLM call failed: {e}")
        raise


# Outline Generation
def generate_outline(title: str, notes_before: str, notes_after: str | None = None) -> str:
    """
    Generate a structured book outline using the LLM.

    Args:
        title: Book title
        notes_before: Editor notes guiding outline creation (required)
        notes_after: Optional post-first-draft notes for outline refinement

    Returns:
        Structured outline text with numbered chapters and descriptions
    """
    prompt = f"""You are an expert book editor and author. Generate a detailed book outline.

BOOK TITLE: {title}

EDITOR'S NOTES AND GUIDELINES:
{notes_before}
"""
    
    if notes_after:
        prompt += f"""ADDITIONAL EDITOR FEEDBACK (use this to refine and improve the outline):{notes_after}"""

    prompt += """
        REQUIREMENTS:
        1. Create a structured outline with 5-8 chapters (unless notes specify otherwise).
        2. For each chapter, provide:
        - Chapter number and title
        - A 2-3 sentence description of what the chapter covers
        - Key topics/sections within the chapter
        3. Include an Introduction and Conclusion chapter.
        4. Make the outline logical, flowing, and comprehensive.

        FORMAT your response exactly like this:
        Chapter 1: [Title]
        Description: [2-3 sentences about what this chapter covers]
        Key Topics: [comma-separated list of topics]

        Chapter 2: [Title]
        Description: [2-3 sentences]
        Key Topics: [topics]

        ... and so on for each chapter.
"""

    print(f"  [LLM] Generating outline for '{title}'...")
    return _call_llm(prompt, max_tokens=3000)

# Chapter Generation
def generate_chapter(
    book_title: str,
    outline: str,
    chapter_number: int,
    chapter_title: str,
    previous_summaries: list[str],
    chapter_notes: str | None = None,
) -> str:
    """
    Generate a full chapter using the outline and context from previous chapters.

    Args:
        book_title: Title of the book
        outline: Full book outline
        chapter_number: Which chapter to write (1-indexed)
        chapter_title: Title of this chapter
        previous_summaries: List of summaries from chapters 1 to N-1
        chapter_notes: Optional editor notes for this specific chapter

    Returns:
        Full chapter text
    """
    # Build context from previous chapters
    context_block = ""
    if previous_summaries:
        context_block = "\nPREVIOUS CHAPTER SUMMARIES (for continuity):\n"
        for i, summary in enumerate(previous_summaries, 1):
            context_block += f"Chapter {i} Summary: {summary}\n"

    notes_block = ""
    if chapter_notes:
        notes_block = f"\nEDITOR'S NOTES FOR THIS CHAPTER:\n{chapter_notes}\n"

    prompt = f"""You are an expert author writing a book.
        BOOK TITLE: {book_title}
        FULL BOOK OUTLINE:
        {outline}
        {context_block}
        {notes_block}

        YOUR TASK:
        Write Chapter {chapter_number}: {chapter_title}

        REQUIREMENTS:
        1. Write a complete, well-structured chapter (approximately 1500-2500 words).
        2. Maintain consistency with previous chapters (use the summaries for context).
        3. Follow the outline's description and key topics for this chapter.
        4. Use clear headings and subheadings within the chapter.
        5. Write in an engaging, professional tone appropriate for the book's subject.
        6. Include smooth transitions from the previous chapter's content.
        7. End with a natural lead-in to the next chapter (if applicable).

        Write the full chapter now:
"""

    print(f"  [LLM] Generating Chapter {chapter_number}: {chapter_title}...")
    return _call_llm(prompt, max_tokens=4000)


# Chapter Summarization
def summarize_chapter(chapter_content: str) -> str:
    """
    Generate a concise summary of a chapter for context chaining.

    This summary will be passed to the LLM when generating subsequent chapters
    to maintain narrative continuity across the book.

    Returns:
        A 3-5 sentence summary of the chapter's key points.
    """
    prompt = f"""Summarize the following book chapter in 3-5 sentences.
                Focus on the main arguments, key points, and any conclusions.
                This summary will be used to provide context when writing the next chapter.

            CHAPTER CONTENT:
            {chapter_content}

            CONCISE SUMMARY:"""

    print(f"  [LLM] Summarizing chapter...")
    return _call_llm(prompt, max_tokens=500)
