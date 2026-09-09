# Conditional successor: harmless disconnect proof

Status: **dependency verified; fresh boot-specific admission still required; execution disabled**.
The [first-session result](RESULT.md) passes the console observation. The existing
reviewed supplemental verifier confirms changed-ID Gemian return while preserving
the original incomplete SSH-disconnect witness. Its exact dependency pins are in
[session-result.json](session-result.json); the strict aggregate is not relabelled.
This is the test after [SESSION.md](SESSION.md), on a separate owner-selected
boot of the exact same [validated candidate](validation.json). It does not
extend that first session's budget. No device action occurred during preparation.

## Dependency and frozen inputs

First require the complete console-ownership baseline: authenticated USB,
CPU0–7 online and CPUs8–9 offline, matching input/map identity, three null PID-1
standard descriptors, owner-confirmed readable screen, three authentication
probes, complete bounded log preservation and changed-ID Gemian recovery.
Retain the raw archive and supplemental descriptor observation. A failed or
inconclusive prerequisite stops this successor; Candidate R's consumed records
cannot supply it.

The candidate's raw boot hash is
`7dfc3b1f771a12b8e711f699cf8fcfd2678aedc15bc9d8bcc98554f9c6654cdb`;
its padded hash and manifest remain those in validation.json. Reuse its guarded
installer and credentials. At the later attended handoff, revalidate live GPT
boot2 and full-partition identity, skip an already matching image, and follow
the existing clean-shutdown/physical-selection path. Keep Gemian running while
the owner is unavailable.

The separate enabled monitor package is pinned to revision
`93e2b8526daa683c2ba848011fac757a398a13dd`, inventory SHA-256
`0baad6b85ae68770b783245e2f1dcd7eeb4ef40d93c19e0b30e1f89f8adc3065`.
This is distinct from the candidate's baseline userspace package.

- Monitor: 66,672 bytes, SHA-256
  `4363a7d61d818bc443d5cfd76455ac38fc2cea35178d44a2dc81c229ff97b67f`.
- Harmless probe: 66,760 bytes, SHA-256
  `560d00ab80040b90fead5d0a5b2672ed633f62599aa483ff0a33be0fa74d3681`.

The existing validated package was fetched/revalidated through
`baseline/scripts/buildbox_userspace.py --keyboard-monitor-enabled --fetch-only`
with that revision and inventory. Every package member, exact inventory and
provenance passed; its enabled entry and monitor source match current sources.
No build or candidate modification is required. The current exporter includes
fixed-stage refusal diagnostics; its source hash and complete transitive source
identity are recorded in [next-session-preparation.json](next-session-preparation.json).

## Hypothesis and unique observation

After the console inheritance repair, losing one authenticated no-PTY client
while the harmless probe child is alive permits bounded terminal/reaped cleanup
and a complete empty reader scan. Unlike the first session's three PID-1
metadata observations, this tests cancellation and all process descriptors.
The probe opens neither evdev nor a VT. A pass is a disconnect result, not
keyboard coverage or proof of usable keyboard input.

## Admission and finite sequence

Use the existing [disconnect runner](../2026-09-05-owner-away-experiment-preparation/keyboard/disconnect.py)
and [semantic verifier](../2026-09-05-owner-away-experiment-preparation/keyboard/prerequisites.py).
No synthetic admission or future success receipt is supplied by this packet.

1. After the dependency passes, allocate one custodian and fresh admission IDs.
   On the next physical selection, admit one bounded authenticated identity
   observation using the existing identity/RAM guards (12 seconds, 1 KiB stdout,
   16 KiB stderr, one claim, no retry). Record the actual fresh boot ID, exact
   candidate identity and owner screen confirmation. Missing identity stops
   proof admission. The boot must differ from the dependency's mainline and
   Gemian boot IDs.
2. Fill the runner's exact admission inventory with the actual boot ID,
   completed-baseline archive, current source identity, frozen package and
   binary identities, and six actual custody facts. Call `prepare()` offline
   to reparse the complete archive and package; a CLI dry-run alone does not
   validate them. Freeze both generated command bytes and their hashes.
   Publish the exact boot-specific binding only after these checks; the
   current disabled/null binding remains unchanged during this preparation.
3. Execute one proof connection with a two-second host bound. Deliver only the
   pinned probe into its guarded once-only RAM directory. Run its fixture child
   in `ignore` mode. Kill only the local SSH process group after complete stdin
   and the exact child marker, with at most 100 ms marker-to-kill latency.
4. Use the sole independent export connection: 30 seconds, 278,528 bytes stdout,
   16 KiB stderr, no retry. Wait at most two seconds for outer exit 2. Require
   a complete scan of at most 512 processes and 4,096 descriptors, with no
   surviving probe/observer or console, tty0, tty1 or input descriptor. Preserve
   the exact four RAM files and all local transport output. The verifier must
   accept the seven fixed evidence files, terminal/reaped child, permitted
   signal/order and scaled 500 ms lifecycle limits before a pass is recorded.
5. Disable the consumed binding. Preserve/seal this boot's logger once using
   its existing 600-second lifetime, 2 MiB cap and 30-second export budget.
   After unique evidence is preserved and live identity and recovery-tool
   identity pass, use the separately admitted reviewed native recovery path
   and require changed-ID known-good Gemian confirmation. No keyboard capture
   is included, even after a passing proof.

Every phase requires its actual admission and one-use claim. A failed phase
never grants extra transport connections. Recovery is a separate operation;
this proof runner cannot request it.

## Decisions and preservation boundary

- Complete transport, semantic cleanup evidence and empty reader scan: record
  a scoped pass. A later keyboard session still needs its own admission and
  same-boot prerequisites; this boot's proof receipt cannot be transferred to
  another boot.
- Contradictory lifecycle or surviving reader: record failure and retain all
  evidence. Diagnose that observation before selecting another test.
- Missing or truncated transport, framing, inventory or files: record
  inconclusive, including the new fixed-stage stderr diagnostic if available.
  Neither absence of output nor null PID-1 descriptors establish reader release.

The strict exporter can still refuse before emitting files. On refusal, retain
all local partials and leave the remote RAM tree intact. Stop before recovery
and review a separately bounded fixed-file preservation action using the
existing [preserver](../2026-09-05-owner-away-experiment-preparation/keyboard/preserve-disconnect.c).
That action needs its own exact live admission; this packet does not silently
add a bootstrap, retry, scan bypass or permission to discard unique RAM.
If preservation or live identity cannot be established, recovery remains gated.
The historical Candidate R result stays inconclusive.

## Offline verification

On 2026-09-08, seven disconnect host fixtures and six prerequisite fixtures
passed, including binding refusal, deliberate client loss, export diagnostics,
framing and contradictory lifecycle rejection. The exact ARM64 exporter
fixtures already passed as recorded in validation.json; they were not rerun
for this documentation-only preparation. Package integrity and source matching
were rechecked. No actual future baseline archive, boot identity, custody,
Dropbear cancellation or reader-release result exists yet.

Use the [updated recovery semantics](RECOVERY.md) for the next session: an old
SSH timeout after the complete request does not require a supplemental recovery
review. Actual changed-ID Gemian confirmation remains required. The earlier
source-identity snapshot in next-session-preparation.json is historical; compute
the current closure before the fresh boot-specific admission. The completed
first-session dependency still verifies without changing its original result.
