# Experiment: Gemian A72 read-only surface discovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-22-gemian-a72-readonly-discovery` |
| Status | `partial discovery passed`: v2 captured 180 safe samples; no A72 transition; complete owner-synchronized contract still missing |
| Subsystem | MT6797 A72 external power, iDVFS, clocks, DCM, SPM and TOPRGU |
| Device variant | Current named Gemini PDA unit |
| Date(s) | 2026-07-22 source audit and safe-stop; 2026-07-23 corrected live capture |
| Investigator(s) | Project maintainers |
| Tracking issue | Not yet assigned |

## Question or hypothesis

Can the unmodified working Gemian 3.18 kernel expose enough state through
existing read callbacks to capture the A72 firmware/power prerequisites during
natural HPS transitions, without `/dev/mem`, raw I2C access, CPU-online or
policy writes, any SMC invoked by a collected content callback, or
tracing-control changes?

The falsifiable source-level hypothesis is that at least one useful subset is
safe to collect, but that the current interfaces cannot supply the complete
transaction-local state required by the A72 firmware/power contract.

## Provenance and environment

- Public source: `gemian/gemini-linux-kernel-3.18`, commit
  `d388d350cb2dda8f23b99be6fa5db9628896e87f`, inspected from the clean pinned
  recovery-VM checkout at
  `/home/julien.guest/src/reference/gemian-linux-kernel-3.18`.
- Intended live kernel: the named Gemini's working Gemian `3.18.41+` system.
  Source similarity does not prove that the installed binary is byte-identical
  to the public commit; every future capture must retain live identity.
- Same-image configuration evidence retained privately at
  `artifacts/device-inventory/20260712-live/vendor-kernel.config`, SHA-256
  `231d8a2ffe7afac3a4cc62c27d0eb6fe8bd9165ebd096e3e3346dd6df35c18f4`.
- Required state is defined by
  [`../2026-07-22-a72-firmware-power-contract/results/a72-firmware-power-contract-prerequisites-20260722.md`](../2026-07-22-a72-firmware-power-contract/results/a72-firmware-power-contract-prerequisites-20260722.md).
- No kernel, DT, boot image, device partition, firmware, or policy was changed
  for this source audit or live attempt. Attempt 1 stopped at its root-identity
  gate before any vendor callback.

## Safety assessment

The collector is allowlisted and performs no state-changing device or policy
write. It creates no remote file and performs no register-value, sysfs,
procfs, debugfs, tracefs, CPU-hotplug, frequency, voltage, HPS/PPM, partition,
watchdog, reboot, suspend, or firmware write. It does not open `/dev/mem`, an
I2C character device, or a user-controlled SMC interface. The exact collected
content callbacks do not invoke an SMC.

One allowlisted callback, `/proc/idvfs/idvfs_debug`, performs a serialized
DA9214 register-address read through the owning kernel driver. The I2C transfer
sends the register address but does not program a register value. The callback
is accepted only as a partial observation: its selector is mutable elsewhere,
its page is not exposed, and it ignores the driver's read result. The output is
therefore retained verbatim and marked usable only when it reports address
`0xd9`; it is never promoted to page-qualified voltage proof.

The script deliberately does not open `/proc/idvfs/dvt_test`, the DA9214
`da9214_access` attribute, CPUHVFS `dbg_repo`, `dcm_state`, or the B/CCI clock
selection proc nodes. It also never opens B-cluster `cpufreq_volt`: when
CPU8/9 are online that show callback can conditionally invoke fixed read-only
SMC `0x8200035f`. Metadata is sufficient for discovery and keeps the
collector's no-SMC boundary exact. It records metadata only for those exact
paths. Fixture tripwires test that their contents remain unread.

Before any vendor procfs/debugfs callback or DA9214 transaction, the remote
script requires exact kernel `3.18.41+`, architecture `aarch64`, root
identity through two independent representations—read-only
`findmnt -n -o SOURCE /` exactly `/dev/mmcblk0p29` and the `/proc/mounts` root
source exactly `rootfs`—`possible=0-9`, `present=0-9`, a stable well-formed
boot ID, stable external power, and a present/full/100%/healthy battery. It
fails closed if either root source is absent, unreadable, failed, or different.
It checks the boot ID again after capture. It brackets the one safe CPUHVFS
context dump and every natural vendor sample with exact, unchanged
healthy-power observations.
Any power drift, unhealthy power state, exact userspace `read-failed`, or
missing required uptime/online-mask bracket causes an immediate fail-stop with
a sanitized marker in the preserved partial capture. Optional safe surfaces
may remain absent.

