# MT6797 CONSYS public-source ownership attribution

This bounded audit resolves the dynamic reservation producer at the source
allocation-API boundary. The other four ownership predicates remain unresolved;
they are not negative findings or permission to implement a provider.

## Frozen scope and result

The [work contract](WORK_ITEM.md), [inputs](inputs.json),
[request inventory](search-attempts.json) and [verdicts](verdicts.json) freeze
parent `d56c4d8763d2b11f0521b945e890a9a108dbe16e` and public Planet source commit
`c5b0be85017ad0c599725e8273842efdbecdd88a`. Source identity is recorded as immutable
raw URLs, whole-file SHA-256 and Git blob identity, tied to two complete recursive
API tree responses with matching hashes. There was no checkout, mirror or archive.

| Predicate | Verdict | Decision-changing boundary |
| --- | --- | --- |
| Dynamic reservation producer | Resolved, API-level source only | Generic reserved-memory allocation supplies base and size; CONSYS callback stores the base. |
| CONSYS power/reset owner | Unresolved | WMT requests clock/reset effects, but selected CCF dispatch and full resource lifetime are not joined. |
| WLAN-to-common handoff | Unresolved | Local firmware-buffer lifetime and common-to-WLAN callback edges do not prove retained common ownership. |
| Shared remap writer | Unresolved | OR/masked effects are visible; exact physical mapping and WLAN helper caller are incomplete. |
| EMI region-18 requester | Unresolved | Literal region18 reaches an outer wrapper; the actual secure adapter definition is outside the frozen corpus. |

### Observed boundaries

The declaration supplies size and alignment `0x200000`, `no-map`, and allocation
window `[0x40000000,0xc0000000)`. `fdt_init_reserved_mem` passes base/size outputs
through `__reserved_mem_alloc_size`; its allocation API requests allocation and
no-map removal, and the matching callback receives the initialized pair but stores
only the base. The allocation-API boundary is sufficient for this source claim,
not proof of live success, exclusion of a weak-function override, or a fixed
physical address. See verdict citations `declaration` through `callback`, including
the [allocator source](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/of/of_reserved_mem.c#L95).

WMT's power wrapper refuses a zero EMI base. Register control requests reset bit12
and the probe-acquired `conn` clock, but does not propagate its recorded clock
error at its final return. This cautions against treating vendor caller success
as successful hardware transition. See `power_entry` through `clock_effect_anchor`.

The local firmware buffer remains across `wlanAdapterStart` and is freed after
that call; adapter failure maps to `-EIO`. A nearby `request_firmware` variant is
disabled by `#if 0`. WMT invokes a WLAN callback and records a Wi-Fi state bit only
on success, but these separate observed edges are not a proved reverse handoff
or provider-reference lifetime. See `firmware_caller` through `common_callback`.

The common remap operation ORs base-derived low12 plus bit12 into the existing
register: it preserves all set bits and does not clear stale low address bits.
WLAN's remap helper preserves low16 while replacing its upper field. Neither
observation establishes synchronization, physical-address attribution or an
admitted shared-access policy. See `remap_caller` through `upper_remap`.

The downloader requests region18 over the first 512 KiB of the shared base. Its
outer EMI wrapper encodes the five-bit region in bits31:27, discards the adapter
return and returns zero; the downloader ignores that zero too. The secure macro
is not a proved connection to the missing adapter body. No secure-success or
raw-status claim follows. See `region18_request` through `secure_macro`, especially
the [outer EMI wrapper](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/emi_mpu/mt6797/emi_mpu.c#L1116).

## Search accounting and limits

The 32-file allowlist and four query batches were declared before semantic reads.
All 32 regular files count, including no-hit files. There are 41 retained successful
raw-response receipts: A seven plus one contextual reread, B fifteen, C ten and
D eight. An initial A command's output was lost at the result-capture boundary;
its seven attempted identities are preserved as receipt-unavailable, with unknown
HTTP outcomes and exact timestamps. They were repeated within A, not invented
as successful or no-hit records. Thus 48 raw opens were attempted across 32 files.
Two tree inventories are separately counted and contain no source bodies.

All reads stayed in the frozen allowlist. The already selected allocator function
received one contextual reread without following another reference. `memblock.c`
was included in A's whole-file keyword scan and file count, but no deeper memblock
implementation was interpreted or used to claim an effect. The coordinator
clarified the two-reference cap without expanding it: use an allocation-API effect
only with explicit base/size flow; otherwise retain unresolved. No new anchors
were used to evade this bound. The four batches are exhausted; no further source
search is implied by this handoff.

The next discriminators are recorded separately for each unresolved predicate in
`verdicts.json`. They require new frozen source scopes: selected clock/reset
dispatch, common/WLAN lifetime, remap mapping/caller, and the missing EMI adapter.
This experiment does not order roadmap work or authorize any of those tasks.
No incompatible complete chains were found; partial or disabled branches are not
promoted to contradictions. The pinned public source has not been established as
the exact running Gemian binary.

## Validation and rights

Run `python3 experiments/2026-09-06-mt6797-consys-owner-source-attribution/verify.py`
and repeat with `python3 -O`. The [verifier](verify.py) performs no network or
device action: it freezes complete evidence documents, checks input identities,
request/citation bounds and false-authority fields, then runs 11 in-memory refusal
fixtures. Hash checks deliberately reject co-mutated evidence claims; this is
integrity checking of a manually reviewed audit, not automated source semantics
or proof that a network request occurred. Review changes to its fixed pins.

Only independently written facts, necessary identifiers, paths and hashes are
stored. No source excerpts, binaries, firmware, private evidence, device identity
secrets or personal host paths are included. Inspection does not grant vendor
code/API reuse, firmware redistribution, Linux-owner establishment, policy
selection, runtime authority, device action or hardware support. All such flags
remain false. No hardware test, kernel build, Buildbox, VM or device access ran.

See [validation record](VALIDATION.md) for checks actually executed. The owner
retains integration, independent Sol review, workflow measurement and publication.
