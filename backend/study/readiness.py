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


def snapshot(attempt, assessment=ASSESSMENT_ID):
    _, questions = ASSESSMENTS[assessment]
    index = len(attempt["answers"])
    result = {"id": assessment, "index": index, "total": len(questions), "complete": index == len(questions)}
    if not result["complete"]:
        _, prompt, choices, _ = questions[index]
        result.update(prompt=prompt, choices=choices)
    else:
        score = {chapter: {"correct": 0, "total": 0} for chapter, _, _, _ in questions}
        for (chapter, _, _, correct), chosen in zip(questions, attempt["answers"]):
            score[chapter]["total"] += 1
            score[chapter]["correct"] += int(correct == chosen)
        result.update(correct=sum(item["correct"] for item in score.values()), by_chapter=score)
    return result

# The full check uses a separate question bank so the earlier check does not teach its answers.
FULL_ID = "grade6-math-full"
FULL_REQUIRED = REQUIRED | {"percentages", "grade6-algebra", "grade6-geometry"}
FULL_QUESTIONS = (
    ("fractions", "What is 3/10 + 4/10?", ("7/20", "7/10", "12/10", "1/10"), 1),
    ("fractions", "What is 1/6 + 4/6?", ("5/12", "4/6", "5/6", "1"), 2),
    ("fractions", "A jug contains 2/5 L. You add 1/5 L. How much is in the jug?", ("3/5 L", "3/10 L", "2/5 L", "2/25 L"), 0),
    ("decimals", "What is 0.72 + 0.09?", ("0.73", "0.79", "1.62", "0.81"), 3),
    ("decimals", "Find the sum of 2.6 and 0.38.", ("2.44", "2.98", "2.638", "3.08"), 1),
    ("decimals", "Which number equals 0.5 + 0.27?", ("0.32", "0.57", "0.77", "0.527"), 2),
    ("percentages", "What is 40% of 45?", ("18", "20", "25", "40"), 0),
    ("percentages", "Which fraction is equal to 75%?", ("1/4", "3/5", "7/10", "3/4"), 3),
    ("percentages", "A club has 90 members. Ten percent are new. How many are new?", ("8", "9", "10", "81"), 1),
    ("grade6-algebra", "Solve y + 9 = 21.", ("9", "11", "12", "30"), 2),
    ("grade6-algebra", "What is 5n when n equals 3?", ("15", "8", "53", "2"), 0),
    ("grade6-algebra", "Which equation means a number plus 7 equals 20?", ("n - 7 = 20", "7n = 20", "n + 20 = 7", "n + 7 = 20"), 3),
    ("grade6-geometry", "A triangle has base 9 cm and perpendicular height 4 cm. What is its area?",
     ("13 cm²", "18 cm²", "36 cm²", "72 cm²"), 1),
    ("grade6-geometry", "A triangle has area 24 m² and base 8 m. What is its perpendicular height?",
     ("3 m", "4 m", "6 m", "12 m"), 2),
    ("grade6-geometry", "A triangle and a parallelogram have the same base and perpendicular height. The parallelogram has area 30 cm². What is the triangle's area?",
     ("15 cm²", "30 cm²", "45 cm²", "60 cm²"), 0),
)

ASSESSMENTS = {
    ASSESSMENT_ID: (REQUIRED, QUESTIONS),
    FULL_ID: (FULL_REQUIRED, FULL_QUESTIONS),
}