The host wrapper has no target or identity override. It uses exact target
`gemini@192.168.1.50`, the Git-ignored repository identity
`artifacts/credentials/gemini_ed25519`, strict existing-host-key checking, and
no SSH agent. Output must be a new, Git-ignored
`artifacts/runtime-captures/gemian-a72-readonly-*.txt` file directly under the
mode-0700 private capture root. It is mode 0600. If SSH or the remote gate
fails, the wrapper preserves the mode-0600 `.partial` evidence instead of
deleting it. Passwordless `sudo -n` is used only to obtain read permission; no
remote file is created. SSH uses 5-second server-alive probes with three misses
allowed. A checked-in bounded-exec helper runs SSH as its one exact child and
kills only that unreaped child at the hard deadline. The deadline is the
requested inter-sample sleep time, `(samples - 1) * interval`, plus a fixed
60-second grace for connection, gates, callbacks, filtered dmesg and the
server-alive failure window. SSH's other exit and signal statuses propagate.

The implemented automatic stop conditions are exact power drift/unhealthy
power, an observable exact `read-failed`, a missing required sample bracket,
boot-ID change, SSH failure, or the hard wall deadline. The existing callback
does not expose its internal DA9214 read status, so the collector does not
claim to detect an I2C error. It also has no independent thermal stop surface.
SSH and sampling have nonzero CPU cost and can influence HPS timing; the
procedure adds no synthetic workload and does not claim zero observer effect.

## Associated code

- [`scripts/remote-probe.sh`](scripts/remote-probe.sh): POSIX allowlisted probe;
  defaults to 180 one-second samples and permits at most 900 samples or 900
  seconds total.
- [`scripts/collect.sh`](scripts/collect.sh): host-side SSH wrapper requiring a
  new private output path; its target and mode-0600 identity are fixed.
- [`scripts/bounded-exec.pl`](scripts/bounded-exec.pl): minimal monotonic
  wall-clock bound that directly forks/execs and, on timeout, kills only its
  exact unreaped child.
- [`scripts/test-readonly-collector.py`](scripts/test-readonly-collector.py):
  fixture, selector-mismatch, power/read fail-stop, bounds, bounded-child,
  static-token, and excluded-content tripwire tests.
- [`results/gemian-existing-observer-gap-audit-20260722.md`](results/gemian-existing-observer-gap-audit-20260722.md):
  source-backed classification of every prerequisite.
- [`results/tooling-validation-20260722.txt`](results/tooling-validation-20260722.txt):
  local lint/test results and exact scaffold hashes.
- [`results/live-attempt-1-root-gate-20260722.txt`](results/live-attempt-1-root-gate-20260722.txt):
  sanitized safe-stop and generic dual-root corroboration facts.
- [`results/live-attempt-2-partial-discovery-20260723.txt`](results/live-attempt-2-partial-discovery-20260723.txt):
  sanitized successful v2 sampling summary and remaining observer gaps.

The intended invocation, from the repository root, is:

```sh
experiments/2026-07-22-gemian-a72-readonly-discovery/scripts/collect.sh \
  --output artifacts/runtime-captures/gemian-a72-readonly-BOOTID.txt
```

The v1 command was run once and stopped safely before vendor callbacks because
its single `/proc/mounts` gate expected the backing block device rather than
Gemian's `rootfs` representation. The corrected v2 dual-root invocation then
completed once on the returned known-good Gemian boot.

## Procedure

1. Confirm the named unit is expected to be in the known-good Gemian OS. The
   remote script independently rejects any non-exact kernel, architecture,
   root, topology, boot-ID or power/battery gate before opening a vendor
   callback.
2. Run the fixture/static test and `bash -n`/`sh -n`; run ShellCheck when it is
   available. The test also syntax-checks and exercises the Perl hard-bound
   helper, including exact status propagation, timeout partial output, and an
   unrelated-process sentinel.
3. Run `collect.sh` once to a new Git-ignored output path. Do not start a load,
   change HPS/PPM policy, write a CPU `online` file, mount debugfs, or enable a
   trace while it runs.
