# eMMC admission handoff — preparing, execution disabled

Reviewed against published HEAD
`ba2ed13207f1a83654275b54882fe911828b4c20`. This is a bounded offline
handoff, not conditional readiness, physical selection or permission to connect.
The packet's runtime facts remain null. The queue and roadmap retain their
existing ownership; this document adds no ordering or repeat requirement.

## Completed offline boundary

The private launcher and completion adapter implement fixed custody/admission
checks, immutable one-shot claims, exact generated commands, bounded existing
transport reuse and classification from manifest-bound raw snapshots. They join
the same prepared candidate with the actual shared first-baseline archive
verifier; neither a stored success JSON nor a reopened successful replacement
can supply acceptance. The 17 launcher and 20 completion tests passed normally
and optimized, including ordering, timeout/interruption, source drift, snapshot
races, recovery distinctions and export-directory durability.

The published guard fixture passed all 52 exact ARM64 BusyBox/QEMU cases once
at source `4038246fe16effe1ef3a18eebce85e441029c36d`, in 61.183 seconds.
Accepted receipt `emmc/guard-shell-exact.json` SHA-256 is
`4743d51e1720763361fcdfba127ce56f18b1e56f6380e0d73f6e9176b1b7e4d5`;
its attribution, transport result and cleanup are in the owning experiment's
[GUARD_SHELL_RESULTS.md](GUARD_SHELL_RESULTS.md). This closes exact guard-before-body and dispatch
checks only. Full original pre/post programs were syntax-checked; executed
bodies were fixed sentinels. No real observer, logger, target baseline body,
SSH-to-device or physical recovery ran in that fixture. Existing exact observer,
baseline body, logger/helper and authenticated-session receipts keep their
separate scopes and must remain bound to the selected candidate/package.

The private scripts remain at their approved staging paths. Their current
location checks refuse execution here. Those checks are **not a durable
production disable**: merely moving them to their intended production names
would satisfy that location condition. Any later source promotion requires a
reviewed unconditional disabled gate until runtime/admission wiring is accepted.
Nothing is moved or enabled by this handoff.

## Runtime admission predicates — all still unfilled here

1. **Accepted prerequisite:** one first authenticated baseline of the same exact
   candidate has accepted intended/rejected-key checks, separated console/logs,
   CPU0–7 serviceability with CPU8/9 offline, PWRAP/supplies/MMC observations,
   complete independent logger preservation, reviewed ordinary native recovery
   and attributable changed-ID known-good confirmation. Bind its admission,
   deployment, baseline/confirmation manifests, candidate bytes and three boot
   identities through the shared verifier and retained `C.prepare` result.
   A planned recovery, a single successful frame or ten unreviewed cold boots
   cannot replace this proof; ten cold boots are not a prerequisite.
2. **Exact selected artifact/deployment:** retain the validated package and raw
   candidate manifest, kernel/DT/config/initramfs identities, exact member
   hashes (including observer, BusyBox and logger helpers), raw and padded
   images, reviewed guarded installer, live-GPT boot2 install/full-readback
   receipt and independently bootable known-good recovery. Source/classifier
   or candidate changes require fresh review; this handoff selects no artifact
   and requests no installation or rebuild.
3. **New owner session:** one named custodian explicitly admits this one read,
   confirms stable power, exclusive custody, no concurrent device operations
   and one physical boot2 selection of that deployment. The new authenticated
   mainline boot ID must differ from the accepted first baseline and its
   recovered boot. Intended key/host pins are checked locally and immediately
   before transport; no ambient SSH configuration, fallback identity or retry
   substitutes for authentication. Quiet RAM-only operation and the observer's
   full live namespace/storage/topology guards must hold throughout.
4. **Logger and serviceability:** the candidate's original logger is live before
   each pre/read/post body, with exact helper hashes, nonsymlink evidence files,
   no terminal markers and matching held process/executable identity. Before
   and after observations must pass the existing baseline classifier on the
   same new boot. Owner-visible console acceptance remains an independent fact.
   A live guard is not continuity proof: seal/export must later establish a
   complete sequence-zero-through-seal log, no gaps/overflow/parse failure and
   no matching controller errors anywhere in that independently retained log.
5. **Timing and final recovery:** schedule pre/read/post and the separately
   admitted seal within the one logger's original 600-second, 2 MiB lifetime.
   The 130-second observation ceilings plus 30-second seal ceiling do not reset
   its clock or bound owner delay; no remaining-lifetime guarantee is inferred
   from a live guard. A missed deadline cannot pass final coverage. Once the
   observer transport is stopped, separately admit preservation, then ordinary
   native recovery only after verified complete local preservation. Finally
   require owner-confirmed physical recovery, the known-good host pin and one
   authenticated changed-ID probe. Its boot ID must differ from the eMMC boot,
   first baseline, prior recovered boot and original deployment OS boot.

All candidate/package/deployment pins, prerequisite raw archives, current
custody/power/physical selection, current boot, owner console, observation,
logger preservation and final recovery facts above must be actual evidence.
The completed exact guard receipt is offline evidence, not a value for those
runtime fields or proof of the entire target adapter.

## Once-only actions and ceilings

