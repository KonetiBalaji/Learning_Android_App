"""Local exact-quote practice; provider boundary for future semantic generation."""
import random
import re


class GenerationError(ValueError):
    pass


def validate(questions: list[dict], passages: list[dict], count: int) -> list[dict]:
    if len(questions) != count:
        raise GenerationError(f"Expected {count} questions; received {len(questions)}.")
    sources = {p["id"]: p for p in passages}
    seen = set()
    for question in questions:
        prompt = question.get("prompt", "").strip()
        choices = question.get("choices", [])
        source = sources.get(question.get("source_id"))
        quote = question.get("quote", "").strip()
        answer = question.get("answer")
        normalized = [str(c).strip().casefold() for c in choices]
        normalized_prompt = re.sub(r"\s+", " ", prompt).casefold()
        if not prompt or normalized_prompt in seen:
            raise GenerationError("Missing or duplicate question.")
        if len(choices) not in (2, 4) or any(not c for c in normalized) or len(set(normalized)) != len(choices):
            raise GenerationError("Missing or duplicate answer choices.")
        if type(answer) is not int or not 0 <= answer < len(choices):
            raise GenerationError("Invalid answer.")
        if not source or not quote or quote not in source["text"] or not question.get("explanation", "").strip():
            raise GenerationError("Question lacks an exact source reference or explanation.")
        if question.get("type") not in ("multiple_choice", "true_false", "yes_no"):
            raise GenerationError("Unsupported question type.")
        seen.add(normalized_prompt)
    return questions


def generate_local(passages: list[dict], count: int, kind: str, difficulty: str) -> list[dict]:
    if difficulty not in ("easy", "mixed"):
        raise GenerationError("Local practice supports Easy or Mixed. Semantic difficulty needs the future AI provider.")
    candidates = []
    for passage in passages:
        words = list(re.finditer(r"\b[A-Za-z][A-Za-z-]{4,}\b", passage["text"]))
        if len(passage["text"].split()) >= 7 and words:
            word = max(words, key=lambda m: len(m.group()))
            candidates.append((passage, word))
    pool = sorted({word.group().lower() for _, word in candidates})
    random.SystemRandom().shuffle(candidates)
    questions, seen = [], set()
    for passage, word in candidates:
        quote = passage["text"]
        if quote.casefold() in seen:
            continue
        actual = word.group()
        others = [s for s in pool if s.casefold() != actual.casefold() and s.casefold() not in quote.casefold()]
        if len(others) < 3:
            continue
        rng = random.SystemRandom()
        if kind == "multiple_choice":
            choices = [actual] + rng.sample(others, 3)
            rng.shuffle(choices)
            prompt = 'Which word completes this exact passage?\n“' + quote[:word.start()] + "_____" + quote[word.end():] + '”'
            answer = choices.index(actual)
        else:
            positive = rng.choice([True, False])
            shown = quote if positive else quote[:word.start()] + rng.choice(others) + quote[word.end():]
            prompt = ('Does this exactly match the source passage?\n“' if kind == "yes_no" else 'True or false: this exactly matches the source passage.\n“') + shown + '”'
            choices = ["Yes", "No"] if kind == "yes_no" else ["True", "False"]
            answer = 0 if positive else 1
        questions.append({"id": f"q{len(questions)}", "prompt": prompt, "choices": choices, "answer": answer,
                          "type": kind, "source_id": passage["id"], "quote": quote,
                          "concept": passage["section_id"], "section_id": passage["section_id"], "difficulty": "easy", "page": passage["page"],
                          "explanation": f'The original passage says: “{quote}” Read it again and connect the missing word to its context.'})
        seen.add(quote.casefold())
        if len(questions) == count:
            break
    if len(questions) < count:
        raise GenerationError(f"This selection supports {len(questions)} distinct local questions. Choose fewer questions or more material.")
    return validate(questions, passages, count)


def public_question(question: dict) -> dict:
    visible = {k: v for k, v in question.items() if k not in ("answer", "explanation", "quote")}
    visible.setdefault("section_id", question["concept"])
    return visible