4. Retain initial identity, power-bracketed safe CPUHVFS context,
   excluded-node metadata, 180 power-bracketed natural one-second samples, and
   filtered existing kernel messages. The B `cpufreq_volt` node is metadata
   only and its content must not be opened.
5. Treat a sample whose mask changed between the two mask reads as torn.
   Treat an unchanged mask only as `stable-nonatomic`, never as an atomic
   hardware snapshot.
6. On success, summarize only non-identifying results. On failure, inspect and
   retain the mode-0600 `.partial` file; never overwrite it on a retry. Keep all
   full captures private below `artifacts/`.

## Observations

The offline source audit is complete. It found one serialized DA9214 address
read and B/CCI reported-rate surfaces that are useful enough for a bounded
partial collector without entering the secure monitor. It found no safe
existing surface for DA9214 page or BUCKB
enable, either required SPM word, TOPRGU bit 11, the full secure-register set,
protected B/CCI mux/divider fields, or MP2 DCM.

Live attempt 1 produced only `failure=gate-root-mismatch` in a 27-byte,
mode-0600 private partial with SHA-256
`4cfad8507bf664ab7fcb7e095897f623381ff9b8ee336f5ace1a6a296dfafac2`.
It opened no vendor callback and performed no device write. A bounded generic
read-only check then confirmed kernel `3.18.41+`, `aarch64`, findmnt root
`/dev/mmcblk0p29`, `/proc/mounts` root `rootfs`, and possible/present `0-9`.
No boot ID or plain identifier is tracked. The offline code-edit and test work
for the corrected v2 revision used no device or network access; that statement
does not include the separately recorded v1 safe-stop or bounded generic live
corroboration. There is no A72 value, natural-transition capture, or
hardware-support claim.

Live attempt 2 passed all identity, topology, stable boot-ID, external-power,
and battery gates and completed 180 one-second samples. The only observed
online masks were `0` and `0-1`; CPU8 and CPU9 never appeared. Of the samples,
34 were stable at CPU0, 60 were stable at CPU0-1, and 86 changed from CPU0 to
CPU0-1 inside the sequential bracket and are retained as torn. The serialized
DA9214 callback reported selector `0xd9` and value `0x46` in all 180 samples,
the cached B rate remained 845 MHz, and the unprotected derived CCI report
varied among 325, 416, 676, and 819 MHz. Power and boot identity remained
stable. The private capture is mode 0600 with SHA-256
`f741d119a378c287663df5dd5453abdc8be656ecd36e539678eb6ad27266868c`.
No remote file, policy change, SMC, CPU request, or state-changing write was
performed. See
[`results/live-attempt-2-partial-discovery-20260723.txt`](results/live-attempt-2-partial-discovery-20260723.txt).

## Analysis

The source-level hypothesis is supported. Existing interfaces can correlate
the online mask with a driver-serialized read of address `0xd9`, a cached B
rate, a non-semaphore-protected derived CCI rate, safe CPUHVFS context and
coarse existing logs. That can discover whether natural A72 states are
observable and whether the selector still names `0xd9`. B `cpufreq_volt`
content is deliberately excluded so this collector invokes no SMC.

It cannot answer the implementation-critical questions. The values are read
sequentially, the DA9214 page and enable bit are missing, the B rate is cached,
the CCI read lacks the DVFSP hardware semaphore, and no exact SPM/TOPRGU/secure
or MP2 DCM state is exported. A mask-stable sample can still cross a voltage or
clock transition. The scaffold must not be used to select the draft A72 power
patch or to infer a rollback sequence.

## Conclusion

`partial discovery passed` for the named hardware: the corrected v2 collector
reached its sampling phase safely and confirmed the existing partial surfaces,
but observed no natural A72 transition. The result is necessarily incomplete:
the unmodified public Gemian source exposes no synchronized page/enable, SPM,
TOPRGU, secure-register, DVFSP-locked clock, or MP2 DCM state. A complete A72
prerequisite capture still requires a separately reviewed, read-only in-kernel
observer integrated with those owning paths.

## Follow-up

Use the successful v2 capture to size the missing owner-synchronized in-kernel
observer. Do not select or revise the A72 power-on implementation until that
observer captures page/enable, SPM, TOPRGU, secure, protected clock, and DCM
snapshots at natural offline/online/offline state boundaries.
