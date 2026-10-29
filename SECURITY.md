# Security

## Reporting a vulnerability

Please report it privately, never in a public issue:

- **Preferred:** GitHub's private vulnerability reporting (the repository's **Security** tab, then
  **Report a vulnerability**).
- **Otherwise:** email info@kevindstreet.com with "Security" in the subject.

Include what you found, how to reproduce it, and what an attacker could do with it. You will get an
answer within 3 business days. A confirmed issue is fixed within 30 days, sooner when severe, and you
are credited in the advisory unless you would rather not be.

## Scope

In scope: the code in this repository and the `kds-*` packages built from it.

Out of scope: the model providers' own services, the made-up test data, and findings that need a
compromised developer machine.

## How this repository is protected

| Risk | Control |
| --- | --- |
| A committed secret | gitleaks before every commit and over the whole history in CI; secrets live only in `.env` |
| A secret in config | `kds.settings` refuses to start when `settings.toml` holds a secret |
| Personal data in logs | `kds.logs` redacts emails, phone numbers, SSNs, card numbers and birth dates by default |
| A vulnerable dependency | a lockfile with hashes, `pip-audit` in CI, Dependabot every week |
| A tampered Action or tool | Actions pinned to commit SHAs; the gitleaks download checked against its published SHA-256 |
| A flaw in the code | CodeQL and ruff's security rules (bandit) on every push; least-privilege workflow permissions |

