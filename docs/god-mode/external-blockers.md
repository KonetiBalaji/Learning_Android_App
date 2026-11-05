# External release blockers

| Work | Exact input needed | Verification after input |
|---|---|---|
| Live AI | An authorized server-only API key provisioned directly into the deployment's secret store and the authorized model identifier | Run live generation and grounding checks and record accuracy by Easy, Medium, Hard and Mixed difficulty. **NOT VERIFIED** |
| Original branding | The approved Saras Modern and Heritage source assets with light and dark variants or approved usage guidance | Apply them to launcher, splash and headers. Check assets and screens. The named placeholder is in use. **NOT VERIFIED** |
| Production hosting | Access to the persistent Linux Docker host, a public DNS hostname routed to it, and a securely mounted storage key. Existing databases require their original key. | Verify public certificate issuance and run the smoke suite at the production URL. **NOT VERIFIED** |
| Play signing and store | Authorized Play upload signing material through protected local or CI configuration, Play Console access, operator identity and privacy contact, final public privacy and account deletion URLs, and the production backup-retention policy | Verify the distribution bundle against the authorized upload certificate and review final store declarations. **NOT VERIFIED** |
| Publication | Separate explicit approval to publish the reviewed Play release | Record the approved Play submission and track its result. **NOT VERIFIED** |

The separately reported 51-test core is archived as an unverified provenance claim. An exact source location and revision would enable an independent review if it is recovered. It is outside the dev test totals.
