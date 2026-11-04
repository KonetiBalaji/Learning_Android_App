# Saras Play Store release draft

**Title** Saras Study Companion

**Short description** Turn your study documents into quizzes, flashcards, and offline practice.

**Full description**

Upload a PDF, DOCX, or text file and organize practice around its chapters and pages. Correct uncertain scanned text before using it for study.

Answer questions one at a time and check the passage behind each answer. Review mistakes, choose your next practice session, and revisit flashcards as they come due. Use semantic search or the document tutor to find related passages in your material.

Save confirmed material before going offline. Saras can generate local practice on the device, preserve your answers, and sync completed sessions when you reconnect.

**Release notes**

Initial release with document upload and OCR review, source-based quizzes, progress and adaptive practice, spaced review, document search and tutor excerpts, and encrypted offline study with progress synchronization.

**Screenshots to capture**

Use the sample material and a disposable account. Capture the chapter selector, source feedback, OCR correction, flashcard review, and offline results. Use the original Saras branding once available.

## Privacy and Data safety draft

Saras collects the username and password supplied during account creation and sign-in. The backend stores a salted password hash and expiring sessions. User-selected documents and associated study records are processed for OCR, retrieval, practice, tutor excerpts, flashcards, and progress. Offline copies and saved answers use encrypted device storage. Production traffic uses HTTPS. The default local-practice deployment processes study material on the configured Saras server and does not call an AI provider.

Draft Data safety categories to confirm against the actual production environment are user IDs, files and documents, and app activity including quiz answers, progress, and tutor questions. Account data is necessary for synced features. Document submission and tutor use are optional. The shipped app has no advertising SDK. Review the production host, backup policy, telemetry and any later AI provider arrangement before submitting the final declaration.

Documents and associated server records expire after 30 days. Users can delete individual documents and their related records or delete their account from Settings. The deployed `/delete-account` page supports deletion without the app. The server revokes existing sessions and removes associated records. Disconnected copies on another device are reconciled on reconnect or expire at the original document retention deadline.

Before publishing the public privacy policy, fill in the operator identity, privacy contact, production hostname, and actual backup-retention period. The public deletion URL must be reachable without the app. [Google Play account deletion requirements](https://support.google.com/googleplay/android-developer/answer/13327111)

## Build and signing

Use an authorized Play upload key and inject `SARAS_KEYSTORE_PATH`, `SARAS_KEYSTORE_PASSWORD`, `SARAS_KEY_ALIAS`, and `SARAS_KEY_PASSWORD` into the build environment from local secret storage or protected CI secrets. Run `gradlew bundleRelease` inside `android` and verify the resulting signature against the authorized upload certificate. Use a greater version code for each submitted update. Keep the original logos, public URLs, Play Console metadata, and publication approval as release gates. [Google Play target API requirements](https://support.google.com/googleplay/android-developer/answer/11926878)
