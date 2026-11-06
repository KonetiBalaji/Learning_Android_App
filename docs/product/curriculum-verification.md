# Student learning flow verification

The attached student-learning brief describes a curriculum product in addition to Saras's document study tools. This file tracks the brief against the current implementation. The existing Kotlin/Compose and FastAPI stack is retained. The proposed framework and vendor list is a suggested architecture, and this work adds the flow to the current app.

| Brief requirement | Current evidence or remaining work |
|---|---|
| Login and sign-up | Username/password and Google sign-in exist. Live Google sign-in and sign-out were verified for the private OAuth test audience. Email/password registration and sign-in now share the same account system as legacy usernames. Email identifiers are case insensitive and stored as keyed lookup digests. Email ownership verification and recovery are not part of this flow. Public OAuth verification remains open. |
| Grade, subject and chapter selection | Android and the authenticated curriculum API now offer Grade 6 Mathematics, with authored fractions and decimals chapters. Other grades and subjects need real curriculum material before they can be enabled. |
| Diagnostic quiz and feedback | Each starter chapter has a diagnostic question. Correct answers advance to practice. Incorrect answers open a worked explanation and example. A broader diagnostic question bank remains open. |
| Interactive practice and hints | Starter chapters support numeric answers, hints, equivalent fractions, and another worked example after an incorrect answer. This uses authored examples and exact arithmetic. |
| Rewrite and evaluation | A student can explain the rule in their own words. A narrow checklist gives revision feedback. General AI writing assessment and age- or interest-tailored coaching remain open. |
| Mastery and chapter unlocking | Completing practice and the explanation checklist marks the lesson mastered and unlocks the next chapter. The app shows elapsed time and chapter status. This is chapter-level completion for the authored activity. Broader mastery scoring and calibrated confidence remain open. |
| Knowledge gaps and personalized path | Document practice already has adaptive recommendations. Curriculum paths currently use an authored prerequisite. Curriculum gap detection and personalized recommendations remain open. |
| Teacher and parent view | Separate roles, verified student linking, cross-account access controls, progress reports and exam readiness remain open. |
| Voice, animation, badges and dark mode | Mastered chapters award persistent account-scoped badges. The app follows Android dark mode, including login and the native launch theme. Voice and animation remain open. |
| Provider and operations | Production AI credentials and evaluation, production hosting, public OAuth and authorized Play signing remain release gates. |

Curriculum progress is encrypted and scoped to the signed-in account. Account deletion removes it. The flow retains the current lesson and its result, rather than retaining free-text submissions. The document retention policy continues to apply to uploaded material.

Backend tests cover access control, invalid transitions, replay, worked coaching, equivalent answers, rewrite feedback, unlocking, and account deletion. The Android regression drives the Grade 6 fractions flow through the UI and opens the newly unlocked decimals chapter.

Verification for runtime commit `d3e9a29`: 111 backend tests passed. The debug and instrumentation APKs built, four Android unit tests passed, and lint reported zero errors and 15 warnings. The targeted Android 15 emulator regression passed through fractions mastery and the decimals unlock. [Docker HTTPS staging passed](https://github.com/KonetiBalaji/Learning_Android_App/actions/runs/42157314907). Staging exercises the existing HTTPS and document workflow. The curriculum transition is verified separately by the API and emulator tests above.
