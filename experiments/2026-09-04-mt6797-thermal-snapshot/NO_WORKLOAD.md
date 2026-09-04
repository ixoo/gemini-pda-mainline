# First no-workload thermal observation

This is the prospective composition contract. It is not yet a selected device
candidate: the exact package, container, candidate checksum and host execution
receipt remain required before any deployment or boot request.

## Hypothesis and decision

The earlier second-boot CPU/RAM/frequency result passed, but its thermal
comparison failed. The new source path records all seven converted samples in
six bank visits, their validity, the first winning slot and callback timing
from the existing scan. The hypothesis is that this bounded interface returns
complete, internally consistent per-bank evidence on the Gemini without
consuming the CPU lifecycle or frequency-observer budgets.

The unique new evidence is sensor attribution and scan duration, not another
aggregate-only workload repeat. The first device observation performs no A72
admission, hotplug transaction, RAM workload or frequency observation. It leaves
CPU8/CPU9 offline. A complete result validates the observation path only; it
cannot close thermal repeatability, explain the earlier load-associated rise
by itself, or establish conversion age or a simultaneous sensor snapshot.

Missing attributes, identity disagreement, non-pristine accounting, failed or
inconsistent records, temperature refusal or transport interruption reject the
run. Retain partial evidence and do not retry a spent observation. A successful
no-workload result permits designing a separate attributable bounded protocol;
it does not authorize the closed workload or wider power-management tests.

## Production configuration

The named `gemini-thermal-snapshot-candidate` profile inherits every fragment of
`gemini-a72-frequency-thermal-candidate` in order, then appends only
`configs/gemini-thermal-snapshot-candidate.fragment`. It enables the explicit
thermal observer, keeps KUnit and cpufreq/idle/suspend disabled, and selects
release `7.1.3-gemini-thermal-snapshot`. The fixed config-input digest is
`8fe1675a22f82e9efbc38a994a95eaaeb32fbc46b6fad42561f3e01d3097b3a5`.
The profile-binding patch adds that exact identity under the thermal-observer
selector while preserving the previous frequency and physical identities.

The candidate must include the corrected reader lifetime and the proven
thermal/topology DT composition. The deterministic RAM-only initramfs may be
reused only after checking its exact bytes and startup actions. Package,
resolved configuration, DT provenance record, kernel identity, LK container,
load/decompression constraints and mutation checks must be published before
installation. Default-profile integration remains closed.

## Host protocol requirements

A prepublished host protocol must bind one capture directory and at most one
attempt to the exact padded candidate, package provenance and deployment
readback. Require a new boot ID distinct from deployment and every consumed
baseline/repeat boot. Require exact release and A41 record, the ready late-CPU
profile, CPUs 0--7 online and 8--9 offline, the inherited armed lifecycle with
zero execution and zero frequency-observer attempts. Require a unique thermal
observer/status pair on the same MT6797 device, mode 0400, read-only sysfs and
status `abi=1 attempts=0 limit=3` before the first snapshot.

The initial aggregate must be 0--58500 millicelsius. Capture at most three
snapshot records, checking each before requesting another. Retain the same
58500 upper bound for every converted sample; this is at least as restrictive
as the earlier comparison's absolute upper bounds. Require nonnegative valid
samples, complete ABI records, exact sensor order, correct aggregate/first
winner and increasing scan intervals. Refuse more than 5000 millicelsius
aggregate spread. These are conservative experiment refusal thresholds, not
validated silicon limits. This diagnostic does not add hardware trips or
cooling control.

The host must never read the snapshot attribute just to discover or inspect
it. Status reads consume no attempt. A failed snapshot returns text; preserve
that text and stop. No test of a fourth/exhausted read belongs on the device.
Any finite spacing and transport timeout must be fixed in the published runner.
After capture, require status attempts to equal the number actually requested,
unchanged boot/kernel/lifecycle identities, CPU8/CPU9 still offline, frequency
attempts still zero, and an explicit cleanup/no-storage-write statement.

No partition or filesystem backup is needed. Any eventual deployment remains
restricted to live-GPT-resolved inactive boot2 with full readback and clean
shutdown for physical selection. No deployment is admitted by this draft alone.
