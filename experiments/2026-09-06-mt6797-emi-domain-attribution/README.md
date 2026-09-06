# MT6797 EMI domain attribution: bounded unresolved decision

The pinned public source explicitly calls policy field 0 AP and field 2 CONN.
It does **not** establish the active hardware routing of AP, CONSYS or WLAN,
nor the winning policy when regions overlap. No permission policy can be
selected from this investigation. This is the handoff required by the
[work contract](WORK_ITEM.md), not a hardware-support result.

## Verdicts and evidence classes

| Question | Observed source fact | Decision and missing link |
| --- | --- | --- |
| AP field | `ccci_platform.c:91` and the `MPU_ATTR_DEFAULT` column labels at line 129 call D0 AP. `emi_mpu.c:2196` implements `protect_ap_region()`, permitting D0 in region 23. | **Unresolved hardware routing.** Explicit source convention supports the intended D0 association, but no bus-domain assignment register, immutable routing specification or attributable transaction proves it. |
| CONSYS infrastructure | The same CCCI labels call D2 CONN. `emi_mpu.c:569` identifies `MST_ID_PERI_18` as CONNSYS, peripheral port 6, AXI-ID mask `0x1ffb`, value `0x3`. | **Unresolved hardware routing.** Master classification and domain labeling are separate source facts; no inspected code joins this master to D2. |
| WLAN master | CCCI region 18 is labeled Wi-Fi firmware, and its default permissions allow only D2. The frozen WLAN audit records the same final policy. | **Unresolved.** This is intended access policy, not proof that every WLAN firmware fetch/data access uses that CONSYS master or D2. AP-DMA, SPI-related CONNSYS traffic, and WLAN firmware traffic must not be conflated. |
| Overlap priority and applicability | `protect_ap_region()` requests all reported DRAM in region 23; WLAN/WMT requests occupy regions 18/19. No overlap/priority rule was found in the six inspected source files or the frozen secure-handler analysis. | **Unresolved.** Region-number order, software call order, or successful stores do not establish hardware arbitration or current active ranges. |

Every positive entry above is an observed source fact. Applying its intended
names to actual transactions would be an inference, and is deliberately not
accepted. No active mapping or priority rule was contradicted by a measurement,
because no such measurement exists in this item.

## Packed representation and register boundary

At the pinned revision, `emi_mpu.h:278` packs macro arguments D7 through D0
into three-bit fields, with D0 least significant. Its constants at lines
103–109 label 0 `NO_PROTECTION` and 5 `FORBIDDEN`. The independently written
[decoder](decode.py) extracts `(word >> (3 * field)) & 7` and checks reconstruction
by base-eight multiplication.

| Field | Bits | CCCI source label only | Region 18 `0xb6da2d` | Region 19 `0xb6da28` |
| --- | --- | --- | --- | --- |
| 0 | 2:0 | AP | 5 | 0 |
| 1 | 5:3 | MD1 | 5 | 5 |
| 2 | 8:6 | CONN | 0 | 0 |
| 3 | 11:9 | Reserved | 5 | 5 |
| 4 | 14:12 | MM | 5 | 5 |
| 5 | 17:15 | MD3 | 5 | 5 |
| 6 | 20:18 | MFG | 5 | 5 |
| 7 | 23:21 | MDHW | 5 | 5 |

The words differ only in D0 (`xor = 5`). The frozen
[secure ABI](../2026-09-05-mt6797-wifi-contract/RETAINED_EMI_SECURE_ABI.md)
traces low policy bits 23:0 to region-18 permission register `0x102003b0`
and region-19 permission register `0x102003b8`; their range registers are
`0x10200370` and `0x10200378`. It establishes whole-word transport, not a
per-field interpretation by the secure handler. This item reproduced the
retained file/window identities, not its disassembly or execution semantics.

The public `emi_mpu.c:854` violation decoder extracts the master from bits
15:0, region from bits 20:16 and domain from bits 23:21 of `EMI_MPUS`.
The domain switch selects distinct status registers for domains 0–7.
`__match_id()` separately compares the AXI ID and port against the master
table. Thus treating CONSYS port 6 as permission field 6 would confuse two
different quantities. Likewise APMCU channel ports 0 and 1 are not evidence
that AP transactions use both policy domains 0 and 1.

`devapc.c:707` extracts a master ID and domain ID separately from its own
violation status. The inspected DEVAPC header exposes PD violation/mask/debug
registers. These diagnostic paths do not supply the missing assignment from
the CONSYS/WLAN master to an EMI policy field. Running their handlers as an
inspection tool would also be inappropriate: the source includes status
clearing, while this work admits no device operation.

## Potential overlap inventory and its limits

