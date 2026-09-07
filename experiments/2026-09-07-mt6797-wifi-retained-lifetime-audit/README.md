# Experiment: retained MT6797 WLAN lifetime evidence audit

## Record

| Field | Value |
| --- | --- |
| Status | accepted bounded no-evidence stop |
| Parent | `2af9532b3b1c1850cfa071a0f279154127a04db1` |
| Device | Existing named Gemini; no live access |
| Investigator | Astra Medium; accepted after Sol Medium review |
| Date | 2026-09-07 |

## Verdict

No inspected record proves any of the five runtime predicates joined to one
successful WLAN firmware-load/shutdown cycle. The result is a bounded absence
of suitable evidence, not proof that the hardware cannot work or that no such
record exists outside this search. No implementation or observer is admitted.

The [frozen contract](WORK_ITEM.md) fixes the scope.
[Inputs](inputs.json) pin 15 committed records, including all seven contract
inputs, which were hash-verified before the audit. [Inventory](inventory.json)
records the private search boundary; [matrix](evidence-matrix.json) separates
observations, source facts, missing joins and limitations.

## Five-predicate assessment

| Predicate | Existing evidence | Runtime result |
| --- | --- | --- |
| DMA API address versus source/destination/ADDR2 | Static register and forced-bit attribution | Missing joined programming observation |
| Endpoint translation and EN/INT_FLAG progression | Static aperture/polling protocol; runtime HIF activity | Missing transfer-specific progression |
| Positive idle before release | Static timeout/stop uncertainty | Missing idle-before-unmap witness |
| Firmware-stop completion | Common WMT loader fallback and source callback paths | Missing WLAN stop completion |
| Coherent CONSYS OFF | Source and retained static clock-before-reset order | Missing executed shutdown effects |

The July runtime summaries show interface/driver presence, HIF thread activity
and BTIF DMA counters. Their post-reboot common WMT patch-loader success does
not identify a successful WLAN image load plus shutdown. BTIF is not the WLAN
AP-DMA channel. The passive mainline record has a named generation and zero
effect counters; it cannot supply an active lifetime observation.

The common-lifetime source audit contains a late-registration counterexample
to uniform resource acquisition. Vendor/static CONN ordering differs from the
older upstream ordering. These are retained source distinctions, not
conflicting observations of one runtime cycle. There is no accepted cycle
identity, success predicate or temporal join across the five rows.

## Bounded private inventory

The repository evidence was insufficient. At 19:18:28 UTC the approved
explicit RE-shell path performed one filename/stat-only inventory on the
already-running RE VM. It examined 697 file entries after directory pruning:
20 excluded filenames, 25 nonregular entries and 652 other metadata-only
entries. No filename matched the plausible text/log selection rule.

No private body was opened, no candidate was selected and no term count or
selected-file hash is claimed. File type here means regular/nonregular stat
classification, not a content/MIME test. The 20,000-entry inventory cap was
not reached; the 30-record/10-MiB body-read caps were unused. Symlinks were not
followed. The receipt records the exact filename and exclusion rules.

No raw private output was produced or exported, so no guest scratch child was
created. This is an explicit procedural limitation relative to the dispatch's
scratch-child wording; the contract's conditional raw-output retention rule
had no raw output to retain. No alternate private access method was attempted.

Pruned directories, nonmatching filenames, and separate historical capture
stores were not inspected. In particular, public references to private capture
hashes do not imply that their raw files were opened. The result cannot be
generalized to all private stores or hidden evidence.

## Next discriminator and safety

The single next discriminator is a separately frozen and independently reviewed
non-replayed observation protocol joining the five predicates to one successful
WLAN load/shutdown cycle. Its acquisition effects, shared ownership, finite
budget and recovery must be settled before use. This audit selects no concrete
mechanism. The owner-closed retained-instruction observer/checker remains closed.
A normal successful cycle would still not prove fault retention or safe teardown.

Only this experiment's assigned output files were created. No device, radio,
firmware, tracing, register, binary-decoding, database, network lookup, build,
VM-configuration or private-evidence mutation occurred. No raw proprietary
excerpt, personal identifier or private path is reproduced here.

The verifier tests frozen receipt integrity and input identity, not hardware
semantics or the completeness of filename-based discovery. See
[the freeze](FREEZE.md) and [actual validation](VALIDATION.md).

Independent Sol Medium review accepted the packet at
`2026-09-07T19:32:12Z` without rework. It independently verified all 15 input
identities, the five missing runtime joins, the exact 697-entry inventory
accounting, zero private body reads, conditional scratch handling, privacy and
effect limits, local links and both 238-mutation verifier runs.
