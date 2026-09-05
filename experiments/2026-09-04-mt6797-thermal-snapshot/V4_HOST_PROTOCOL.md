# Corrected V4 candidate-pinned host protocol

This implements the [runtime acceptance contract](V4_RUNTIME_ACCEPTANCE.md)
for the frozen corrected candidate. It does not yet admit installation or
execution: exact-candidate shell validation and the complete device-cycle
receipt are still required. No device was accessed to implement these tools.

## Fixed identities and source boundary

The [runner](scripts/run-v4-observation.py) pins padded candidate
`b007af3d7025b804b34c6f1e717b2eca5e9fecf09b0ff731cede2a12116d993c`, record
`6972913af84c5b651848516456d1c6744015f3fc02a9d18596441a6c82d97ad3`, and
release `7.1.3-gemini-thermal-v4-corrected`. It hashes dependencies before
importing the protocol, validates the private deployment receipt, and invokes
the source-pinned offline candidate validator before choosing USB transport.
No expected identity is learned from runtime output.

The [remote read](scripts/remote-v4-observation-read.sh) differs from the frozen
predecessor only in release and record identity. All pristine lifecycle,
offline-A72, path/mode, read-only sysfs, prior-attempt and changed-boot checks
remain. The state probe is reused byte-for-byte and consumes no snapshot.
Both scripts keep their prior behavior; the host applies the new precision
and consumed-boot refusals from the tested orchestration.

## Receipt, persistence and stopping

The only admitted receipt location is
`artifacts/device-install-evidence/thermal-v4-deployment-1/deployment-summary.txt`.
Its mode-0700 directory must contain exactly the mode-0600 summary and manifest,
with no symlinks or extra files. The complete inherited receipt schema requires
inactive boot2, exact candidate/full-readback identities, stable power, no fresh
backup, removed temporary readback and completed shutdown/unreachability.
Missing or inconsistent provenance refuses before interface selection.

The exclusive capture is
`artifacts/runtime-captures/thermal-v4-no-workload-1`. Creation is persisted to
its parent before transport; every request is written exclusively at mode 0600,
flushed and fsynced before the consuming session. An interrupted directory
cannot be reopened. BaseException handling retains refusal classification even
for keyboard interruption, and final inventory hashes are persisted. Storage
failure cannot turn an incomplete attempt into success or remove its spent
capture. The runner never deletes evidence to enable a retry.

At most five source-interface-bound USB sessions are possible, with inherited
5/15/20-second connect/idle/outer limits and one-second spacing before reads two
and three. A request-seal interruption produces no consuming transport; timeout
or nonzero transport retains available partial output and stops. Postflight is
attempted only after three complete accepted snapshots. No additional cleanup
probe follows refusal. Ordinary reads remain two; CPU admission/off, frequency
observation, storage access and reboot counts remain zero.

## Guarded installer adapter

[install-v4-boot2.sh](scripts/install-v4-boot2.sh) pins the established base
installer and changes only the exact candidate, manifest and private basename
plus experiment attribution. The candidate validator runs before execution.
The original live-GPT, inactive target, power, full-partition readback,
matching-image skip and clean-shutdown gates are retained. It creates no backup
and never substitutes another partition. Its derived script passed Bash syntax
and ShellCheck, and temporary derivation state was removed. Validation-only
performs no device access.

After exact-shell admission is published, the intended preparation command is:

```sh
bash experiments/2026-09-04-mt6797-thermal-snapshot/scripts/install-v4-boot2.sh --execute \
  --target gemini@192.168.1.50 \
  --candidate-dir artifacts/thermal-snapshot-composition/candidate-v4-ba906730 \
  --evidence-dir artifacts/device-install-evidence/thermal-v4-deployment-1
```

The device must first be in its documented known-good OS; no old mainline or
Gemian-cycle receipt can stand in for this installation. Only a complete receipt
and a fresh owner-selected boot admit the new pristine gate. Without `--execute`,
the runner validates sources, candidate and receipt offline. With it, the
single frozen run is requested; it is not selected yet.

## Offline validation and remaining admission

[test-v4-observation-runner.py](scripts/test-v4-observation-runner.py) invokes
the actual runner with fake USB and private temporary files. Ten scenarios
cover success, preflight refusal/timeout, consuming timeout/nonzero/interruption,
host-spacing interruption, request-seal interruption, second-read heat and
postflight failure. All ten captures refuse restart without another transport.
Five receipt inventory/manifest/mode/schema/identity failures refuse before USB;
a dependency mutation refuses and the remote script's two-identity-only delta
is checked. Each retained capture's manifest and file modes are verified.
The [orchestration fixtures](scripts/test-v4-observation-protocol.py) separately
cover 30 scenarios and 13 identity refusals.

These host tests do not execute the target shell or validate hardware. Exact
candidate BusyBox tests of the new remote checks, shell syntax and full host
suite must pass from a clean published revision before preparation. The prior
candidate's shell pass alone is insufficient. No rebuild is required for this
host-only work. The current consumed mainline session is untouched, and all
thermal-repeatability and wider power-management gates remain closed.
Ordered work belongs to the [roadmap](../../docs/ROADMAP.md).
