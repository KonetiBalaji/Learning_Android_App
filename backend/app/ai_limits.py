"""Hard response-size ceilings for every paid provider request."""

# Large enough for at most twenty bounded document questions, but finite so a
# malformed/provider-divergent response cannot consume an unbounded completion.
DOCUMENT_GENERATION_OUTPUT_TOKENS = 16_384

# Three diagnostic items include explanations, examples, hints, and practice.
DIAGNOSTIC_GENERATION_OUTPUT_TOKENS = 8_192

# Independent audits return compact structured decisions rather than lessons.
REVIEW_OUTPUT_TOKENS = 4_096

# One learner-facing lesson, rewrite assessment, practice item, or chat reply.
TUTOR_OUTPUT_TOKENS = 2_048
