# MT6351 VCN33 ownership evidence

Source and retained-binary follow-up, 2026-09-08. No device access, PMIC reads or writes.
The shared voltage selector is established; output-pin topology and the enable
combination logic remain unresolved. Do not copy the newer PMIC drivers'
enable-consolidation writes on the strength of register names alone.

## Pinned source

The inspected public Gemian tree is commit
[`8cfe6596a503612e3332d9c26e292a19525a7f07`](https://github.com/gemian/gemini-linux-kernel-3.18/tree/8cfe6596a503612e3332d9c26e292a19525a7f07).
Files were read from retained Git objects in the RE VM. This is a source
identity, not proof that its connectivity implementation is running on the PDA.
It differs from the Planet source revision used by the July regulator audit.
Its register header does match that audit's complete header SHA-256.

| Path below `drivers/misc/mediatek/` | SHA-256 |
| --- | --- |
| `power/mt6797/pmic.c` | `c08786d5ad44006d1fdc0f885e43f6ca1e9398f9c6e5e14c4ec6fe167e3d143c` |
| `include/mt-plat/mt6797/include/mach/upmu_hw.h` | `e376d2835dd32812b52caf6a51139cc7fd541de18eaad0f30ecf8194f70cebbe` |
| `connectivity/common/common_main/mt6797/mtk_wcn_consys_hw.c` | `0ec8e9c1594626d0b31f2d2623927d614f63af4437c16df838e10e11258663ce` |
| `connectivity/common/common_main/mt6797/include/mtk_wcn_consys_hw.h` | `3ee7631a95a12f5cddd860c213e51e75e1cb3146ca858a892aaae55b4d22fad1` |

## Established register and source facts

| Control | Header definition |
| --- | --- |
| Shared voltage selector | `0x0ada`, bits 10:9 |
| BT software enable | `0x0a98`, bit 1 |
| Wi-Fi software enable | `0x0a9a`, bit 1 |
| BT/Wi-Fi on-control fields | Bit 3 of their respective enable registers |
| BT/Wi-Fi source-clock selection | Bits 13:11 of their respective enable registers |
| Common reported VCN33 enable | `0x0a92`, bit 15 |

The selector table at `pmic.c:1404` maps raw values 0–3 to 3.3, 3.4, 3.5 and
3.6 V. Both descriptor entries at lines 1634–1637 use that one selector field.
Separate regulator handles therefore do not provide independent voltage
ownership. A successful write through either handle changes the field used by
both; the current draft has no cross-consumer voltage arbitration.

The connectivity header defines `CONSYS_BT_WIFI_SHARE_V33` as **0** and
`CONSYS_PMIC_CTRL_ENABLE` as **1**. The counter-based common BT/Wi-Fi helper at
`mtk_wcn_consys_hw.c:846–894` belongs to the disabled branch. Its presence is
not evidence that the common helper governs this platform.

The selected source branch has separate BT and Wi-Fi paths. Both request
3.3 V. Under `CONFIG_MTK_PMIC_LEGACY`, each path changes its own on-control
field and uses the vendor power API; the alternative uses separate regulator
handles. The retained-binary audit below identifies the compiled branch; its
execution on a given boot remains unobserved. Nearby comments cite older offsets that disagree with the
MT6351 header; they are not a register-address authority.

## Retained kernel control path

The [binary receipt](results/vcn33-binary-receipt.json) pins the retained boot
image, decompressed kernel, reconstructed ELF, five function spans and the
descriptor/operation/register tables. The boot image is the same historical
capture identified by the [RTC audit](../2026-07-11-mt6351-pmic-recovery/results/rtc-binary-audit-20260908.md).
Its gzip payload equals the retained `Image`, and the ELF's entire `.kernel`
section equals that image. Analysis used GNU AArch64 objdump 2.42 in the RE VM;
private disassembly is retained there. This does not establish the current boot.

Both compiled PALDO control functions select separate regulator handles.
For a nonzero enable argument and a non-null handle, each requests exactly
3,300,000 microvolts and then calls `regulator_enable()`. The disable path
calls `regulator_disable()` when its handle is non-null. Neither consumer
function contains the legacy branch's direct on-control writes or the disabled
shared-counter implementation. Comments describing a software-to-hardware mode
switch therefore do not describe an operation in these compiled consumers.

The two named descriptors reference the same operations table. Their enable
and selector fields, decoded at the offsets actually loaded by the callbacks,
join the compiled PMU table to `0x0a98` bit 1 for BT, `0x0a9a` bit 1 for Wi-Fi,
and the common `0x0ada` bits 10:9 selector. Both voltage-table pointers yield
3.3, 3.4, 3.5 and 3.6 V. This independently confirms the source register mapping
and shared selector in the retained kernel, rather than assuming its tables
match the public source.

The return path is not a hardware-success witness. Both consumer functions
return zero on every decoded path, including null handles and reported enable
failure; they ignore voltage-setting and disable results. The provider's
enable and voltage-selector callbacks also discard the PMIC setter result and
return zero. Its disable callback rejects a zero use count, but otherwise
discards the setter result too. Enable/disable read back the register without
comparing it or propagating the read result. These are compiled control-flow
facts, not evidence that a failure happened on hardware.

This narrows the next investigation to the physical output/control contract
and ownership of any mode/source-clock setup elsewhere. Do not repeat the
source-branch question or treat the legacy mode-switch sequence as the running
reference. The audit does not prove pin topology, enable combination logic,
current rail state or successful PMIC transport, and admits no rail experiment.

## Initializer and suspend-table follow-up

The [initializer receipt](results/vcn33-initializer-receipt.json) checks the
same retained kernel's `PMIC_INIT_SETTING_V1()` and its modem helper. All 245
direct configuration calls and nine flag-setting calls in the first function,
plus seven configuration calls in the helper, have locally resolvable register
arguments. None targets `0x0a92`, `0x0a98` or `0x0a9a`. The initializer does
write `0x0a94` bit 9, a separate VCN33 field; this is not a claim that startup
leaves every VCN33 register untouched. Other kernel, loader and firmware writers
remain outside this bounded audit.

The pinned source's `mt_power_gs_6351_array.c` contains the same three VCN33
triples in its flight-mode suspend, suspend and early-suspend deep-idle tables:

| Register | Comparison mask | Expected masked value |
| --- | --- | --- |
| `0x0a92` | `0x0004` | `0` |
| `0x0a98` | `0x000a` | `0` |
| `0x0a9a` | `0x000a` | `0` |

These describe expected mode-control, on-control and enable bits in those
named states. They omit the source-clock selectors and do not establish an
initialization sequence, observed register values or actual suspend behavior.
Thus neither these tables nor the two compiled initializers supplies the
missing mode/source-clock owner. Investigate other writers or obtain an
attributable, separately admitted observation; do not infer software ownership
from the golden values or copy them as a programming recipe.

## Retained LK initialization follow-up

The [LK receipt](results/vcn33-lk-init-receipt.json) pins a bounded audit of the
same retained loader used by the [modem-tail analysis](../2026-09-07-mt6797-cellular-upstream-architecture/LOADER_TAIL.md).
The routine identified by its caller's PMIC-initialization profiling message
calls two hooks that each return immediately. It then requests a full-width
read of `0x02b6` and returns zero without using the read result. The public LK
source has the same empty initialization/custom hooks and read sequence.
These hooks therefore do not supply the missing VCN33 mode/source-clock setup.

This is a selected compiled-path result, not a whole-loader writer inventory or
proof that LK leaves all PMIC state unchanged. The read wrapper's underlying
transport effects are outside this audit. Other LK consumers and earlier
preloader/firmware remain possible owners; the retained image also does not
attest the current boot. Do not repeat these empty hooks as a proposed source
of the missing rail contract. No current PMIC read or rail experiment occurred.

## Retained HIF wrapper follow-up

The [HIF receipt](results/vcn33-hif-wrapper-receipt.json) revalidates the retained
kernel and its reconstructed ELF, then pins the 152-byte `HifAhbProbe` and
40-byte `HifAhbRemove` spans. Their direct power calls are the already-audited
`mtk_wcn_consys_hw_wifi_paldo_ctrl(1)` and `(0)`, respectively. Neither wrapper
adds a direct VCN33 mode or source-clock operation. The matching gen3 source
places its direct `upmu_set_vcn33_on_ctrl_wifi` calls in the non-Device-Tree
MT6323 branch; those calls are not the compiled wrapper path in this image.
The source's hardware-mode comment beside the selected helper call therefore
adds no mode-setting operation to the earlier compiled PALDO result.

The probe wrapper ignores the PALDO helper's return. If the subsequent probe
callback fails, it invokes the remove callback and returns an error without a
balancing PALDO-disable call in this wrapper. The normal HIF remove wrapper
invokes that callback and then explicitly disables PALDO. This is a difference
between the two decoded paths, not proof of a leaked rail: the indirect
callbacks and caller-level unwind are outside this bounded audit. A future
power contract cannot assume that the failure branch locally balances its
request. This result supplies no current-boot, physical output or enable-logic
attribution and admits no rail or radio experiment.

The [retained late-registration follow-up](../2026-09-06-mt6797-wlan-common-lifetime-source-attribution/RETAINED_CALLBACKS.md)
confirms that this caller supplies no local compensating disable and can hide
the callback error behind a successful platform probe. Full unwind remains unproved.

## Decision

The common selector and common status naming support a shared analog-resource
interpretation, but they do not prove one output pin, two switched outputs, or
the Boolean relationship between the software and source-clock controls.
The [retained runtime summary](../2026-07-11-mt6351-pmic-recovery/results/runtime-pmic-repeat-20260714.txt)
reported both handles enabled at 3.3 V. That observation does not distinguish
those hardware models.

Keep the compile-only draft's shared-rail limitation open. A production model
needs an MT6351-specific output/control contract before choosing a common
regulator, aliases or separate output switches. The MT6358/MT6359 precedents
in the [topic record](README.md) do not supply that contract. This source audit
does not authorize enable-bit experiments, source-clock changes or radio use.
