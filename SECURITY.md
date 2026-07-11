# Security policy

## Sensitive reports

Do not publish exploitable boot-chain vulnerabilities, credentials, keys, IMEI values, calibration data, NVRAM contents, or private firmware dumps in a public issue.

For a security vulnerability in repository-owned tooling, use GitHub's private vulnerability-reporting flow when it is available. If private reporting is unavailable, contact the maintainer through the private contact method on their GitHub profile and include only enough detail to arrange a secure handoff.

For vulnerabilities in Linux, a distribution, firmware, or a third-party tool, follow that upstream project's security process.

## Hardware safety is tracked separately

Potential data-loss or hardware-damage paths in project tooling should be reported promptly with non-sensitive reproduction details and the `safety: data-loss` or `safety: brick-risk` label. Read [Safety and recovery](docs/SAFETY.md) before attempting to reproduce them.

## Supported versions

The project does not yet publish supported releases. Development branches and generated images are experimental and receive no security-maintenance guarantee.
