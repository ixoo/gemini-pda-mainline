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
with no symlinks or extra files. The strict V4 receipt schema requires
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
installer and adapts candidate identities and experiment attribution. The
[guard derivation](scripts/v4_installer_guard.py) additionally embeds the exact
library from the shared [block identity guard](../../scripts/boot2-device-guard.sh),
after validating its complete SHA-256. It replaces the historical root-source
string check with verified mountinfo, sysfs and block-node identities. The
observed root and target device numbers are pinned across deployment stages;
the guard runs again immediately before the write with the observed root pin.
The [V4 receipt validator](scripts/v4_deployment_receipt.py) requires these
fields and the exact guard digest, rejecting absent, duplicate, empty, malformed
or equal root/target numbers. It records the actual verified root rather than
assuming a partition number.

The candidate validator runs before execution. Existing live-GPT, power,
full-partition readback, matching-image skip and clean-shutdown gates remain.
No historical installer or receipt parser is modified. The derived script passes
Bash syntax and ShellCheck; temporary derivation state is removed.
Validation-only performs no device access. The guard executes under Gemian Bash;
the separate observation scripts execute under the candidate BusyBox shell.

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

The [guard integration fixtures](scripts/test-v4-installer-guard.py) reject
three changed-source derivations and 24 invalid device-identity receipts, while
accepting a verified root different from the historical fixed partition.
The shared guard's 18 fixture groups also pass. The complete
[derived deployment shell](scripts/test-v4-deployment-shell.py) passes 19
synthetic cases on host Bash, including a target mount or changed root appearing
between initial validation and the write, corrupt staging/readback, wrong GPT,
low power, holders and swap. Writes and device applets are mocked; only the
successful write and failed readback cases reach one bounded simulated write.
These tests are not evidence of the physical Gemian mount state.

The [remote-shell fixtures](scripts/test-v4-remote-shell.py) execute both remote
observation scripts against synthetic files, enforcing exactly one consuming
read for admitted attempts and zero before refusal. Eighteen read cases and six
state cases pass a host-shell smoke test. The smoke test exposed and corrected
two fixture defects: path replacement inside `/proc/sys`, and mutation of
read-only fixture files. Neither production remote script changed.

The [V4 shell suite](scripts/run-v4-shell-tests.py) requires a clean exact Git
revision and the frozen initramfs. It extracts the hash-verified candidate
BusyBox using the pinned predecessor extractor, executes observation checks
under AArch64 user-mode QEMU, and runs host/installer fixtures under builder
Python/Bash. Temporary binary and wrapper files are removed. No kernel build,
device operation, or native-shell substitute is allowed for the observation
checks. Exact-candidate execution is still pending publication of this tooling.

These host tests do not execute the target shell or validate hardware. Exact
candidate BusyBox tests of the new remote checks, shell syntax and full host
suite must pass from a clean published revision before preparation. The prior
candidate's shell pass alone is insufficient. No rebuild is required for this
host-only work. No device operation is admitted by this integration, and all
thermal-repeatability and wider power-management gates remain closed.
Ordered work belongs to the [roadmap](../../docs/ROADMAP.md).

The [host validation receipt](results/v4-guard-host-validation.json) binds these
preliminary checks to exact sources; it explicitly leaves physical admission
and exact-candidate execution pending.

The final host argument gate now accepts only `thermal-v4-deployment-1`, matching
the runner's frozen receipt path. An offline integration review found that the
inherited global name substitution had left a different evidence prefix; this
would have refused the published installation command before SSH. The entire
V4 derivation is now shared by the installer and deployment fixtures. Eight
executed host-path cases prove runner agreement and refusal of alternative,
existing or symlinked capture directories. No device attempt encountered this
host-only defect.
