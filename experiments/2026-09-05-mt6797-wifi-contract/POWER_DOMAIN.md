# MT6797 CONN power-island and provider admission contract

This bounded investigation follows
`fcb1cb6b889fb738f8ac34e210d50f625982c246`. It resolves the concrete CONN
register sequence and tests whether existing upstream power-domain mechanisms
can represent it. **The island data fits, but adding that data alone would
activate CONN during SCPSYS probe, before its independent reset and rail
preparation.** No kernel patch, speculative DT node or new session framework
is added. The outcome is the exact provider operation needed before such a
topic is defensible, with separately identified sequencing/rollback gaps.

The Wi-Fi workstream owns this investigation; Orchestrator owns shared
integration, manifest/series admission and future Buildbox scheduling. Work
used the existing topic worktree, public pinned source and already-published
retained observations. No device, private input, VM or builder was accessed.
No new acquisition, Linux tree, firmware or vendor implementation was stored.
The eventual upstream destination is the MediaTek generic power-domain
provider, coordinated with reset/regulator owners; there is no submission or
DCO certification in this slice.

## Inputs and actual selected path

| Input | Pin and role |
| --- | --- |
| Current upstream | Linux `4d7d9486c04d917265f64c55bd23b2cc4fe7749c`; still the master endpoint at this audit, timestamp `2026-09-05T02:36:11Z` |
| Selected vendor source | Planet `c5b0be85017ad0c599725e8273842efdbecdd88a`; selected Gemini defconfig, WMT wrapper and MT6797 clock provider |
| Independent source comparator | Gemian `d388d350cb2dda8f23b99be6fa5db9628896e87f`; its MT6797 clock provider corroborates the island masks and sequence |
| Retained named-device evidence | [Connectivity summary](../2026-07-12-connectivity-wmt-recovery/results/runtime-summary.txt) identifies `mtk_wmt`, `SCP_SYS_CONN` and four VCN supplies on Gemian `3.18.41+`; this is not a trace of individual power transitions |
| Local kernel inputs | Manifest-selected Linux 7.1.3 plus local patches; neither the manifest nor any series/profile is changed or treated as pristine current upstream |

