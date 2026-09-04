# Progress persistence and account-isolation QA

PROG-01 uses only the authenticated backend progress snapshot. Subject cards show
the mean completion of chapters that the learner has actually assessed and label
that scope as `assessed progress`; subjects without an assessment say
`No assessment yet`. Chapter cards use the corresponding backend chapter score.
No baseline percentage is embedded in the Android catalog.

`scripts/qa-account-switch.ps1 -ResetTestAppData` now verifies this boundary on
the dedicated `LearnSmart_API36` emulator and isolated deterministic QA server.
It creates two synthetic accounts, assigns different interests, and seeds a
completed assessed chapter only for the first account through an authenticated
QA-only endpoint. The Android UI then proves:

- the second account shows no assessed progress and cannot see the first account's
  100% value;
- after sign-out and password sign-in, the first account shows 100% Mathematics
  assessed progress from its server record;
- after forced app stop and restart, that same authenticated progress is restored;
- each account still exposes only its own saved interest; and
- both disposable accounts are deleted and app data is cleared in the successful run.

The 2026-09-04 run exited successfully. Visual inspection of
`artifacts/qa-account-progress.png` confirms the full Mathematics progress bar,
100% label, and `No assessment yet` on unassessed subjects without clipping or
ambiguous all-curriculum wording. Backend regression separately covers owner and
grade filtering, while the earlier mastery-resume scenario proves a real completed
diagnostic produces the same backend-derived 100% chapter display.

This is deterministic emulator QA, not educational validation or user acceptance.
Physical-device testing, TalkBack review, approved curriculum coverage and explicit
UAT remain open.