The public `emi_mpu_mod_init()` calls `protect_ap_region()` at line 2345.
Region 23 covers `emi_physical_offset` through
`emi_physical_offset + get_max_DRAM_size() - 1`. Its D0..D7 request is
`[0,5,5,5,0,5,6,5]`. If the reserved WLAN/WMT interval lies within that reported
DRAM range, the request overlaps regions 18 and 19; the D0/D2 permissions then
conflict with at least one of those requests. This conditional source-level
overlap is consequential, but does not prove any of the requests took effect.

The frozen ownership record gives WLAN `[base,base+0x80000)` and WMT
`[base+0x80000,base+0x100000)`. They are adjacent, not mutually overlapping,
when the common base and size prerequisites hold. Their actual base is not
observed here. No historical base is substituted for current state.

The selected CCCI file defines the following region roles. Definitions and
array rows are inventories of intended roles, **not active-region receipts**:

| Region numbers | Source-defined role |
| --- | --- |
| 0, 1 | Secure OS, ATF |
| 2, 3, 4 | SCP OS, secure shared video, trusted UI |
| 5 | MD1 secure shared memory |
| 6 | No role macro in this block; a default array row exists |
| 7, 8, 9 | MD1 shared memory, MD3 shared memory, MD1/MD3 shared memory |
| 10–14 | MD1 MCU/HW read/write subdivisions and ROM/RW |
| 15, 16, 17 | MD log, MD3 ROM, MD3 RW |
| 18, 19 | Wi-Fi firmware, WMT |
| 20–22 | No role macro in this block |
| 23 | AP |

`MPU_ATTR_DEFAULT` declares 24 rows but explicitly initializes rows 0–20;
rows 21–23 are implicitly zero under C aggregate rules. Row 20 resembles an
AP policy while the active AP macro is 23; nearby comments also preserve old
region numbers. This is a source-maintenance hazard, not permission to assign
row 20 to AP or infer the runtime contents of rows 21–23. The separate
`protect_ap_region()` explicitly prepares its own region-23 word.

A complete active/default overlap inventory cannot be determined from these
sources: secure-world initial contents for regions 0/1 and other regions,
bootloader setup, runtime modem-image ranges, call/configuration reachability,
write results and subsequent agents are missing. The frozen secure handler
accepts regions 2–23 but is a setter, not a snapshot of their active contents.
Consequently none of regions 0–23 is ruled out as a possible additional
overlap by this item. No lowest/highest-region-wins rule is assumed.

## Frozen corpus and search inventory

All six fetched source files are from
[`lineage-geminipda/android_kernel_planet_mt6797`](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/tree/c5b0be85017ad0c599725e8273842efdbecdd88a),
commit `c5b0be85017ad0c599725e8273842efdbecdd88a`. Paths below are relative to
that repository. No other public revision was examined.

| Path | Bytes | SHA-256 |
| --- | --- | --- |
| `drivers/misc/mediatek/emi_mpu/mt6797/emi_mpu.c` | 93439 | `39921d80191b674940246425123b52fa140262a7e17022f90f02dd88389932b2` |
| `drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/emi_mpu.h` | 9747 | `a59c8a9a3e6fbb6889d131e23a413597f7bf5f188d82c4e953a66ce2a5aed68d` |
| `drivers/misc/mediatek/devapc/mt6797/devapc.c` | 29835 | `be1dae42f431ea8729a3101db7baa465df00769fec432a590f335f311ae18514` |
| `drivers/misc/mediatek/devapc/mt6797/devapc.h` | 4132 | `e12e80f10623c753626c9ae5f4b7efbd14036e9ad95fd7bca96a5b4c873f70b7` |
| `drivers/misc/mediatek/eccci/mt6797/ccci_platform.c` | 38764 | `d7092013b0fa14b12c37e96a973c3179c565c1a1e1ebef3a6c27ec38b566a156` |
| `drivers/misc/mediatek/eccci/mt6797/ccci_platform.h` | 2915 | `ea9bbefef867f8a097428bb2fc3bf336b767b4f1064dc2f554e1dfc11cb48fa7` |

Two unresolved branches each received at most two bounded search passes;
focused line reads and identity rechecks below refine those passes, not a
broader source corpus:

1. **Master/domain attribution, attempt 1:** EMI C/header and frozen ABI
   records; search `domain`, `master`, `CONN`, `APMCU`, permission macro and
   region-set symbols. Result: encoding, independent master/domain decoder,
   caller policy; no assignment chain.
2. **Master/domain attribution, attempt 2:** pinned recursive Git tree
   (`truncated=false`), filtered to MT6797 EMI/DEVAPC/CCCI paths, then only the
   four DEVAPC/CCCI files above; search domain/master/permission identifiers
   and inspect CCCI labels/table. Result: explicit D0/AP and D2/CONN intent,
   no concrete routing assignment; stop at the caller-intent boundary.
