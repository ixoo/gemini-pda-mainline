# Retained VCN28 mode-control ownership

The retained kernel confirms a separate VCN28 on-control operation in the
common connectivity power wrapper. It is outside the regulator enable vote,
so a regulator-only sequence cannot reproduce this reference. Source-clock
selection and the physical control logic remain unresolved; this is not a
programming recipe or admission of a new rail experiment.

## Compiled producer and setter

The [receipt](results/vcn28-binary-receipt.json) pins the same retained
Image/reconstructed ELF used by the [VCN33 audit](VCN33.md), four function
regions and the actual PMU table entry. Complete Image/ELF hashes and kernel
section equality were rechecked in the RE VM. This establishes retained
compiled behavior, not the current boot or successful PMIC transactions.

In `mtk_wcn_consys_hw_reg_ctrl`, the first argument selects on/off and the
second supplies `co_clock_type`. On with the second argument zero calls
`pmic_set_register_value(1758, 1)` before requesting 2,800,000 microvolts and
regulator enable through the non-null VCN28 handle. A nonzero second argument
skips that VCN28 setup. The mode request precedes the handle null check, so
an absent regulator handle does not suppress that request.

Off calls `pmic_set_register_value(1758, 0)` after clock disable/unprepare and
before the optional VCN28 regulator disable. It does not test the second
argument before these VCN28 operations. Thus the source's conditional on-path
must not be interpreted as a matched conditional release policy.

The PMIC wrapper calls `mt6351_set_register_value`. Its table lookup uses a
12-byte stride, verifies the entry index and loads register/mask/shift from
that entry. Index 1758 resolves to `0x0a0c`, mask 1, shift 3. It reaches
`pmic_config_interface`, then sets its return to zero without preserving the
transport result. The common caller also does not test the mode-setting
return before continuing. These operations prove requested field writes,
not achieved hardware state.

The standalone `mtk_wcn_consys_hw_vcn28_ctrl` uses the same regulator-handle
slot and requests 2.8 V plus enable, or disable. Its compiled body makes no
on-control or source-clock selection request. It returns zero even for a null
handle or an enable error. Calling it is not equivalent to executing the
common wrapper's mode transition.

## Source-clock boundary

The pinned Gemian header, whose complete digest is in the receipt, names
`0x0a0c` bit 3 as VCN28 on-control, bits 7:5 as source-clock mode selection,
and bits 13:11 as source-clock enable selection. The inspected compiled
on-control requests have mask 1 and shift 3; they do not select those other
fields. The source labels value 1 as hardware control, but this audit does
not establish the signal truth table or the selected source-clock inputs.

Rejoining the previously decoded initializer call inventories to their
reverified binary regions and PMU table found no `0x0a0c` target in
`PMIC_INIT_SETTING_V1` or `PMIC_MD_INIT_SETTING_V1`. This is limited to those
two routines. It does not exclude other callers, boot firmware, defaults or
later writes and does not identify the source-clock owner.

## Integration consequence and validation

Keep on-control state with the shared power owner, separately from consumer
regulator references. Do not equate an enable count with mode ownership or
infer that a successful vendor return confirms a transition. The
[CONN provider direction](../2026-09-05-mt6797-wifi-contract/PROVIDER_OWNERSHIP.md)
still needs an attributable source-clock/control contract and error-aware
retention. The independently unresolved [VCN33 topology](VCN33.md) is unchanged.

Validation decoded the selected bodies and table entry, checked nine key
instruction encodings, reverified both initializer region hashes, and checked
the source-file identities. Raw disassembly remains private in the RE VM.
No source tree or binary was copied into Git. No device access, PMIC read/write,
radio action, kernel build or hardware test occurred.
