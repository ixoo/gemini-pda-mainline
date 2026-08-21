# Protected-readback call ledger

## Status

Design, live read-only slot preflight, deterministic Buildbox patch generation,
strict review, canonical admission through patch `0323`, the exact Buildbox
kernel, reproducible Android-v0 candidate construction, guarded deployment,
full readback, clean shutdown, and the single device attempt are complete. The
exact artifact is rejected as `neither` and must not be repeated. No native VM
build occurred.

The rejected predecessor returned to changed-boot-ID Gemian before exposing
mainline USB and left no pstore, `last_kmsg`, or observer record. Its two reads
were adjacent and both log records came afterward, so that result cannot say
whether the observer was entered, the protected-clock call returned, or the
later BigiDVFS call was reached. See the
[predecessor result](../2026-08-21-mainline-protected-readback-runtime-observer/results/runtime-attempt-1-inconclusive-pre-transport-20260821.txt).

## Question

Which boundary did the predecessor cross: observer entry, return from the
protected-clock read, or entry into the later BigiDVFS read?

## Hypothesis and attributable evidence

The successor preserves the predecessor kernel, candidate DT, initramfs, two
protected reads, and CPU/owner closures. It adds exactly two short records in
the final two dmesg zones of the existing Gemini persistent-RAM reservation:

1. slot 173 at `0x444bd000`, immediately before the protected-clock call;
2. slot 174 at `0x444be000`, only after that call returns and immediately
   before BigiDVFS.

The first call validates the proven post-LK `MT6797X` model together with the
retained `planet,gemini-pda` compatibility, the full DT ramoops contract, and
valid empty headers in all four final zones before writing anything. The
second accepts only the exact first record plus the other three valid empty
headers. Each writer copies the fixed payload before metadata, orders every
commit, performs a full header-and-payload readback, never retries, never
clears, and never overwrites a nonempty slot. A failed ledger gate stops before
the next protected access.

Normal mainline ramoops registration is skipped only while this isolated
option is selected. Known-good Gemian is the read-only recovery path. The
recovered prefix has these decision branches:

| Recovered records | Interpretation | Next action |
| --- | --- | --- |
| neither | Observer entry was not established, or the exact ledger gate refused before any protected read | Keep both transports unattributed; audit earlier init ordering or the gate result through serviceable USB |
| before-clock only | The observer entered and the protected-clock call did not return before reset | Isolate the clock transport; do not invoke BigiDVFS in its successor |
| before-clock and after-clock | The clock call returned; failure is at or after BigiDVFS entry | Preserve the clock result and isolate BigiDVFS with its own terminal record |
| exact USB runtime completion | Both protected calls returned | Validate the existing strict runtime record and open composition only if every prior gate passes |
| malformed, duplicate, or foreign record | Attribution failed | Reject without transport inference |

## Live preflight

After the predecessor returned, a bounded read-only `/dev/mem` header check
from known-good Gemian found slots 171--174 at `0x444bb000`--`0x444be000` all
equal to raw bytes `444247430000000000000000`: little-endian signature
`0x43474244` followed by zero start and size fields. No memory write occurred.
This does not replace the candidate's own fail-closed DT/header validation.

The first installer preflight correctly stopped before candidate upload or any
storage write because its host-side raw-byte check had encoded the signature
in integer display order. A bounded read-only audit showed all four slots were
still valid and empty and exposed the required little-endian byte order. The
preflight and this record were corrected before deployment. See
[`results/deployment-attempt-1-preflight-validator-rejected.txt`](results/deployment-attempt-1-preflight-validator-rejected.txt).

The corrected deployment passed the empty-slot, live TEE, GPT, inactive-root,
power, predecessor, staging, write, sync, flush, and device-side full checksum
gates. Its final power sample then changed, so it stopped before the independent
host readback and shutdown. A resumed pass found the exact candidate already
present, skipped rewriting it, repeated the gates, streamed and byte-compared
the full 16 MiB, removed the temporary readback, and confirmed clean shutdown.
No fresh partition backup was made. See
[`results/deployment-attempt-2-write-final-power-gate.txt`](results/deployment-attempt-2-write-final-power-gate.txt)
and [`results/deployment-attempt-3-success.txt`](results/deployment-attempt-3-success.txt).

