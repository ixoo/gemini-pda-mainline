# Kepler results

This directory contains sanitized, reviewable offline build and runtime
contract evidence.

The exact helper ELF and raw live transcript are intentionally retained only
under Git-ignored `artifacts/`.

- `build-kepler-20260727.txt` records reproducible build and offline ioctl
  validation.
- `runtime-transfer-contract-kepler-20260727.txt` records the fail-closed
  volatile runner contract.
- `runtime-kepler-split-read-20260727.txt` is the sanitized result of the
  single accepted-Hubble hardware invocation.
- `da9214-split-read-protocol-crosscheck-20260727.txt` records the two
  datasheets' agreement that a STOP followed by a second START is a valid
  register-read sequence.

The sanitized result intentionally omits host-interface details, service
banners, and any unrelated identifiers.
