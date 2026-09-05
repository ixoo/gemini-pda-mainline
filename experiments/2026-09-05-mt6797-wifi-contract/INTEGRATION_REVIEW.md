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