The Planet header enables the power API, PMIC and AFE paths, and disables
`CONSYS_AHB_CLK_MAGEMENT` (the source's spelling). The selected defconfig uses
OF/common clocks, not `MTK_CLKMGR`. DT clock `"conn"` resolves to
`SCP_SYS_CONN`, clock-binding
number 2. The provider's internal `SYS_CONN` number is 1; these are different
namespaces. Its `pg_conn` has no parent or preclock. The executed path is
`clk_prepare_enable(conn)` through the power-gate operations to
`spm_mtcmos_ctrl_conn()`.
[WMT selection](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/mt6797/include/mtk_wcn_consys_hw.h#L39),
[DT mapping](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/arch/arm64/boot/dts/mt6797.dtsi#L3767),
[provider registration](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/clk/mediatek/clk-mt6797-pg.c#L2526).

The inactive direct-register fallback uses bus-protection bits 18/19. The
executed provider uses **bits 17/18**. Its generic descriptor contains zero
for the protection mask because custom CONN operations supply the real mask.
Neither the fallback constants nor that zero may seed upstream CONN data.
The [Gemian provider](https://github.com/gemian/gemini-linux-kernel-3.18/blob/d388d350cb2dda8f23b99be6fa5db9628896e87f/drivers/clk/mediatek/clk-mt6797-pg.c#L565)
independently agrees with the active Planet mask and island sequence. The
Gemian tree's corresponding DT is `mt6797.dts`, not the Planet `.dtsi`; no
matching common MT6797 WMT implementation was established from that pin.

## Exact island controls

All entries describe source semantics, not a newly observed register state.

| Resource | Physical base / offset | Meaning |
| --- | --- | --- |
| SPM register-control enable | `0x10006000 + 0x000` | Vendor writes key/enable value `0x0b160001`; shared SPM access authority must be established |
| CONN power control | SPM `+0x32c` | Reset release bit 0, isolation bit 1, power requests bits 2/3, clock-disable bit 4 |
| Dual power status | SPM `+0x180`, `+0x184` | CONN bit 1 in both registers |
| CONN SRAM | No executed field | Request and ACK masks are both zero |
| Bus protection | INFRACFG `0x10001000 + 0x220`; status `+0x228` | Mask `0x00060000`, bits 17 and 18 |
| Independent CONMCU reset | TOPRGU `0x10007000 + 0x18` | Bit 12, key `0x88000000`; distinct from SPM control bit 0 |
| CONN2AP sleep mask | TOPCKGEN `0x10000000 + 0x1350` | Bit 8, controlled by the surrounding WMT owner |
| MCU readiness preparation | `0x18070000 + 0x110` | ACR bit 18 before external reset release |

The active island power-on sequence is: enable SPM register control; set
primary then secondary power request; wait for both ACKs set; clear
clock-disable; clear isolation; release domain reset; clear protection and
wait for both protection bits clear. Off reverses the power intent:
enable SPM control; assert/ack protection; set isolation; set clock-disable;
assert domain reset; clear primary then secondary power request; wait for
both ACKs clear. There is no CONN SRAM transition or explicit delay inside
this selected routine.
[Provider definitions and sequence](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/clk/mediatek/clk-mt6797-pg.c#L574).

## The outer owner is not a power-domain data field

The selected WMT wrapper requests VCN18 at 1.8 V, waits 240 microseconds,
conditionally requests VCN28 at 2.8 V for `co_clock_type == 0`, sets the sleep
mask, and asserts CONMCU reset before invoking the island. Afterward it waits
30 microseconds (not the nearby 10-microsecond comment), checks chip identity,
programs MCU/AFE state, releases CONMCU reset and sleeps 20 ms. Its chip-ID
loop permits ten attempts separated by 20 ms after misses, but its unsigned
post-decrement mishandles exhaustion. Clock/regulator failures are logged
without reliably stopping this path; the wrapper ultimately returns zero.
[Outer sequence](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/mt6797/mtk_wcn_consys_hw.c#L291).

The retained [configuration summary](../2026-07-12-connectivity-wmt-recovery/results/wmt-config-summary.txt)
records `co_clock_flag=0`. That is configuration evidence, not proof of the
runtime function argument or physical oscillator wiring. The optional AHB
clock branch is disabled in the selected source and must not become an
invented mandatory preclock.

TOPRGU's keyed reset update is serialized by its watchdog/reset provider.
SPM reset release cannot substitute for CONMCU reset. A normal implementation
must hold the independent reset across island activation until preparation
has succeeded, and must propagate failure before releasing it.
[Selected reset helper](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/watchdog/mediatek/wdt/mt6797/mtk_wdt.c#L396).

Local [patch 0090](../../patches/v7.1.3/0090-watchdog-mtk-expose-MT6797-TOPRGU-resets.patch)
already describes TOPRGU CONMCU bit 12; it is an existing
integration input, not a new reset provider to duplicate. Local MT6351
[patch 0015](../../patches/v7.1.3/0015-regulator-mt6351-add-regulator-driver.patch)
describes VCN rails, but its ordinary enable/voltage operations do not
provide the wrapper's VCN28 hardware-control selection. Its VCN33 BT/Wi-Fi
entries also share one voltage selector while exposing distinct enable
controls. Those are concrete regulator-owner coordination questions; the
power-domain driver's single optional supply cannot replace them.

The WMT, WLAN and existing power owners also share the windows described in
[OWNERSHIP.md](OWNERSHIP.md). Reuse the existing SPM, infracfg and TOPRGU
providers. A second whole-window mapping or a whole AP-DMA reset would create
resource conflicts. Local patches
[0047](../../patches/v7.1.3/0047-pmdomain-mediatek-add-MT6797-MFG-domains.patch)
and [0050](../../patches/v7.1.3/0050-pmdomain-mediatek-use-MT6797-MFG-52MHz-preclock.patch)
separately extend MFG SRAM offsets
and preclocks; they neither implement nor admit CONN.

## What current upstream can represent

The currently bound `mtk-scpsys.c` supports the `0x32c` control offset, dual
bit-1 status at the MT6797-selected `0x180/0x184` offsets, and mask `0x60000`.
Its masked infracfg update/poll uses the required `0x220/0x228` registers.
Zero SRAM masks are representable, although the helper still performs an
unchanged-value write and a read. No new SRAM or bus-protection algorithm is
needed for these fields. The generic CONN offset constant `0x280` belongs to
another layout and must not be substituted.
[Upstream data and helpers](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/pmdomain/mediatek/mtk-scpsys.c#L122),
[infracfg helper](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/soc/mediatek/mtk-infracfg.c#L28).

The existing power ABI occupies IDs 0–11, including GPU IDs 6–10 even where
raw upstream domain data has gaps. A future CONN binding must append an ID;
it must not reuse a GPU slot or reinterpret the vendor clock-binding ID.
[Binding identifiers](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/include/dt-bindings/power/mt6797-power.h).

Upstream enables basic clocks before power requests and supports one optional
regulator. Missing supply permits operation; it is no prerequisite gate.
There is no CONMCU reset consumer or outer multi-rail/readiness sequence.
Its off order sets isolation, asserts reset, then disables the clock; the
selected provider sets isolation, disables the clock, then asserts reset.
Interchangeability has not been proved. Neither audited upstream provider
establishes the vendor SPM key/enable operation's ownership.
[Power transition implementation](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/pmdomain/mediatek/mtk-scpsys.c#L303).

## Concrete missing operation: registration without initial activation

The enabled MT6797 SCPSYS provider unconditionally calls `power_on()` for
every domain during registration, before a consumer requests it. Keeping a
future Wi-Fi node disabled or omitting its supply does not suppress this.
An initial power-on failure becomes a warning and registration continues.
Therefore a bare CONN data patch would itself add hardware operations at
probe. That is the decisive reason no such patch is prepared here.
[Registration path](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/pmdomain/mediatek/mtk-scpsys.c#L516).

The missing normal-provider capability is to admit a consumer-prepared domain
without invoking its initial power callback. Its initial-state contract must
explicitly distinguish the two power ACKs:

| Primary ACK | Secondary ACK | Required treatment for a future admission change |
| --- | --- | --- |
| 0 | 0 | May establish an initially-off genpd without a CONN transition, subject to owned/stable observation and the remaining prerequisites |
| 1 | 1 | Do not blindly adopt or declare off a possibly firmware-owned domain; require attributable handoff or refuse/withhold admission |
| 0 | 1 | Inconsistent/transitioning state; refuse before domain registration or power callbacks |
| 1 | 0 | Inconsistent/transitioning state; same refusal |

This is a proposed acceptance contract, not executable policy or a claim
that the named device is currently off. A prospective change must place the
check before registration/power side effects and return an actionable error.
The legacy registration helper is currently void and continues after errors;
merely adding a boolean around its callback is insufficient. Whether to
reject the whole provider or withhold only CONN affects existing multimedia
consumers and must be resolved explicitly. The current baseline must not
lose those domains because a newly added CONN prerequisite is unresolved.

The newer `mtk-pm-domains` driver provides `MTK_SCPD_KEEP_DEFAULT_OFF` and
available-DT-child selection. MT6797 does not bind to it and is not in its
binding schema. That flag warns when a domain is already on but still
initializes genpd as off; it is not arbitrary-state adoption or a proof of
ownership. Moving MT6797 to that driver is a provider/binding migration, not
an existing capability toggle for the current node.
[Newer initialization](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/pmdomain/mediatek/mtk-pm-domains.c#L985),
[binding scope](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/Documentation/devicetree/bindings/power/mediatek,power-controller.yaml).

## Failure handling and evidence still required

| Failure boundary | What the source establishes / what remains |
| --- | --- |
| Vendor ACK/protection wait | Power ACK loops are unbounded; protection counts 20,000 iterations then calls `BUG()`. Neither supplies recoverable timed failure. Mixed ACKs can be mistaken for off by vendor state detection. |
| Upstream power-on error | Clocks/regulator are disabled, but power, isolation/reset and protection state are not reconstructed. A returned error is not successful rollback. |
| Upstream power-off error | The function returns with possible partial state and no restoration of its initial state. Protection helper writes also do not propagate all regmap errors. |
| Outer preparation failure | Do not infer that dropping rails or releasing reset is safe. The wrapper does not provide a usable transactional unwind, and its shutdown omits an explicit CONMCU reset assertion. |

The discriminating evidence is now specific: the boot path's owned SPM
register-control state, coherent initial CONN ACK/reset/protection state, and
documentation or attributable implementation evidence for the shutdown-order
difference and partial-transition recovery. Existing published captures
identify providers/resources but do not establish those facts. A retained
boot-source or private-capture observation may resolve them; this record does
not authorize a new register probe or device session.

This leaves a concrete kernel destination and admission behavior to implement,
with the island data already determined. It does not wait for A72, a new
baseline boot or calibration history. The [roadmap](../../docs/ROADMAP.md)
alone orders the remaining work. No candidate, device readiness or hardware
support is promoted.

## Reproduction and validation

The [machine-readable contract](results/conn-power-domain-contract.json)
records selected masks, ordering, representability and source identities.
Re-fetch its public pinned raw files, verify SHA-256, follow the selected
defconfig/header/DT/provider call path, and compare actual operations with
the cited upstream functions. This requires no Linux tree or private input.
The inspected implementation/header sources carry GPLv2-compatible notices;
only independently described facts are included from DT files without an
explicit grant in their header.

[Validation](results/conn-power-domain-validation.txt) records the executed
source, schema/consistency, publication and independent review checks. No
kernel code, binding, DT, config, manifest or patch series changed, so no
kernel build, checkpatch or DT-schema execution was required. This is a
source/retained-evidence contract, not hardware validation.
