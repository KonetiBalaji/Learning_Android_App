"""Authored assessment kept separate from diagnostic and coached practice."""

ASSESSMENT_ID = "grade6-math"
REQUIRED = {"fractions", "decimals"}
QUESTIONS = (
    ("fractions", "What is 2/9 + 4/9?", ("6/18", "2/3", "4/9", "8/9"), 1),
    ("fractions", "One trail segment is 1/8 km and the next is 3/8 km. How far in all?",
     ("1/2 km", "1/4 km", "5/8 km", "3/8 km"), 0),
    ("fractions", "Which expression shows how to add 2/7 and 3/7?",
     ("5/14", "6/7", "2/14", "(2 + 3)/7"), 3),
    ("decimals", "What is 0.35 + 0.6?", ("0.41", "0.65", "0.95", "6.35"), 2),
    ("decimals", "A rope has sections of 1.8 m and 0.27 m. What is the total length?",
     ("1.97 m", "2.07 m", "1.827 m", "2.17 m"), 1),
    ("decimals", "Which is equivalent to 0.4 + 0.08?", ("48 hundredths", "12 hundredths", "48 tenths", "8 hundredths"), 0),
)


def snapshot(attempt):
    index = len(attempt["answers"])
    result = {"id": ASSESSMENT_ID, "index": index, "total": len(QUESTIONS), "complete": index == len(QUESTIONS)}
    if not result["complete"]:
        _, prompt, choices, _ = QUESTIONS[index]
        result.update(prompt=prompt, choices=choices)
    else:
        score = {chapter: {"correct": 0, "total": 0} for chapter in ("fractions", "decimals")}
        for (chapter, _, _, correct), chosen in zip(QUESTIONS, attempt["answers"]):
            score[chapter]["total"] += 1
            score[chapter]["correct"] += int(correct == chosen)
        result.update(correct=sum(item["correct"] for item in score.values()), by_chapter=score)
    return result
