# Public-release credential check — 2026-10-17

The owner authorized public visibility on condition that the standalone repository
contains no private keys. The repository has its own Git history and synthetic
sample tasks. No original product history or real project ledgers were copied.

The release scan uses Gitleaks 8.30.1, downloaded from its official GitHub release.
The Windows x64 archive SHA-256 matched GitHub's release asset digest:
`d29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e`.

Both the complete Git history (`--log-opts=--all`) and working directory are scanned,
with findings fully redacted. No environment-provided Gitleaks configuration or
inline allow comments are used. The default rules remain enabled.

The initial default scan reported two generic-API-key candidates in the source
hash manifests. Both were verified by hashing the referenced stylesheet files:

| Manifest | Hashed input | Classification |
| --- | --- | --- |
| docs/provenance.json | web/shared/ci/tokens.css | SHA-256 of the original stylesheet |
| docs/verification.json | tools/tokens.css | SHA-256 of the standalone stylesheet |

`.gitleaks.toml` allows only those two exact digest strings, only within these two
manifest paths, and only for the generic-API-key rule. It excludes no files or
commits. These values are reproducible file checksums and confer no access.

Reproduce the release checks with Gitleaks installed:

```sh
gitleaks git . --log-opts=--all --config .gitleaks.toml --ignore-gitleaks-allow --redact=100
gitleaks dir . --config .gitleaks.toml --ignore-gitleaks-allow --redact=100
```

The release check found no credentials after these verified false positives were
accounted for. Automated scanning is detection evidence, not a guarantee against
every possible form of secret. The proprietary license is unchanged.
