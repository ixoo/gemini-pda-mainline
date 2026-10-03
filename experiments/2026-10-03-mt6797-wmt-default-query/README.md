# Experiment: first MT6797 WMT default query

| Field | Value |
| --- | --- |
| ID | `2026-10-03-mt6797-wmt-default-query` |
| Status | `in-progress` (installed and readback verified; waiting-owner-boot) |
| Subsystem | CONSYS / BTIF / WMT |
| Device | Project Gemini PDA |
| Investigator | Codex, under owner standing authorization |
| Tracking issue | [#25](https://github.com/ixoo/gemini-pda-mainline/issues/25) |

## Question and boundary

Can the freshly powered CONSYS MCU answer the fixed default WMT option query
through BTIF mandatory STP, before WLAN HIF or common initialization?
The [startup review](../2026-10-03-mt6797-wifi-audit/BTIF_MANDATORY.md) owns the
source identities, register conflicts and host fault fixtures. This experiment
owns integration, build and any later exact candidate/runtime receipt.

## Selected compile inputs

Profile `mt6797-a53-wmt-default-query-compile` uses the existing WMT-before-start
foundation through proposal 0052, followed by proposals 0086–0091. It does not
select the later receive-sampling stack or parked proposal 0085. The executor
and wire helper are byte-identical to the host-tested drafts. The binding and
CONSYS owner acquire exact BTIF/channel resources and existing upstream clocks.
A source-fingerprinted level-low SPI 130 must inherit the MT6797 sysirq provider;
actual IRQ mapping occurs only after admitted CONSYS reset release.

The isolated board disables the WLAN child. Probe enables no transport clocks
and performs no query. After private region-19 preservation and its existing
one-shot preparation, the root-only `wmt_default_query` attribute replaces the
WLAN trigger. It reuses the existing prepower admission and power/reset sequence,
then stops after the query, with all four HIF/EMI-copy/WLAN-start arguments false.
The inherited diagnostic DT flags describe the foundation; the query-only
property overrides their runtime continuation. No Wi-Fi PA rail, calibration,
full-mode negotiation, ROM patch or WLAN firmware transfer belongs to this test.

## Validation and remaining admission

Run the existing sanitizer host fixtures and strict patch style checks. Synthetic
archive patches deliberately carry no invented DCO; checkpatch excludes only
`MISSING_SIGN_OFF` and the new-file MAINTAINERS reminder. Check exact replay,
canonical profile order, staged privacy/license/link checks and repository gates.
Compile only from a clean pushed checkout:

```sh
KERNEL_PROFILE=mt6797-a53-wmt-default-query-compile ./scripts/build-kernel --backend buildbox
```

Exact five-file replay, byte equality with both host-tested helpers,
sanitizer-backed host fixtures, strict patch style and repository checks pass.
The [first Buildbox attempt](results/build-1.json) failed DT compilation on
two clock references to an absent `infracfg` label. Proposal 0091 uses the
existing `infrasys` label. That attempt produced no validated package. The corrected
[second build](results/build-2.json) passed and its exact inventory and clean
commit/profile provenance passed local fetch validation. Compiled owner/helper
hashes match the reviewed integration, and the linked kernel contains the
query store and IRQ handler. Complete private logs are retained by digest.
The [focused schema checks](results/schema-2.json) pass binding lint/example
compilation and direct validation of the exact package DTB. Removing each of
clocks, clock-names and interrupts is rejected. Two DTC USB ranges warnings
remain outside the selected CONSYS node; this is not an all-bindings board
validation or a validated booted-DT candidate.
Proposal 0090 also fixes a reviewed deadline-underflow race by sampling
`jiffies` once, with a deadline-drift fixture that rejects the older executor.
The [channel-register review](results/dma-read-review.json) corroborates the
selected EN/STOP/FLUSH and buffer-count fields without documented read-clear
effects. It does not establish clock-off access, shared-clock enable safety or
live writer exclusion.
Before device admission, review the finite MMIO/IRQ effects, FIFO alias writes,
the initial DMA_EN timeout acknowledgment, shared AP-DMA clock-enable effects,
channel exclusion and power-retaining failure/recovery lifetime. Host fixtures
do not model real MMIO or IRQ concurrency. Do not use this record as a hardware
admission or installation instruction. No device has been contacted.

A later admitted test will consume one exact query lifetime: a matched response
establishes transport liveness; timeout or malformed/extra data stops without
retry and keeps the transport question open. Neither outcome establishes RF
calibration, reception, association or working Wi-Fi.

## Candidate and runtime follow-up

The [candidate builder](build-candidate.py) pins the exact fetched package and
proven pool-sample parent, preserves all 178 unrelated DT nodes, disables the
WLAN child and changes only CONSYS transport properties. The private RAM root
changes only its release gate; unused retained WLAN inputs remain private and
are not transferred to the MCU. The [candidate receipt](results/candidate.json)
records a validated LK container and 16-MiB padded image. The
[offline checks](results/candidate-validation.json) reproduce every member hash
and refuse an occupied output without mutation. Direct selected-schema
validation of the composed booted DT passed with empty diagnostics.

The [clock source join](results/clock-admission.json) resolves the AP-DMA ordering
for this candidate only: the active UART0 console retains a vote on the same
clock, so the query adds a reference rather than ungating the engine. The
[runtime protocol](RUNTIME_PROTOCOL.md) requires that live console/runtime state
and confines one query and retained-power recovery. The [host-tooling validation](results/tooling-validation.json) now records nine
synthetic guard/receipt tests, shell checks and offline capture/recovery preparation
against temporary synthetic receipts. Deployment is recorded below; changed-boot mainline identity is still required
before the query. The
candidate receipt retains its historical offline-only admission field.


## Host execution order

The [installer adapter](install-passive.py) pins the existing full live-GPT/block
identity guard, predecessor or already-matching checksum, stable-power gates,
independent full partition readback and clean shutdown. It uses the project-wide
backup; it writes only logical boot2. Prepare its generated installer for the
freshly verified Gemian boot identity, review it, and publish intended tools
before execution. Installation is followed by owner-operated boot2 selection.

After a real deployment receipt is copied privately into `session-1`, run offline
preparation for both [capture](capture-private.py) and
[preservation/recovery](passive-host.py). Verify the exact new mainline identity,
then execute capture once: two identical private preimages, one region-19 setup,
one default query. Run the preservation/recovery host after capture regardless
of capture's return status; a failed query does not skip evidence sealing or
admit a retry. Stop on a missing identity/evidence/recovery prerequisite.

The [session adapter](passive-session.py) validates the retained authenticated
RAM environment and existing bounded A53 regression. It sends no WLAN firmware
or radio command. The capture rechecks the UART console, driver/runtime state and
positive RAM clock counters before each trigger. Its read-only restoration trap
is installed before the read-write remount, including that remount's failure
path. Both newly written and already-matching installations require the reviewed
complete deployment receipt; matching-skip additionally requires the predecessor
to equal the candidate. Raw captures, generated installers and credentials stay
private under ignored `artifacts/`.

Run the hardware-free guard/receipt checks with:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-10-03-mt6797-wmt-default-query/tests/runtime-guard-test.py
```


## Deployment and owner handoff

[Deployment 1](results/deployment-1.json) resolved logical boot2 from the live
Gemian GPT to `/dev/mmcblk0p30`, with root `/dev/mmcblk0p29`. The block identity,
mount/holder/swap, target size/writability, predecessor and stable-power checks
passed. One write, synchronization/flush, full remote checksum and independent
16-MiB byte-for-byte readback matched the selected candidate. Temporary staging
and readback were removed; the project backup was reused. Clean shutdown was
confirmed unreachable; no automatic reboot occurred.

Capture and regression/preservation/recovery preparation passed against that
real deployment receipt. The [session packet](SESSION.md) now requests one
physical boot2 selection. No query, RF scan or mainline runtime result follows
from deployment. The first query lifetime remains unconsumed.
