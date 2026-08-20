from __future__ import annotations

import hashlib
import random
import re
import uuid
from dataclasses import dataclass

from .schemas import Chapter


@dataclass(frozen=True)
class GeneratedQuestion:
    prompt: str
    options: list[str]
    correct_option: str
    explanation: str
    source_reference: str


def generate_grounded_questions(text: str, chapters: list[Chapter], selected_ids: list[str], count: int) -> list[GeneratedQuestion]:
    selected = [chapter for chapter in chapters if chapter.id in selected_ids]
    if not selected:
        raise ValueError("Select at least one valid chapter")
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
        distractors = [sentence for _, sentence in unique if sentence != answer]
        rng.shuffle(distractors)
        options = [answer, *distractors[:3]]
        rng.shuffle(options)
        output.append(
            GeneratedQuestion(
                prompt=f"Which statement is directly supported by {chapter.title}?",
                options=options,
                correct_option=answer,
                explanation=f"This is stated in the selected source material. Review the supporting passage before continuing.",
                source_reference=f"{chapter.title} (source characters {chapter.start_character}-{chapter.end_character})",
            )
        )
    return output


def question_id() -> str:
    return str(uuid.uuid4())
