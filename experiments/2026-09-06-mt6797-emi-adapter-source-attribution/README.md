# MT6797 EMI adapter source attribution

The missing adapter-source edge is closed. All four predicates are resolved for
the pinned public source and its named configuration—not for the deployed kernel
or current secure firmware. The adapter passes through a narrowed secure result;
the outer EMI wrapper is the layer that discards it.

## Frozen evidence

The [work contract](WORK_ITEM.md) pins parent
`cb035d7f8b9f782b1b8b1139352621fe2a38c025` and public Planet commit
`c5b0be85017ad0c599725e8273842efdbecdd88a`. The [input inventory](inputs.json)
records two complete tree responses, the allowlist frozen before source reads,
whole-file Git/SHA-256 identities, and the five exact predecessor/ABI documents.
The [attempt ledger](search-attempts.json) records every request, timestamp,
query hit and inspected context locator.

There were two predeclared batches, 10 distinct regular files, 11 successful raw
requests and two body-free tree requests. The adapter was opened once in each
batch; it counts once in the union. There were no request failures, source
mismatches, unavailable receipts or repairs. No source checkout, archive,
mirror, VM, binary analysis or source-body file was created.

## Findings

| Predicate | Verdict | Exact source boundary |
| --- | --- | --- |
| Adapter definition | Resolved | EMI Makefile selects `emi_reg_rw.o`; its definition is tied to the MT6797/ARM64/MTK_PSCI public configuration. |
| Secure-call mapping | Resolved | Adapter → `emi_mpu_smc_set` → `mt_secure_call`; concrete identifier and x0–x3 argument positions. |
| Adapter return semantics | Resolved | Updated x0 is converted to `int`; adapter returns it unchanged; outer wrapper discards it. |
| Region18 end to end | Resolved | Frozen WLAN region18 request reaches packed x3 and the identified lost-status boundary. |

The parent MediaTek Makefile gates `emi_mpu/` on `CONFIG_MTK_EMI_MPU` and supplies
the platform include path. The EMI Makefile selects `emi_reg_rw.o`. The named
`lineage_gemini_defconfig` sets MT6797, `MTK_PLATFORM="mt6797"`, ARM64,
MTK_PSCI and EMI_MPU. The selected adapter's PSCI branch directly returns the
secure macro. Its no-PSCI fallback returns zero without issuing that call; this
conditional alternative is not a second selected definition. See exact
`build_*`, `config_*`, `header_include` and `adapter_body` citations in
[the verdict record](verdicts.json), including the
[adapter definition](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/emi_mpu/emi_reg_rw.c#L74).

The direct chain has only two references from the adapter anchor. At its end,
the MT6797 ARM64 secure wrapper specifies:

| Register | Value |
| --- | --- |
| x0 | `0x82000209` |
| x1 | Original 64-bit start |
| x2 | Original 64-bit inclusive end |
| x3 | Packed unsigned region/permission word |

The source uses the literal `0x82000209` even in its ARM64 function. A comment
describing a 64-bit call is not authority to substitute `0xc2000209`. The updated
x0-bound variable is explicitly converted to `int`; the adapter propagates this
value, with no errno mapping or preservation of the full 64-bit raw result. See
`secure_id`, `secure_macro`, `secure_arguments` and `secure_return`, including
the [selected wrapper](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/mt_secure_api.h#L46).

The predecessor's exact WLAN requester citation supplies literal region18 and
first-half-MiB bounds. Its source hash and locator are checked against the frozen
predecessor records without another WLAN source open. The freshly inspected outer
wrapper masks permissions to 24 bits and encodes region18 in bits31:27,
contributing `0x90000000`. It forwards original bounds and the packed value to the
adapter, ignores the returned status, and returns its own zero. Both predecessor
region18 requests share this path. See `outer_pack_and_drop` and the explicitly
pinned predecessor citation; an outer zero is never evidence of secure success.

## Limits and handoff

No incompatible complete chains were found. Build-selection evidence is not a
build, linker-wide uniqueness proof or effective/deployed configuration check.
The source cast establishes the vendor narrowing boundary, not a portable C
implementation or validation of compiler-generated inline assembly. No runtime
raw value, secure effect, firmware lock, domain assignment, current selector,
reservation lifetime or shared-remap synchronization was observed.

The [retained ABI constraints](../2026-09-05-mt6797-wifi-contract/RETAINED_EMI_SECURE_ABI.md)
and [original arithmetic helper](../2026-09-05-mt6797-wifi-contract/EMI_ABI.md)
remain separate evidence: this audit reopens neither firmware nor their tests.
Their signed-low-word/full-raw distinction agrees with the identified source
boundary, but historical firmware identity does not establish today's firmware.

All nine authority flags remain false, including deployed adapter, current secure
firmware compatibility, vendor API/code reuse and Linux-owner establishment.
Source-level resolution does not admit policy selection, runtime use, a device
action or hardware support. The other CONSYS ownership gaps remain with their
owning experiments. Next discriminators in `verdicts.json` are bounded handoff
conditions, not an ordered roadmap or permission to begin adjacent work.

Only independently written facts, necessary identifiers, relative paths and
opaque whole-file identities are stored. No vendor implementation, source
excerpt, firmware, proprietary document or private device evidence is included.
There was no device, SMC, MMIO, kernel build, Buildbox or publication action.

## Reproduction of local checks

Run `python3 experiments/2026-09-06-mt6797-emi-adapter-source-attribution/verify.py`
and repeat with `python3 -O`. The [offline verifier](verify.py) pins every evidence
record, caps, identities, exact citation keys and all false-authority fields;
22 in-memory mutations must be refused. These checks protect the integrity of
manually interpreted evidence. They are not independent proof of network requests
or source semantics, and changing the verifier's fixed pins requires fresh review.

Checks actually run, timestamps and remaining integration steps are in
[the validation record](VALIDATION.md). Sol review, shared-file integration,
workflow measurement and publication remain with the coordinator.
