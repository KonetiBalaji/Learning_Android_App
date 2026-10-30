# OCR, semantic retrieval, and adaptive practice

## Local OCR with review

Image-only PDF pages and short native headers over image bodies are rasterized locally with PDFium and recognized with RapidOCR. No document is sent to an OCR service or language model. Prepare public model weights before serving uploads:

```powershell
.venv/Scripts/python scripts/prepare-models.py
.venv/Scripts/python scripts/prepare-models.py --verify
```

The script records local public-model hashes. `STUDY_MODEL_DIR` selects the ignored cache. `STUDY_MODELS_OFFLINE=true` prevents the semantic model from downloading missing files at runtime.

OCR below the default 0.98 review threshold produces `needs_review`. This is a recognition score, **not an accuracy percentage**. The app displays the actual original raster with pinch/drag inspection, then allows correction and confirmation. An unreadable page may have an empty candidate and no passages; it never receives invented study text. Quizzes, search, and adaptive practice cannot use outstanding uncertain transcription. Higher-score OCR remains inspectable through the original-page source link.

Corrections increment a source revision, checked again before quiz persistence. Source text cannot be silently changed beneath existing quiz citations. Identical confirmed-page retries are idempotent. Candidates and original review images are encrypted and linked to the document's ownership, retention, and deletion.

Bounds: 50 MB upload; 2 million extracted/confirmed characters; 20,000 characters per OCR page; 50 OCR pages per upload; bounded preview dimensions/bytes; one PDF worker per API process; a maximum 180-second timeout; a 2 GiB parser-process memory ceiling. The memory guard is selectively reused from remote commit `448d2e9`. A disposable worker verifies that allocation above a smaller test ceiling is rejected. POSIX platforms without address-space limits retain process/time/output bounds and still need container limits.

## Real semantic search

The local `BAAI/bge-small-en-v1.5` model encodes source passages and queries as dense vectors using FastEmbed. Segments are bounded to 800 characters. Normalized vectors and source references are encrypted in the document store; source fingerprints invalidate stale indexes. Search scores only the passages permitted by the owner's chapter/page selection. Returned quotes are exact source substrings. A small exact-term tie-breaker resolves close semantic matches without replacing embeddings with keyword search.

The 0.64 cutoff was calibrated on the small English biology fixture in `shared/semantic-evaluation.json`. An initial 0.65 gate rejected “cell power factory” at 0.6486 despite ranking the correct source first. That diagnostic was added to calibration; the unchanged holdout set was rerun after adjustment:

```powershell
.venv/Scripts/python scripts/evaluate-semantic.py
```

Observed result: **10/10 calibration and 12/12 holdout** retrieval cases passed. This is limited retrieval evidence, not a general educational-accuracy or answer-entailment benchmark and not live OpenAI validation. Queries below the cutoff return no matches. Semantic study topics restrict quiz generation to matched passages. Insufficient distinct questions are reported rather than invented.

## Adaptive next practice

The recommendation considers up to five recent completed sessions for the same document. The latest answer to a distinct source question replaces earlier retry evidence rather than inflating the count. It prioritizes a lower-confidence source section or an unseen section and sizes the focused session to material that supports questions. Easy/Medium/Hard recommendations use observed response counts. Local passage recall remains explicitly Easy; live AI difficulty quality is still **NOT VERIFIED**.

The device flow starts the recommended quiz and preserves access to original results/history, mistakes, flashcards, and spaced review.

## Verification scope

- The integrated pre-tutor backend suite passed **62 tests**. The subsequent full run passed **70 tests**: those 62, one real memory-guard probe, and seven prepared tutor-validation tests. The latter do not imply a completed chat API/UI.
- **2 Android 15 emulator flows passed:** the expanded ten-question/semantic/adaptive/flashcard flow, and image-only PDF → original-page review → corrected transcription → quiz.
- JVM tests, APK assembly, and lint passed.
- A real local OCR smoke recognized three expected biology terms and scored 0.96105, correctly requiring review. Full-page OCR accuracy is not claimed.
- Prepared tutor-validation helpers are not yet an integrated chat feature until the API and Android flow are wired and verified.
