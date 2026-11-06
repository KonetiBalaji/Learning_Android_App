# Student learning flow verification

The attached student-learning brief describes a curriculum product in addition to Saras's document study tools. This file tracks the brief against the current implementation. The existing Kotlin/Compose and FastAPI stack is retained. The proposed framework and vendor list is a suggested architecture, and this work adds the flow to the current app.

| Brief requirement | Current evidence or remaining work |
|---|---|
| Login and sign-up | Username/password and Google sign-in exist. Live Google sign-in and sign-out were verified for the private OAuth test audience. Email/password registration and sign-in now share the same account system as legacy usernames. Email identifiers are case insensitive and stored as keyed lookup digests. Email ownership verification and recovery are not part of this flow. Public OAuth verification remains open. |
| Grade, subject and chapter selection | The starter catalog offers Mathematics in grades 1 through 12, plus Grade 6 Science, English and Social Studies. It contains 22 authored lessons. Grade 6 Science, English and Social Studies each have a second chapter unlocked by mastering the first. Broader standards alignment and chapter coverage remain open. |
| Diagnostic quiz and feedback | The percentages, algebra, and geometry chapters each have three diagnostic questions. Correct answers advance the diagnostic. For a wrong answer, the coach shows the selected option before opening the worked example. Fractions and decimals have authored guidance for each wrong option. New attempts in fractions, decimals, and the six Grade 6 Science, English and Social Studies chapters have two diagnostic questions. Existing attempts in those chapters retain their original single-question path. Starter lessons outside Grade 6 have one diagnostic question. Broader diagnostic banks remain open. |
| Interactive practice and hints | Starter chapters support numeric and short-text answers, hints, equivalent fractions, and an alternate practice prompt after an incorrect answer. The five Grade 6 Mathematics chapters have practice banks of 21 fractions, 18 decimals, 14 percentages, 18 algebra, and 18 geometry questions. The added variants use exact arithmetic, preserve the initial two prompts for existing attempts, and remain separate from readiness items. The six Grade 6 Science, English and Social Studies chapters each offer five authored practice prompts. Provider-generated practice remains open. |
| Rewrite and evaluation | A student can explain the rule in their own words. A narrow checklist gives revision feedback. In all eleven Grade 6 chapters, it can ask a guiding question about the first missing concept. The Android 15 fractions test verifies that the hint appears after an incomplete explanation and that a revision can reach mastery. General AI writing assessment and automatic age- or interest-tailored coaching remain open. In fractions and decimals, students can manually select a soccer or gaming example while keeping the standard worked steps available. The selection is local to the coaching view. The Android 15 fractions regression switches and clears the themes and continues to mastery. |
| Mastery and chapter unlocking | Completing practice and the explanation checklist marks the lesson mastered and unlocks the next chapter. The app shows elapsed time and chapter status. New diagnostic attempts also show the observed correct-answer count after mastery. Older attempts without a complete count still support mastery and omit the score. This is chapter-level completion for the authored activity. Grade 6 Mathematics has a six-question fractions and decimals check and a separate 15-question check across all five starter chapters. Broader assessment coverage and calibrated confidence remain open. |
| Knowledge gaps and personalized path | Document practice already has adaptive recommendations. Curriculum ranks unfinished chapters by observed diagnostic misses, practice misses, and explanation revisions. Older diagnostics retain evidence of at most one known miss. Two or more recorded events are labeled Repeated difficulty. Teacher and parent reports prioritize the same topics and expose topic names without per-attempt counts or answers. The chapter list shows mastery progress and prioritizes chapters needing practice or already started. The grade subject menu offers one shortcut across subjects after the student starts learning. It prioritizes unlocked chapters needing review, then work in progress, then an available chapter in a subject with prior mastery. The Android 15 regression verifies that the shortcut resumes an active science diagnostic and reopens coaching after a wrong answer. AI-generated recommendations remain open. |
| Teacher and parent view | Students can issue a one-use teacher or parent invitation, and either account can revoke the link. The viewer sees chapter mastery by subject, a rolling seven-day summary, areas to practice, and an evidence-based recommendation. Invited roles describe the relationship chosen by the student. The dashboard also shows a completed Grade 6 Mathematics readiness score with topic counts. School/guardian identity verification, scheduled delivery, and a validated exam readiness prediction remain open. |
| Voice, animation, badges and dark mode | Mastered chapters award persistent account-scoped badges. The app follows Android dark mode, including login and the native launch theme. The curriculum coach can read its explanation aloud and reveal the worked example. In fractions and decimals, students can move forward and back through authored steps with a crossfade between them. Students can dictate rewrites or tutor questions and edit the transcript before submitting. The document tutor can read its latest answer aloud. A Saras tutor avatar stays in the header on curriculum and document tutor screens. Its mouth opens when on-device narration starts and closes when narration stops. AI-generated animated explanations remain open. |
| Provider and operations | Production AI credentials and evaluation, production hosting, public OAuth and authorized Play signing remain release gates. |

