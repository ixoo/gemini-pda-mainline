# Photon result records

This directory holds sanitized, exact-revision Candidate Photon evidence.
Revision r0 was installed and fully read back but never booted; it is preserved
and marked superseded. Revision r1 corrected the early-stop ambiguity and was
reproduced, but its causal `overwritten` labels were superseded before
installation. Neutral pre/post revision r2 preserves r1's exact `I2C_RDWR`
request/message sequence and control behavior and is the only revision
eligible for the hardware decision run.

Exact records:

- `build-candidate-photon-r0-20260727.txt` and
  `install-candidate-photon-r0-boot2-20260727.txt`: installed, fully read back,
  never booted.
- `build-candidate-photon-r1-20260727.txt` and
  `helper-contract-tests-photon-r1-20260727.txt`: reproduced, never installed,
  superseded vocabulary.
- `build-candidate-photon-r2-20260727.txt` and
  `helper-contract-tests-photon-r2-20260727.txt`: neutral eligible revision.
- `install-candidate-photon-r2-boot2-20260727.txt`: exact r0 predecessor,
  guarded logical-`boot2` write, full backup, flush, and matching full
  readback.
- `runtime-candidate-photon-r2-attempt-1-20260727.txt`: white screen and
  automatic watchdog-class return before recoverable console/USB; exact
  post-return `boot2` checksum, empty pstore, and no probe invocation.
- `../../2026-07-27-da9214-transient-probe-hubble/results/runtime-candidate-hubble-photon-r2-attempt-1-20260727.txt`:
  exact r2 was later transferred into volatile `/run` on exact Cassini and
  invoked once; all six post bytes equalled their distinct prefills.

Each build record must preserve both independent artifact roots and all
boot-bearing hashes. A hardware record must preserve the installed raw and
padded hashes, exact Photon r0 predecessor plus its retained exact
Cassini-to-r0 chain, full backup and readback identities, boot IDs, complete
BEGIN/PRE/RESULT sequence, stdout post-values, I2C6 counter deltas, CPU and
serviceability state, native-reboot result, pstore, and the post-cycle full
`boot2` checksum.

Do not store private keys, partition images, full private logs, device serials,
credentials, or proprietary datasheet content here.