| Action | Independent claim and effect | Transport ceiling / stdout |
| --- | --- | --- |
| Observation admission | Fixed global attempt consumed before any connection; changing UUID or rebooting cannot renew it | Three connections total |
| Preflight | One existing baseline observation, then accept its new boot ID | 45 seconds / 128 KiB |
| Read | Exact candidate observer once; live-GPT boot2 offset 0–16777215, 32768 sectors; input-only dd to hash | 40 seconds / 8 KiB; inner dd deadline 20 seconds |
| Postflight | One existing baseline observation of that same boot | 45 seconds / 128 KiB |
| Preserve log | Separately admitted one seal/export using reviewed generator/parser | 30 seconds / 3 MiB |
| Request recovery | Separately admitted one native request; no chained confirmation | 15 seconds / 128 KiB |
| Confirm recovery | Separately admitted one known-good authenticated probe after owner confirmation | 15 seconds / 128 KiB |

Every stderr ceiling is 16 KiB. Existing transport cleanup accounting remains
unchanged. Each phase/action exclusively creates its fixed claim before
connection; handled failure or interruption consumes it, retains partial
streams and stops. The device's consumed RAM directory is not cleared for a
retry; a reboot does not renew the host experiment budget. No storage write,
mount, extra read, load/thermal operation, CPU8/9 admission, logger restart or
new generic transport is introduced. The 16 MiB count is software-requested
payload, not measured physical-media traffic or health/performance proof.

## Refusal and recovery outcomes

- Missing/drifted admission, candidate, prerequisite, custody, source or host pin
  refuses before its next dispatch. Failed preflight prevents the read; any
  failed, incomplete or interrupted read prevents postflight. Do not retry.
- Complete nonzero read status, wrong digest or targeted controller errors fail
  the bounded claim. Lost authentication, timeout, incomplete framing, missing
  continuity or insufficient attribution is inconclusive. Preserve the consumed
  state and review it; neither outcome authorizes another observation.
- Successful pre/read/post gives only `read-serviceability-only-pass`. An
  attributable sealed observation archive can support separate preservation
  even after a handled failed read. Missing manifest or failed/unattributable
  preflight refuses this adapter's remote completion route; recovery outside
  it needs separate review and must not invent a boot identity.
- A terminal failed logger may still have all available evidence preserved;
  that can permit ordinary recovery but cannot pass complete coverage. A
  partial/unavailable export needs the existing separately admitted emergency
  reason and explicit acknowledgement of possible unique RAM loss. Timeouts
  supply no acknowledgement and never trigger an automatic recovery action.
- Final `one-read-emmc-and-recovery-pass` requires all read/serviceability,
  full-log, zero-error, ordinary-recovery, owner-console and changed-ID evidence.
  Valid known-good confirmation without those complete proofs is only
  `recovered-with-emmc-incomplete`; emergency recovery cannot upgrade the result.

## Exact source pins and minimal publication

These seven reused contracts are checked by the private `source-pins.json`:

| Source relative to the parent experiment | SHA-256 |
| --- | --- |
| `baseline/scripts/collect-baseline.py` | `efbca1e464e04005d3b7d503742b426eb9f642140ec289c40bc43563852208cf` |
| `baseline/scripts/finish-baseline.py` | `f6fc5cf6a73518385af714b4f8566e32e4b231338cf231b0204d0b5aa96564a0` |
| `baseline/scripts/session_steps.py` | `762616bb386647e0a25addd36ad9dba2f6384ebde4858f89a806a32678fc60fc` |
| `baseline/scripts/verified_baseline.py` | `ba70f6df476283c0113d433ae856940cc9c031f864019da95f014324e16c926e` |
| `emmc/classify.py` | `0be35e88eb3868e515d2185932519d0fb878260eced50f336e6dde301983acc3` |
| `emmc/guarded_observation.py` | `5fe4472b3ed61812cc05b6662decac89f6799d81de06def4f8bae51cb920317d` |
| `emmc/observe.sh` | `dbdf6a7c07c9ad895e75e8dc83b229567da7b22e92d905f284ff43208d902e31` |

The private launcher SHA-256 is
`8b504987889a48ee11ffb1581428ae699f8d155aeadb43150ba912767ffd5072`;
completion SHA-256 is
`2c7f633ad8f20bcf720361590abc6ca7653e64d86515d5e503bdd321fcb9a2c4`;
source-pin inventory SHA-256 is
`b66ea41b84bb4e86837910df271f6a1f744f9e676377b935db2105bb56852b3a`.
Guard fixture source remains
`eb02e660f779c34fe4b0c75beccd79ce5a621211b522166022c7bbf24cc5f284`.
Admission binds exact launcher/pin bytes; completion additionally binds its own
source bytes. Present tracked V/G modules must match these pins; private
fallbacks are fixed to the approved stage and reject symlinks or drift.

This record publishes only the contract, source pins and test summary. The
executable drafts, private manifests/fixtures, runtime placeholders, credentials,
candidate images and raw logs remain excluded. Source-only executable promotion,
a durable disabled gate and admission acceptance remain a separate reviewed
item. This document changes no queue readiness, selects no candidate and
requests no action.
