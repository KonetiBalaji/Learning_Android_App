# Student learning flow verification

The attached student-learning brief describes a curriculum product in addition to Saras's document study tools. This file tracks the brief against the current implementation. The existing Kotlin/Compose and FastAPI stack is retained. The proposed framework and vendor list is a suggested architecture, and this work adds the flow to the current app.

| Brief requirement | Current evidence or remaining work |
|---|---|
| Login and sign-up | Username/password and Google sign-in exist. Live Google sign-in and sign-out were verified for the private OAuth test audience. Email/password registration and sign-in now share the same account system as legacy usernames. Email identifiers are case insensitive and stored as keyed lookup digests. Email ownership verification and recovery are not part of this flow. Public OAuth verification remains open. |
| Grade, subject and chapter selection | The starter catalog offers Mathematics in grades 1 through 12, plus Grade 6 Science, English and Social Studies. It contains 16 authored lessons. Broader standards alignment and chapter coverage remain open. |
| Diagnostic quiz and feedback | Each starter chapter has a diagnostic question. Correct answers advance to practice. Incorrect answers open a worked explanation and example. A broader diagnostic question bank remains open. |
| Interactive practice and hints | Starter chapters support numeric and short-text answers, hints, equivalent fractions, and an alternate practice prompt after an incorrect answer. This uses authored examples and exact arithmetic. |
| Rewrite and evaluation | A student can explain the rule in their own words. A narrow checklist gives revision feedback. General AI writing assessment and age- or interest-tailored coaching remain open. |
| Mastery and chapter unlocking | Completing practice and the explanation checklist marks the lesson mastered and unlocks the next chapter. The app shows elapsed time and chapter status. This is chapter-level completion for the authored activity. Broader mastery scoring and calibrated confidence remain open. |
| Knowledge gaps and personalized path | Document practice already has adaptive recommendations. Curriculum records diagnostic misses, practice misses, and explanation revisions. The chapter list shows mastery progress and prioritizes chapters needing practice or already started. Cross-subject and AI recommendations remain open. |
| Teacher and parent view | Students can issue a one-use teacher or parent invitation, and either account can revoke the link. The viewer sees chapter mastery by subject, a rolling seven-day summary, areas to practice, and an evidence-based recommendation. Invited roles describe the relationship chosen by the student. School/guardian identity verification, scheduled delivery, and a validated exam readiness prediction remain open. |
| Voice, animation, badges and dark mode | Mastered chapters award persistent account-scoped badges. The app follows Android dark mode, including login and the native launch theme. Voice and animation remain open. |
| Provider and operations | Production AI credentials and evaluation, production hosting, public OAuth and authorized Play signing remain release gates. |

Curriculum progress is encrypted and scoped to the signed-in account. Account deletion removes it. The flow retains the current lesson and its result, rather than retaining free-text submissions. The document retention policy continues to apply to uploaded material.

Backend tests cover access control, invalid transitions, replay, worked coaching, equivalent answers, rewrite feedback, unlocking, and account deletion. The Android regression drives the Grade 6 fractions flow through the UI and opens the newly unlocked decimals chapter.

Verification for runtime commit `d3e9a29`: 111 backend tests passed. The debug and instrumentation APKs built, four Android unit tests passed, and lint reported zero errors and 15 warnings. The targeted Android 15 emulator regression passed through fractions mastery and the decimals unlock. [Docker HTTPS staging passed](https://github.com/KonetiBalaji/Learning_Android_App/actions/runs/42157314907). Staging exercises the existing HTTPS and document workflow. The curriculum transition is verified separately by the API and emulator tests above.


### Teacher and parent report boundary

An invitation expires after 15 minutes, is stored only as a digest, and must be given privately to its recipient. An account cannot redeem its own invitation. Reissuing or cancelling an invitation invalidates the earlier code for that role. The linked viewer receives only curriculum aggregates, chapter topics and the next practice recommendation. They cannot use the link to read uploaded materials, quiz answers, written responses or other account data. Either participant may remove a link. Account deletion removes the links and outstanding invitations.

The weekly report summarizes the last seven days of recorded curriculum activity. Earlier lesson records created before activity timestamps were introduced remain visible in all-time mastery and have no inferred date for weekly reporting. There is no automated email delivery or predictive exam score.

The teacher and parent checkpoint passed 131 backend tests and the targeted Android 15 run for invitation redemption and report access, dark mode, and mastery progression. The Android build and lint passed. The dashboard's access-control tests also verify cross-account denial, cancellation, expiry, replay protection, revocation and account deletion.

For a full Android device run, point the test runner at a second disposable instance of the same backend with `-e sharingPort <port>`. The sharing scenario creates and signs into multiple accounts. A separate fixture keeps its authentication requests from contending with other scenarios for the production login rate limit.