3. **Overlap/priority, attempt 1:** EMI C/header and frozen secure ABI;
   search `priority`, `overlap`, region-set calls and `protect_ap_region`.
   Result: region 23 all-DRAM request, setter behavior, no arbitration rule.
4. **Overlap/priority, attempt 2:** the same four DEVAPC/CCCI files, CCCI
   region definitions/default rows and call sites. Case-insensitive
   `priority|overlap` has no matches in all six files. Result: source-role
   inventory, incomplete active state, no priority rule; stop.

The first web fetch returned a cache miss; direct immutable raw URLs then
succeeded. Source bytes were streamed or held in memory, hashed, and discarded;
no source tree was downloaded. Negative searches cover this corpus only.

Machine-readable [inputs](results/inputs.json) freeze the six file-level
GPL-2.0-only notices, purposes, SHA-256 and Git blob identities, all used
sanitized record hashes, and private identity without a private path. The
recursive API index contains 59,243 entries, reports `truncated=false`, and
is pinned both by response digest and a canonical complete-inventory digest.
Its discovery-path list does not mean those additional files were fetched.

The [search record](results/search-attempts.json) contains exactly the two
branches above and two attempts per branch. Individual original UTC boundaries
and formal predeclarations were **not recorded**. They are null/unavailable;
the attempt descriptions are retrospective, not a claim that the later
contract's preregistration requirement was satisfied. Complete line-number
inventories were reproduced during repair at the recorded UTC times against
the same six frozen files, using explicit query-family regexes. These are
repair-time reproductions, not fabricated historical logs or new corpus
searches. This provenance limitation remains visible for integration review.
Each attempt's `query_corpus_source_ids` is exactly the source-file inventory
queried by its replay regex. `supporting_record_ids` identifies citation and
constraint inputs only; `supporting_records_queried=false` explicitly excludes
them from that query and its hit/no-hit inventory. The verifier checks each
supporting ID against the exact seven admitted records.

The [verdict record](results/verdicts.json) exposes the four independent
`unresolved` verdicts, evidence classes, identity-linked citations, missing
links, next discriminators and `policy_selection_allowed=false`.

All four contract record SHA-256 values were independently rechecked and
matched. The existing
[public-source ledger](../2026-09-05-mt6797-wifi-contract/results/whole-image-emi-sources.json)
was read for paths; its WLAN/WMT findings were not freshly re-traced. The
[July retained identity record](../2026-07-22-a72-firmware-power-contract/results/live-tee-identity-20260723.txt)
and [August mapping record](../2026-08-06-da921x-page-owner-audit/results/tee-owner-disassembly-20260806.txt)
were searched only for the existing private filename/mapping reference.

The RE VM already held the named retained TEE artifact; its private path is
omitted. It is 5,242,880 bytes with the contract
SHA-256 `2cd154f332ee72edb6dee431a68eb5f8b98b4dc05ee14e56591cfbffcf81a9b3`.
Read-only SHA-256 checks matched the frozen JSON for file windows
`[0x6148,0x61c8)`, `[0x66d0,0x6720)`, `[0x6720,0x6770)`,
`[0x62b4,0x62c0)` and `[0x13228,0x13254)` respectively (range/selector,
region18, region19, shared store, region table). The exact window hashes and
address mapping remain in the frozen
[ABI JSON](../2026-09-05-mt6797-wifi-contract/results/retained-emi-secure-abi.json).
No new disassembly was performed, so prior control-flow conclusions remain
attributed to that audit. The analysis shell was closed; no VM files or
databases were created.

Rights classification: public source is inspection evidence only; no source
code is reproduced or imported here and no new source-license reuse decision
is made. Retained TEE bytes remain private with redistribution unestablished.
Only hashes, register/field facts, symbol names and original descriptions are
included. Host usernames, private absolute paths, raw firmware and disassembly
are excluded. The decoder is independently written MIT-licensed arithmetic.

## Escalation and next discriminating checks

Stop reason: the two bounded branches establish source intent but not hardware
routing or overlap semantics, meeting the contract's explicit stop condition.
Repair attempts: none; this is an evidence investigation. No policy was chosen.

| Unresolved question | Next discriminating check, separately scoped |
| --- | --- |
| Does AP actually issue D0? | Obtain an exact MT6797 bus-domain assignment specification or trace retained initialization of its identified assignment register with complete field semantics. Compare the assignment with an already retained, attributable AP transaction/domain observation if one exists. |
| Does CONSYS actually issue D2? | Establish the assignment for the source-identified CONSYS AXI master, including bridge override/security attributes; a domain-named permission macro cannot provide this. |
| Which WLAN accesses use that master/domain? | Trace WLAN firmware fetch/data bus routing to the established CONSYS master or locate an attributable retained WLAN transaction with both master and domain decoded. Do not substitute host AP-DMA or SPI traffic. |
| Which overlapping region wins? | Obtain the exact MT6797 EMI region-match arbitration specification or independently attributable retained evidence that distinguishes opposing priorities. Then inventory all relevant active ranges/policies for an exact boot identity through a separately reviewed non-consuming read path. |

