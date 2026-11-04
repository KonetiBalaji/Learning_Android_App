# Deploy Saras
Use a Linux Docker host with the Docker Compose plugin. The API runs as UID 10001 behind Caddy and uses a single worker with persistent SQLite storage. Only the proxy publishes ports. The image prepares and verifies public OCR and embedding models at build time.

1. Provision a Fernet key in a file outside the repository. For a new empty database, use `umask 077; openssl rand -base64 32 | tr '+/' '-_' > /secure/path/storage.key`. Give the container UID 10001 read access. For an existing database, use its original key and retain a backup. Back up the database and key separately.
2. Set `STUDY_STORAGE_KEY_PATH` to the absolute key-file path, `STUDY_SITE` to the bare public DNS name, and `STUDY_BIND=0.0.0.0` on the intended public host. Point DNS at that host and allow inbound TCP 80 and 443. The default bind address is loopback.
3. Run `docker compose up --build --wait`. Check `https://YOUR_HOST/health` and `https://YOUR_HOST/ready` with certificate verification enabled. Retain the Caddy data volume so the proxy can reuse and renew its certificates.
4. Before opening access, run the study-flow smoke against the intended staging hostname with its trusted CA. Back up existing volumes before upgrading. Use `docker compose down` to stop a live deployment while retaining volumes.

The default generation mode is local practice. Request limits are per client IP in one process, with a default of 120 requests per minute and separate sign-in throttling. The API trusts forwarded addresses from its private Compose network, so keep port 8000 unpublished and limit network membership to this stack. Request logs contain the route template, status and latency. Document and linked progress records expire after 30 days. Database and proxy volumes should be backed up with appropriate host permissions.

The GitHub Actions staging job deploys the same stack on loopback with Caddy's private CA, validates certificate trust explicitly, and exercises the study workflow. Its cleanup deletes only the disposable runner volumes. Public certificate issuance and a persistent production host require the deployment hostname and access.
