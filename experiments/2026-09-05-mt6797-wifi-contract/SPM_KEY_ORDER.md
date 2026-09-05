# SPM key owner and CONN transition order

This narrow source decision follows `245c85e1a3c443607f4440b4ba900fae9d8c712c`
and the [provider-lifetime review](PROVIDER_OWNERSHIP.md). Exact public inputs
are in [the source ledger](results/spm-key-order-sources.json). No source tree,
vendor implementation, private observation or proprietary material is added.
No device, radio, register, VM or builder action was performed.

## Decision

The key belongs to shared SPM register control, not to a private CONN register.
The selected vendor sources write it at initialization and before transitions;
they do not establish that it is consumed by each transition or that clearing
it afterward is safe. **No audited upstream MT6797 owner supplies this write.**
Do not invent an existing Linux initialization guarantee, duplicate the SPM
mapping, or add a consumer-owned key write/restore pair.

The selected Planet and Gemian CCF sources agree on the CONN island order.
Their OFF sequence disables the domain clock before asserting domain reset;
the legacy upstream sequence does the reverse. A future CONN-specific ordering
capability in the existing provider has direct source support. Reordering all
existing upstream domains, or claiming the two orders equivalent, does not.
The shared key's retained-firmware contract still prevents an active CONN
implementation from being justified by this source decision alone.

## Shared register, several vendor callers

