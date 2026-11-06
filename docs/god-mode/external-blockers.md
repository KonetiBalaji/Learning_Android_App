# External release blockers

| Work | Exact input needed | Verification after input |
|---|---|---|
| Live AI | An authorized server-only API key provisioned directly into the deployment's secret store and the authorized model identifier | Run live generation and grounding checks and record accuracy by Easy, Medium, Hard and Mixed difficulty. Verify live curriculum coaching, age and interest adaptation, practice generation, and written assessment. **NOT VERIFIED** |
| Exam-readiness prediction | Authorized, de-identified paired practice results and actual exam outcomes for the target curriculum | Evaluate prediction accuracy and calibration on held-out outcomes. The current readiness checks report observed assessment scores. **NOT VERIFIED** |
| Physical-device voice | A physical Android test device with an on-device recognizer that can connect to its speech service. The QA app and test APK now install on the Android 13 phone, and the automated fractions test passed. Its recognizer reported that it could not connect to the speech service. | Verify active recording cancellation and microphone transcription with disposable lesson data. The tester confirmed audible read-aloud on the Android 13 phone. The emulator verifies permission denial and cleanup of pending dictation controls. **NOT VERIFIED** |
| Original branding | The approved Saras Modern and Heritage source assets with light and dark variants or approved usage guidance | Apply them to launcher, splash and headers. Check assets and screens. The named placeholder is in use. **NOT VERIFIED** |
| Production hosting | Access to the persistent Linux Docker host, a public DNS hostname routed to it, a securely mounted storage key, and the production backup location and retention policy. Existing databases require their original key. | Verify public certificate issuance, run the smoke suite at the production URL, and rehearse recovery with a production backup in an isolated environment. **NOT VERIFIED** |
| Play signing and store | Authorized Play upload signing material through protected local or CI configuration, Play Console access, operator identity and privacy contact, final public privacy and account deletion URLs, and the production backup-retention policy | Verify the distribution bundle against the authorized upload certificate and review final store declarations. **NOT VERIFIED** |
| Public Google sign-in | Access to the Saras Google Cloud project, the intended production OAuth audience and consent configuration, the public site origin, and the Play app signing certificate fingerprint | Verify public OAuth and sign-in on the distributed build. Verify the implemented Google web account deletion flow on the authorized public HTTPS origin before distribution. Private debug sign-in was verified with one test account. |
| Publication | Separate explicit approval to publish the reviewed Play release | Record the approved Play submission and track its result. **NOT VERIFIED** |

## Public release handoff

Intake checked against dev at `2cf13dd`. The referenced Gmail artwork was not available through the connected account search, and no approved artwork was found in the repository or project working files. The repository lists no Actions secret names. That check does not establish whether secrets exist in a deployment store.

Provide the inputs in release order:

1. **Branding:** Re-supply the original Modern and Heritage files, or give an accessible location. Specify light/dark variants or approved placement for launcher, splash and headers.
2. **Live AI:** Provide the deployment target or secret store location and the authorized model identifier. Have the deployment owner provision the authorized server-only key there and confirm provisioning. No key value is needed in the handoff.
3. **Production:** Provide the host access route, public hostname with DNS routed to the host, and confirmation of the mounted storage key and whether the deployment uses an existing database. Confirm that the host can obtain a public TLS certificate.
4. **Play:** Provide access to the app in Play Console, protected upload signing configuration, the authorized upload certificate SHA-256 fingerprint for comparison, operator identity, privacy contact, final public privacy and deletion URLs, and the production backup retention policy.

After review, publication would require separate explicit approval identifying the verified bundle version and intended Play release track. This preparation ends before submission.

The separately reported 51-test core is archived as an unverified provenance claim. An exact source location and revision would enable an independent review if it is recovered. It is outside the dev test totals.