## Provenance

- Canonical parent ends at patch `0322`.
- Prepared parent source state is pinned in [`contract.json`](contract.json).
- Patch generation and compilation run on Buildbox from clean pushed commits.
- No native VM kernel build is permitted.
- The patch uses a synthetic, non-certifying experiment author with no DCO
  sign-off and is not submission-ready.

The first fully generated review bundle passed its automated source, replay,
and strict-style gates but was rejected during manual admission review: it
required the pre-LK derivative model string even though pinned LK rewrites the
runtime root model to `MT6797X`. It was not admitted, compiled, or used on the
device. The generator now pins the proven post-LK fingerprint instead.

Exact clean pushed commit `32e4874` then generated one patch. Source semantics,
patch replay, strict checkpatch, fetched-versus-admitted bytes, the 104-profile
canonical-series audit, and all eight invariant mutations pass. See
[`results/generation-32e4874.txt`](results/generation-32e4874.txt).

Exact clean pushed commit `36027e9` then built the isolated profile on
Buildbox with no modules. The fetched package passed its complete checksum
inventory and pins release `7.1.3-gemini-protected-readback-ledger`. Both
readback backends, the observer, and the call ledger are built in; all older
ledger options and all CPU8/CPU9 admission paths remain off. The candidate DTB
is byte-identical to the rejected predecessor. See
[`results/build-36027e9.txt`](results/build-36027e9.txt).

Two independent Android-v0 assemblies and two independent padding paths agree
byte-for-byte. The 7,639,040-byte raw container is `199e618a...c17`; the exact
16 MiB `boot2` image is `3ce494c9...715a`. All 32 LK gates pass, the serviceable
initramfs remains exact, and all six container mutations are rejected. See
[`results/candidate-199e618a.txt`](results/candidate-199e618a.txt).

The USB completion classifier and retained-record classifier now pass their
offline positive and mutation tests. The USB probe is read-only and makes no
partition, driver, CPU, reboot, or power request. See
[`results/runtime-tools-offline.txt`](results/runtime-tools-offline.txt).

On the one physical selection, mainline USB never appeared and the device
returned automatically to changed-boot-ID Gemian. Read-only recovery found no
pstore file and the retained classifier reported neither fixed record. A
direct bounded read confirmed all four final-slot headers remained valid-empty
and every sampled payload byte remained erased. `last_kmsg` was empty and the
full inactive `boot2` checksum still matched exactly. Therefore neither
protected transport was reached or tested; the remaining boundary is observer
probe entry versus refusal by the exact ledger gate. See
[`results/runtime-attempt-1-neither-20260821.txt`](results/runtime-attempt-1-neither-20260821.txt).

## Scope and safety

The only new runtime effects are at most two short writes to already reserved
persistent RAM under the standing retained-RAM diagnostic authorization. The
patch performs no storage, firmware, I2C, regulator, clock, CPU, timer,
watchdog, reset, or power operation. It adds no protected read, secure write,
automatic retry, owner registration, or CPU8/CPU9 request. The existing two
read-only protected calls remain the complete hardware-access budget.

Guarded installation still resolves logical `boot2` from the live GPT, verifies
it is inactive and unmounted, requires stable power, records the predecessor,
writes and fully reads back the exact padded candidate, and then shuts the
device down without rebooting. No fresh partition backup is required.

## Decision rule

Do not repeat this artifact. Preserve the kernel, DTB, initramfs, protected-read
budget, and all CPU/owner closures, but move the same two retained records to
`probe-enter` and `gate-passed`. The first must use only the minimum exact board,
reservation, and empty-slot safety gate; the second follows the complete
current ledger gate and immediately precedes the clock call. One successor
cycle must distinguish probe-not-entered, exact-gate-refused, and clock
nonreturn before any transport or composition claim is reopened.
