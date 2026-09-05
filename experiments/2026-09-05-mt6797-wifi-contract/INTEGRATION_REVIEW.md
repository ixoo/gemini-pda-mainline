# Wi-Fi milestone integration review

## Reviewed inputs and boundary

Project Planning reviewed milestone
`bbe78e38a3a089ec674a9106e2529ea20a14b04a` against integration parent
`3a570d8f`, including an independent read-only review. The original milestone's
18 files contain metadata collectors, a retained-firmware structure validator,
source analysis and sanitized evidence. They contain no kernel inputs or raw
firmware, calibration, credentials or partition images.

The independent reviewer found one additional code defect after the coordinator
identified the calibration-inventory wording issue. The review did not repeat
device access, private firmware inspection or the complete external-source
audit. Observed platform ancestry and MTKE structure remain within the original
evidence limits; neither establishes mainline networking or a loaded image.

## Corrections

1. The populated-SDIO branches used regex match subscripting, unavailable on
   Gemian's Python 3.5.3. They now use `group()`. Two regression cases exercise
   valid and contradictory populated inventories with group-only match objects.
   Both reject the original implementation with `TypeError`; the corrected
   implementation emits classification and completes its final identity check.
   This is host compatibility coverage, not a new Python 3.5 hardware run.
2. The original empty-SDIO receipt never entered the affected branch and remains
   unchanged. The presence helper's embedded source identity now refers to the
   corrected core. The [consumed session](SESSION.md) retains its original
   hashes and identifies the immutable milestone revision for reconstruction.
   Current helpers have no fresh physical admission or observation budget.
3. Calibration was excluded from the July firmware-file inventory, not from
   every project capture. The later private partition backup includes relevant
   configuration/protection partitions. Applicable retained data can be studied
   offline after integrity, identity and access checks; its format and regulatory
   applicability remain unresolved.
4. Shared hardware notes now distinguish selected gen3 GPLv2 host-source
   evidence from firmware rights and from SDIO-shaped vendor names. They link
   the new durable contract rather than repeating source hashes. The queue
   records the completed metadata packet as consumed/stale, with no candidate
   selected. A53 and active radio preparation have not become boot-ready.

## Validation and identities

The exact original milestone passed 40 ancestry, 15 presence and 55 firmware
synthetic tests in the coordinator's isolated temporary export; it was removed
after the run. The corrected ancestry suite passes 42 tests, the presence suite
passes 15, and the unchanged firmware validator retains its 55-test result.
Two compatibility regressions also fail as expected against the original core.

| Current helper | SHA-256 |
| --- | --- |
| `scripts/wifi_sysfs.py` | `78e9853cee0dcd6dd1ff876595904f80d52b9fd994aeefdc31cd8818b8e55934` |
| `scripts/parent_presence.py` | `5dc401ab6451eaca2ce0c7900acfd5cd6b58998dbb23262cb2f9a3311e4c3891` |

The original [host receipt](results/host-validation.txt) remains historical.
The common repository gate passed for the integration's changed files and all
189 profiles; Linux-only package provenance validation remains required in CI.
No kernel build is
needed because kernel, DT, configuration, manifest and patch-series inputs
are unchanged. No additional device or RE-VM action occurred in this review.

## Separate command/ACK follow-up review

After the milestone integration, Project Planning separately reviewed
`054b4ec830b7f6f849faca7b842a3a210dc01867` against `eb236d28`. Its six additive
files define a pure DOWNLOAD_CONFIG/CMD_RESULT model and shared EMI/remap/MPU
ownership requirements. Both coordinator and independent review found no
actionable defect within the documented source contract. The independent
reviewer ran all 36 tests against the exact committed modules; all passed.
Fresh retrieval of the vendor files failed during that review, so independent
verification of their recorded source hashes was not repeated. The worker's
source audit and its stated limits remain in the [follow-up](FOLLOWUP_HANDOFF.md).

This model handles already delimited records. It supplies no transport, loader,
PDA payload parser, device action or new readiness claim. The corrected core and
presence helpers, original receipts and consumed packet are preserved during
integration. Ordered work remains in the [roadmap](../../docs/ROADMAP.md).

## Separate calibration follow-up review

Project Planning reviewed the five additive files in
`ca4e114d697b03e5b7b846d3f1365050f1620c3c` against `a0ad5499`.
Coordinator and independent reviewer each ran all 23 synthetic tests; all
passed. Independent review verified the pinned layout, manufacture-version
checks, legacy power branch, firmware-version comparison and MAC predicate
against vendor source with matching recorded hashes. No actionable defect was
found. The review did not access private records or a device, reproduce the
backup-integrity receipt, or fully repeat the regulatory-table audit.

The [calibration contract](CALIBRATION.md) distinguishes retained-image integrity,
record structure, source compatibility and unproven board/firmware applicability.
Its pure inspector never emits raw inputs or grants loading/transmit authority.
Integration preserves earlier helper bytes and immutable receipts, links the
new source fact from the hardware contract, and keeps record producer/restoration
research in the roadmap. No candidate, physical readiness or hardware support
claim changes. No kernel inputs changed or kernel build was required.

The common publication gate passed for all nine changed files and all 189
manifest profiles. Earlier corrected collectors, consumed session and kernel
inputs remain byte-identical. Linux-only package validation remains a CI gate;
no hardware or private-record test was performed by integration.

## Separate storage-envelope follow-up review

Project Planning adopted the five additive files from
`99b6af9fe44dca1a0ebc057bfcd881ebc3f3183c`. Independent review ran all 26 new
storage and 23 unchanged record tests; all 49 passed. Both helper identities
and all three pinned public init/fstab source hashes match. The conditional
path mapping, strict size/trailer refusals, checksum-collision caveat and
independent version-context boundary agree with the published contract.
No actionable defect was found.

The review used only published sanitized files. It did not reopen private
captures, repeat the binary-derived producer interpretation or reproduce the
retained filesystem inspection; those remain investigator-attributed evidence.
The reviewed [provenance record](PROVENANCE.md) preserves the inconclusive
installed-configuration recovery and unproved board/firmware applicability.
Earlier helpers and immutable receipts remain unchanged. No kernel inputs,
hardware support claim, device custody, candidate or queue readiness changes.

The common publication checks passed, including all 190 manifest profiles.
No kernel input changed or kernel build was required for this integration.

## Separate INIT-session follow-up review

Project Planning adopts the four additive files from
`fcb1cb6b889fb738f8ac34e210d50f625982c246`. Independent review passed all
68 session/decoder tests normally and with Python optimization. A separate
exploration checked 8,865 traces, 25,914 transitions and 12,835 fixed refusals
without mutation. Serialization, deadline boundaries, completion attribution,
terminal failures and sequence bookkeeping had no actionable findings. The
recorded helper/document hashes match and the prior decoder is unchanged.
This review did not refetch the vendor sources or repeat their earlier audit.

The [session model](INIT_SESSION.md) remains a sequential host reference.
Deadline enforcement requires caller observations; sequence nonreuse applies
within one object; generation labels do not authenticate received bytes.
Real provider locking, transport completion, cancellation, stale-receive
handling and recovery remain implementation prerequisites. No kernel input,
shared-resource ownership, candidate, queue readiness or hardware support
claim changes. No kernel build or device action was needed for integration.
