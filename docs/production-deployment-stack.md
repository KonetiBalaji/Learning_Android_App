# Host-neutral HTTPS deployment stack

`deploy/compose.production.yml` runs the reviewed backend image behind an Nginx
TLS boundary. Only HTTPS is published; the API port remains private on the Compose
network. Both containers use read-only root filesystems, no-new-privileges and
bounded writable tmpfs mounts. Learner state lives only in the explicitly
pre-created external runtime volume.

Copy `deploy/.env.production.example` outside the repository and replace every
placeholder through the chosen host's secret/configuration facility. Never commit
the populated file. The TLS directory must contain `fullchain.pem` and
`privkey.pem`, owned and renewed by the host/operator. Set the backend image to an
immutable reviewed digest and the release revision to its exact source commit.

The proxy accepts TLS 1.2/1.3, caps the complete multipart request at 50 MiB plus
the application's fixed 256 KiB envelope, bounds header/body/connect/send/read
timeouts, applies a per-IP burst gate, disables request buffering and overwrites
forwarded client identity. Its minimal access log contains no path, query, body,
identity or authorization value. Application request IDs remain available in the
backend's privacy-safe structured log.

The hosted quality job validates Compose interpolation, starts the stack with a
disposable certificate and production-shaped configuration, waits for the API
health dependency, verifies `/ready` through HTTPS, and proves the API port is not
published. The certificate and runtime volume are then destroyed.

This is a deployable host-neutral bundle, not evidence of a live production
deployment. Real acceptance still requires the user-confirmed host/domain,
certificate automation, protected secrets, encrypted durable storage, backup and
restore, monitoring/alerts, provider budget, rollback, live readiness and the APK
candidate bound to that exact HTTPS origin.
