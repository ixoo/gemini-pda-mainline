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

The separate command/ACK and shared-memory follow-up is outside this milestone
review. Ordered implementation work remains in the [roadmap](../../docs/ROADMAP.md).