At the Planet pin, `mt_spm_reg_mt6797.h` identifies `POWERON_CONFIG_EN` as
SPM `0x10006000 + 0x000`, bit 0 as `BCLK_CG_EN_LSB`, and the high-half project
key as `0x0b16`. The combined write is `0x0b160001`. These are source-defined
fields and write semantics, not a measured current register value or a claim
that key bits read back unchanged.
[Register definitions](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/base/power/include/spm_v2/mt_spm_reg_mt6797.h#L264).

| Source path | Actual placement | Ownership implication |
| --- | --- | --- |
| `spm_register_init()` | Writes key plus bit 0 under `__spm_lock`; called by `spm_module_init()`, reached from MT6797 PM initialization outside its disabled legacy block | A shared SPM initializer already performs the operation in this vendor kernel; this is not an upstream initializer |
| `spm_poweron_config_set()` | Repeats the same write under `__spm_lock` | There is also a callable SPM-owner helper; its definition alone does not establish every runtime caller |
| Selected OF WMT ON branch | Writes key/enable after external reset assertion and before `clk_prepare_enable(conn)` | Even the API-enabled branch retains a direct shared-register write; it is not confined to the inactive fallback |
| `spm_mtcmos_ctrl_conn(state)` | Writes key/enable before branching to ON or OFF | CCF repeats the operation for actual island transitions; the same preamble occurs in other subsystem routines |

[SPM initialization](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/base/power/spm_v2/mt_spm.c#L703),
[PM caller](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/base/power/mt6797/mt_pm_init.c#L622),
[SPM helper](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/base/power/spm_v2/mt_spm_sleep.c#L1069),
[WMT preamble](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/mt6797/mtk_wcn_consys_hw.c#L328),
[CCF preamble](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/clk/mediatek/clk-mt6797-pg.c#L574).

Thus a requested ON is not necessarily a new CCF key write: the CCF wrapper
can return early when it already considers the island ON. The actual CONN
routine writes before either transition. None of these reviewed paths saves
and restores the prior key/control value. This is evidence for shared enable
state with repeated enabling writes, not proof of a one-shot unlock, required
per-transition refresh, harmless concurrent writes, or a safe disable policy.
The CCF wrapper's clock lock and the SPM helper's `__spm_lock` are distinct;
the source does not establish a single lock shared with WMT or retained firmware.
[CCF state check and lock](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/clk/mediatek/clk-mt6797-pg.c#L2278).

The existing upstream `mtk-scpsys.c` owns the MT6797 SPM power-domain mapping
and transitions, but contains no corresponding key/enable initialization.
The newer `mtk-pm-domains.c` and MT6797 clock driver do not supply it either.
The legacy provider is byte-identical at the upstream and v7.1.3 pins; local
patches 0047 and 0050 modify its MFG data/helpers, not this shared enable.
This is a scoped source finding, not an exhaustive proof about retained
bootloader or secure-world writers.
[Legacy provider](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/pmdomain/mediatek/mtk-scpsys.c),
[newer provider](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/pmdomain/mediatek/mtk-pm-domains.c),
[MT6797 clocks](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/clk/mediatek/clk-mt6797.c).

Two misleading matches are explicitly excluded. Historical local A72 code
named SPM `+0x218` as a power-on configuration register; that offset is the
MP2 reset/power control identified by the
[A72 contract](../2026-07-22-a72-firmware-power-contract/results/a72-firmware-power-contract-prerequisites-20260722.md).
Protected-clock code uses the same key value at **CSPM `0x11015000 + 0x000`**,
a different block. Neither establishes SPM `0x10006000 + 0x000` ownership.

## Which order is supported

The [earlier contract](POWER_DOMAIN.md#exact-island-controls) records the full
selected sequence. This comparison isolates the consequential differences:

| Point | Selected Planet/Gemian CCF | Legacy upstream | Conclusion |
| --- | --- | --- | --- |
| ON after both ACKs | Clear clock-disable, clear isolation, release SPM reset, release protection | Same order, with SRAM helper before protection release | Core ON order agrees; zero SRAM masks still cause a register access in the legacy helper |
| OFF after protection ACK | Set isolation, set clock-disable, assert SPM reset | SRAM helper, set isolation, assert SPM reset, set clock-disable | Clock/reset order differs; there is no equivalence proof |
| Power requests | Separate primary then secondary writes, both ACKs polled | Same request order and dual-ACK intent | Matching source sequence, not hardware validation |
| Delays and failures | No explicit island delay; unbounded ACK loops | Bounded polling and error returns | Do not import infinite loops or infer rollback from a timeout |

[Planet CONN sequence](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/clk/mediatek/clk-mt6797-pg.c#L574),
[Gemian comparator](https://github.com/gemian/gemini-linux-kernel-3.18/blob/d388d350cb2dda8f23b99be6fa5db9628896e87f/drivers/clk/mediatek/clk-mt6797-pg.c#L565).
Their agreement is corroboration between related public source trees, not an
independent hardware experiment or exact attribution of the retained binary.

The compiled-out OF WMT fallback adds a one-microsecond ON delay and uses an
OFF order of reset, isolation, clock-disable, delay, then one combined request
clear. It also uses the rejected protection mask described in the earlier
contract. It cannot justify adding that delay, combining the request writes,
or changing the selected CCF order. The outer selected WMT delay after the
CCF call is a different boundary and remains part of outer preparation.
[Inactive OF fallback](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/mt6797/mtk_wcn_consys_hw.c#L635).

## Smallest supported direction and unresolved acquisition

For island ordering, the smallest source-supported change is an opt-in
per-domain capability in the existing SCPSYS OFF callback that places
clock-disable before reset assertion. Keep existing domains' order unchanged;
select it only with a separately reviewed CONN domain. This decision does not
add that capability or select a domain, and does not settle prerequisite
retention or subsequent-use failures from the provider-lifetime review.

For the shared key, do not implement an unconditional new write or restoration
from this evidence. The concrete missing attribution is the retained boot and
secure-firmware behavior at **SPM `+0x000`**, separate from CSPM: which owner
sets or clears bit 0, when that state can be lost, and whether the normal-world
provider may re-enable it while those owners are active. A bounded static audit
of the existing retained kernel's CONN/SPM routines and boot/secure-firmware
writers is the next acquisition needed to attribute the source paths. If that
cannot establish the contract, a documented register contract or separately
admitted observation is needed; no register experiment is authorized here.
A single sampled enabled bit would not prove write ownership or lifetime.

The already-published
[runtime metadata](../2026-07-12-connectivity-wmt-recovery/results/runtime-summary.txt)
establishes vendor provider/resource presence, not a key-write trace or ordering
experiment. Retained local metadata was reviewed privately; its inspection
record stays under ignored, restricted artifacts. No raw retained binary was
analyzed in this item and no private finding is promoted into this public
source decision. In particular, there is no claimed proof that LK leaves the
SPM enable set or that the upstream provider may rely on it across suspend.