Curriculum progress is encrypted and scoped to the signed-in account. Account deletion removes it. The flow retains the current lesson and its result, rather than retaining free-text submissions. The document retention policy continues to apply to uploaded material.

Backend tests cover access control, invalid transitions, replay, worked coaching, equivalent answers, rewrite feedback, unlocking, and account deletion. The Android regression drives the Grade 6 fractions flow through the UI and opens the newly unlocked decimals chapter.

Verification for runtime commit `d3e9a29`: 111 backend tests passed. The debug and instrumentation APKs built, four Android unit tests passed, and lint reported zero errors and 15 warnings. The targeted Android 15 emulator regression passed through fractions mastery and the decimals unlock. [Docker HTTPS staging passed](https://github.com/KonetiBalaji/Learning_Android_App/actions/runs/42157314907). Staging exercises the existing HTTPS and document workflow. The curriculum transition is verified separately by the API and emulator tests above.


### Teacher and parent report boundary

An invitation expires after 15 minutes, is stored only as a digest, and must be given privately to its recipient. An account cannot redeem its own invitation. Reissuing or cancelling an invitation invalidates the earlier code for that role. The linked viewer receives only curriculum aggregates, chapter topics and the next practice recommendation. They cannot use the link to read uploaded materials, quiz answers, written responses or other account data. Either participant may remove a link. Account deletion removes the links and outstanding invitations.

The weekly report summarizes the last seven days of recorded curriculum activity. Earlier lesson records created before activity timestamps were introduced remain visible in all-time mastery and have no inferred date for weekly reporting. There is no automated email delivery or predictive exam score.

The teacher and parent checkpoint passed 131 backend tests and the targeted Android 15 run for invitation redemption and report access, dark mode, and mastery progression. The Android build and lint passed. The dashboard's access-control tests also verify cross-account denial, cancellation, expiry, replay protection, revocation and account deletion.

For a full Android device run, point the test runner at a second disposable instance of the same backend with `-e sharingPort <port>`. The sharing scenario creates and signs into multiple accounts. A separate fixture keeps its authentication requests from contending with other scenarios for the production login rate limit.


### Voice controls

Dictation uses Android's on-device recognizer on devices that support it. It requests microphone access only when the student taps Dictate. The transcript fills the editable field and is submitted only through the existing lesson or tutor action. If recognition or an offline voice is unavailable, typing and on-screen text remain available. Read-aloud selects an installed English voice that reports no network requirement. Leaving the screen or backgrounding the app ends the audio session.

[Android on-device recognition](https://developer.android.com/reference/android/speech/SpeechRecognizer) · [Android text-to-speech voice capabilities](https://developer.android.com/reference/android/speech/tts/Voice)

The voice checkpoint passed the Android 15 curriculum and document tutor instrumentation tests. The tests exercise the explanation reveal, the read-aloud button's completion or fallback path, and the presence of the dictation controls. They do not verify real microphone transcription or independently check the audio output. The updated Android 15 fractions regression also verifies forward and backward step navigation, hiding the example, and continuing through mastery.


### Readiness evidence

After mastering fractions and decimals, a student can start or resume a six-question held-out assessment. The server returns one question at a time, accepts an identical answer retry without advancing twice, rejects changed answers, and only returns the score and topic breakdown when complete. The result measures performance on these questions. It does not estimate exam outcomes. Predictions would require a broader assessment and validation against real exam outcomes. The completed aggregate is included in explicitly shared teacher and parent reports. The individual answers remain private, and account deletion removes the attempt.

The readiness checkpoint passed 133 backend tests, four Android unit tests, and an Android 15 flow that completed both lessons and scored six out of six on the readiness check. Lint reported zero errors and 15 warnings. The backend test also verifies a mixed result, topic totals, linked viewer access, and account deletion.


### Grade 6 Mathematics chapter sequence

The Grade 6 Mathematics path runs from fractions and decimals through percentages, introductory algebra, and triangle area. Each new chapter unlocks after mastery of the previous chapter. The three new chapters have three diagnostic questions apiece and can resume on the same question after reopening. A six-question assessment measures fractions and decimals, and a separate 15-question assessment measures all five chapters after they are mastered.


### Full Grade 6 Mathematics readiness check

The full check has three new, held-out questions per topic. It unlocks after mastering fractions, decimals, percentages, introductory algebra, and triangle area. Its attempt, score, and report are separate from the existing six-question check. A completed teacher or parent report can show both scores. It never includes a student's individual answers or an exam forecast.

### Grade 6 Science, English and Social Studies progression

Backend tests complete both chapters in each subject and verify that mastery does not unlock the second chapter for another account. The Android 15 emulator regression starts each subject from the Grade 6 menu, checks the locked button, masters the first chapter, and opens the second chapter's diagnostic after the catalog refreshes.
