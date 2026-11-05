# Security

PawSec currently supports one trusted owner, not public registration or mutually untrusted users.

- Public mode requires an HTTPS origin and a password hash; all routes require authentication.
- Cross-origin requests and cross-site browser fetches are rejected. Mutations in public mode require an exact Origin header.
- Caddy is the only exposed container. Do not publish the application port or run Flask's development server on the Internet.
- Local mode is intended for loopback access only. Do not tunnel local mode to a public address.
- Runtime data, browser sessions, environment files, encryption keys, backups and model credentials must never be committed.
- The owner can configure outbound model providers and mail services. This authority is unsuitable for anonymous visitors.
- PDF parsing, model output, third-party APIs and imported metadata remain untrusted. Verify generated summaries and citations.
- Encryption of saved provider credentials does not protect against someone with access to the entire data volume.

Report suspected vulnerabilities using the hosting platform's private vulnerability reporting feature when available. Do not disclose credentials, private papers or exploit details in a public issue. Repository maintainers should enable private vulnerability reporting before announcing a public release.
