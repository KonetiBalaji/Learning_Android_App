# Grade 8 Grammar sentence-parts explorer

## Scope

The exact `Grade 8 -> English -> Grammar` tutor route now includes an
application-owned interactive sentence model. The learner selects Subject, Verb or
Object in the complete sentence "The curious student solved the puzzle." The chosen
words receive a visible highlight and the card explains their grammatical role plus
a question the learner can use to check the classification.

The three actions and all text are curated Kotlin data. No provider response,
generated HTML/JavaScript, arbitrary coordinate instruction or upstream action
payload can change the scene. The selected state survives recomposition, buttons
carry explicit text state, and the sentence exposes a dynamic accessibility
description naming the highlighted words.

Selection is presentation-only: it makes no network request, submits no learner
answer, adds no coaching round, and awards no mastery. Unsupported subject/chapter
pairs do not receive this scene.

## Verification

`scripts/qa-sentence-explorer.ps1 -ResetTestAppData` ran against the dedicated
`LearnSmart_API36` emulator and explicitly isolated `scripted-english-qa` fixture.
It created a disposable account, selected Grade 8 English Grammar, entered tutoring
after a known wrong answer, verified the initial Subject state, selected Verb, and
verified both the role and question prompt. An authenticated session read proved the
state remained `tutor`, with zero coaching rounds and zero mastery score. The account
was deleted and app data cleared.

The inspected `artifacts/qa-sentence-explorer.png` shows the word "solved"
highlighted, readable selectors and explanations, and an unobstructed practice
button. The screenshot remains untracked QA evidence and is not packaged in the APK.

Unit tests verify exact route allowlisting and that the three non-overlapping parts
reconstruct the intended complete sentence. Android verification passed 129 JVM
tests with zero failures/skips plus lint and debug assembly. Backend regression
remained 451 passing with one existing Windows skip. The PowerShell harness and QA
fixture parsed without errors.

## Limits

This demonstrates subject/verb/object identification in one declarative sentence.
It does not cover clauses, passive voice, complements, multilingual grammar, broad
curriculum alignment, educator review, TalkBack traversal, a physical device, UAT,
or the remaining English chapters. TUT-05 remains partial.