These are proposed evidence discriminators, not a device protocol or permission
to trigger faults, read MMIO, issue SMCs, clear violation status or boot a
candidate. A new scope is required before expanding beyond this corpus.

## Validation and handoff

Actual checks: four frozen hashes matched; six public full-file hashes recorded;
retained TEE whole-file and five window hashes matched; `python3 decode.py`
checked both expected arrays, reconstruction and changed-bit identity;
`git diff --check` and explicit `git diff --no-index --check /dev/null` checks
of both new files found no whitespace errors (exit 1 indicates new-file
differences). A focused new-file scan and manual review found no exposed private
identifiers, key material or personal absolute host paths. No shell source changed.
No kernel build, hardware
test, firmware execution, fresh capture, device SSH, commit or push occurred.
The integration owner runs the repository publication gate and appends any
accepted offline measurement to the shared ledger after review.

Repair validation: `python3 decode.py --online` passed both arithmetic vectors,
record shape/enums/citation checks, local frozen-record hashes, public whole-file
and Git blob hashes, file-level notices, complete replayed hit/no-hit lists and
canonical recursive-tree inventory identity. It holds public bytes in memory
only. The default invocation checks local records and arithmetic without
network access. Neither invocation accesses the private artifact or hardware;
the private identity check compares metadata against the frozen sanitized JSON.
The second review repair additionally pins the parent commit, repository and
tree URLs, API-reported identity, raw tree-response digest, exact six selected
tree entries, exact seven record IDs and exactly one private artifact identity.
Online verification checks both the raw response digest and API tree identity.
The strengthened offline and online invocations and Python in-memory
compilation passed. A regenerable review bytecode cache found during final
inspection was removed; no generated cache is retained.
After two unsuccessful repair reviews, the integrator explicitly escalated a
final bounded verifier repair. The verifier now embeds the exact seven
record path/hash pairs and independent canonical metadata digests for the
complete frozen source, record and private-artifact lists. Those expectations
are constants in code, not values derived from mutable input files at runtime.
They enforce the exact purpose and rights text, license notices, identities,
cardinality and fields before opening any referenced record path. Changing
metadata requires an explicit reviewed update of the frozen expectations.

The verifier explicitly requires false AP/CONSYS/WLAN routing predicates,
false overlap-rule/applicability predicates, the exact unknown runtime-region
state, and blocked policy selection. Arithmetic uses `require()` and therefore
remains checked under Python `-O`.

The independently written [refusal fixtures](refusal_test.py) operate only on
deep-copied dictionaries in memory. All 34 mutations were rejected with the
expected diagnostic, including a record path plus its otherwise correct hash
swapped to another admitted file, purpose/rights changes for each input class,
extra/missing records/artifacts/sources/tree paths, routing/priority predicate
promotion or omission, runtime-state promotion, and supporting/query inventory
violations. Unchanged controls passed before and after; original evidence was
unchanged. `python3 refusal_test.py`, `python3 -O decode.py`, and
`python3 decode.py --online` passed after this repair.

Changed scope: this README, `decode.py`, `refusal_test.py`, and the three JSON records under
`results/`, alongside the owner's work contract. Parent remains
`82405bb9eafb3af37cafb331e1bc0eaeb2518f3f`.
Review-ready timestamp: `2026-09-06T05:03:55Z` (observed UTC clock); start was
`2026-09-06T04:57:48Z` per the work contract, elapsed 6 minutes 7 seconds.
The integrator required the machine-readable records and verifier before
review; repaired handoff timestamp is `2026-09-06T05:09:34Z`. The first timestamp
is not an acceptance receipt. Exact repair-start time was not captured.
Second review repair: observed start `2026-09-06T05:13:09Z`, verification
completed `2026-09-06T05:14:52Z`; this remains a review handoff, not acceptance.
Escalated final repair: observed start `2026-09-06T05:17:02Z`, verification
completed `2026-09-06T05:20:11Z`. The 34 refusal cases also pass under Python
`-O`; both Python files compile in memory. Remaining hardware and historical
search-provenance limitations are unchanged.
Actual specialist route: Astra Medium. Credits and review/rework time are
unavailable to this worker. Remaining risks are the four unresolved verdicts
above, incomplete active-region inventory and unverified current firmware
identity; none is closed by arithmetic or compilation.
