from __future__ import annotations

import hashlib
import random
import re
import uuid
from dataclasses import dataclass

from .schemas import Chapter
from .document_selection import resolve_chapters
from .document_errors import DocumentErrorCode, DocumentValidationError


NON_CONCEPT_WORDS = {
    'chapter', 'this', 'that', 'these', 'those', 'there', 'their', 'which', 'while',
    'when', 'where', 'with', 'from', 'into', 'through', 'under', 'outside', 'inside',
    'other', 'many', 'what', 'have', 'has', 'help', 'helps',
}


def grounded_concept_term(sentence: str) -> str:
    words = re.findall(r'[A-Za-z]{4,}', sentence)
    substantive = [word for word in words if word.casefold() not in NON_CONCEPT_WORDS]
    if not substantive:
        raise DocumentValidationError(DocumentErrorCode.INSUFFICIENT_MATERIAL,
                                      'A source sentence has no usable study term')
    return substantive[0]


@dataclass(frozen=True)
class GeneratedQuestion:
    prompt: str
    options: list[str]
    correct_option: str
    explanation: str
    source_reference: str
    chapter_id: str | None = None
    concept: str | None = None


def generate_grounded_questions(text: str, chapters: list[Chapter], selected_ids: list[str], count: int) -> list[GeneratedQuestion]:
    selected = resolve_chapters(text, chapters, selected_ids)
    candidates: list[tuple[Chapter, str, int, int]] = []
    for chapter in selected:
        chapter_text = text[chapter.start_character : chapter.end_character]
        for match in re.finditer(r"[^.!?]+[.!?](?=\s|$)", chapter_text, re.DOTALL):
            sentence = re.sub(r"\s+", " ", match.group()).strip()
            if 45 <= len(sentence) <= 360:
                candidates.append((chapter, sentence, chapter.start_character + match.start(),
                                   chapter.start_character + match.end()))
    unique: list[tuple[Chapter, str, int, int]] = []
    seen: set[str] = set()
    for chapter, sentence, start, end in candidates:
        fingerprint = hashlib.sha256(sentence.lower().encode()).hexdigest()
        if fingerprint not in seen:
            seen.add(fingerprint)
            unique.append((chapter, sentence, start, end))
    if len(unique) < 4:
        raise DocumentValidationError(DocumentErrorCode.INSUFFICIENT_MATERIAL, "The selected material needs at least four clear sentences before a reliable quiz can be generated")
    rng = random.Random(hashlib.sha256((text + ",".join(selected_ids)).encode()).hexdigest())
    rng.shuffle(unique)
    output: list[GeneratedQuestion] = []
    for position, (chapter, answer, source_start, source_end) in enumerate(unique[:count]):
        # Credential-free QA uses exact-text recall, not a fabricated semantic assessment.
        term = grounded_concept_term(answer)
        distractors = list(dict.fromkeys(word for _, sentence, _, _ in unique for word in re.findall(r'[A-Za-z]{4,}', sentence)
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
                source_reference=f"{chapter.title} (source characters {source_start}-{source_end})",
                chapter_id=chapter.id,
                concept=term,
            )
        )
    if len(output) != count:
        raise DocumentValidationError(DocumentErrorCode.INSUFFICIENT_MATERIAL, 'The selected material cannot support the requested number of distinct questions; select more material or fewer questions')
    return output


def question_id() -> str:
    return str(uuid.uuid4())
