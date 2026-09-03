from __future__ import annotations

import hashlib
import random
import re
import uuid
from dataclasses import dataclass

from .schemas import Chapter
from .document_selection import resolve_chapters


@dataclass(frozen=True)
class GeneratedQuestion:
    prompt: str
    options: list[str]
    correct_option: str
    explanation: str
    source_reference: str


def generate_grounded_questions(text: str, chapters: list[Chapter], selected_ids: list[str], count: int) -> list[GeneratedQuestion]:
    selected = resolve_chapters(text, chapters, selected_ids)
    candidates: list[tuple[Chapter, str]] = []
    for chapter in selected:
        chapter_text = text[chapter.start_character : chapter.end_character]
        sentences = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", chapter_text))
        candidates.extend((chapter, sentence.strip()) for sentence in sentences if 45 <= len(sentence.strip()) <= 360)
    unique: list[tuple[Chapter, str]] = []
    seen: set[str] = set()
    for chapter, sentence in candidates:
        fingerprint = hashlib.sha256(sentence.lower().encode()).hexdigest()
        if fingerprint not in seen:
            seen.add(fingerprint)
            unique.append((chapter, sentence))
    if len(unique) < 4:
        raise ValueError("The selected material needs at least four clear sentences before a reliable quiz can be generated")
    rng = random.Random(hashlib.sha256((text + ",".join(selected_ids)).encode()).hexdigest())
    rng.shuffle(unique)
    output: list[GeneratedQuestion] = []
    for position, (chapter, answer) in enumerate(unique[:count]):
        # Credential-free QA uses exact-text recall, not a fabricated semantic assessment.
        term = max(re.findall(r'[A-Za-z]{4,}', answer), key=len)
        distractors = list(dict.fromkeys(word for _, sentence in unique for word in re.findall(r'[A-Za-z]{4,}', sentence)
                                        if word.casefold() != term.casefold()))
        rng.shuffle(distractors)
        options = [term, *distractors[:3]]
        if len(options) != 4:
            continue
        rng.shuffle(options)
        output.append(
            GeneratedQuestion(
                prompt=f'Which word completes this exact sentence from the selected text? "{answer.replace(term, "____", 1)}"',
                options=options,
                correct_option=term,
                explanation=f'The source sentence is: {answer}',
                source_reference=f"{chapter.title} (source characters {chapter.start_character}-{chapter.end_character})",
            )
        )
    if len(output) != count:
        raise ValueError('The selected material cannot support the requested number of distinct questions; select more material or fewer questions')
    return output


def question_id() -> str:
    return str(uuid.uuid4())
