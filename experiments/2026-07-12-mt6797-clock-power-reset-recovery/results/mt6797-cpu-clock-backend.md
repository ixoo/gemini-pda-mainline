# MT6797 CPU clock backend and ownership boundary

## Status

Source-recovered and suitable for a disabled-only mainline design. No clock,
PLL, divider, secure monitor, regulator, or device state was written.

## Provenance

The primary source is the pinned Planet MT6797 tree at commit
`c5b0be85017ad0c599725e8273842efdbecdd88a`. The companion analyzer is
[`analyze-cpu-clock-backend.sh`](../scripts/analyze-cpu-clock-backend.sh); it
uses `git show` directly and never copies the vendor tree into this
repository. The Linux comparison is the VM's Linux `7.1.3` source tree.

The analyzer's source identities are:

| Source | SHA-256 |
| --- | --- |
| vendor `drivers/misc/mediatek/base/power/mt6797/mt_cpufreq.c` | `9a04aa630a262737cb7ca11d4c71d2815c9ad47b9308612aa98edbbf00de724c` |
| vendor `drivers/misc/mediatek/freqhopping/mt6797/mt_freqhopping.c` | `6f4165bdedd7ec318eb35e48fbc7da35967edb1af3729e47feb2537d944ac2a4` |
| vendor `drivers/misc/mediatek/base/power/mt6797/mt_idvfs.h` | `7c0e142b4a61ef89f432195e779c9a3408a8b25282732dad9a0eb98be96cfd68` |
| vendor `drivers/misc/mediatek/base/power/mt6797/mt_idvfs.c` | `7232f5ba7347511d97da6947c6833811b439d3116f95a13e631be40d7033b2e7` |
| vendor `drivers/clk/mediatek/clk-mt6797.c` | `d4bc12ed162488b1df787eaf5a97364f080b0c847d57188686514b0cb11e1473` |
| vendor `drivers/clk/mediatek/clk-mt6797-pll.c` | `6afd16d5eda26f70c48c10e88f78e167cd393735a812755556d130a5b4d8fbdb` |
| Linux `drivers/clk/mediatek/clk-mt6797.c` | `aea5041078556536d0bac36fb76e5b3fcd2746fbae78c4a730c70fae0ab76b4a` |
| Linux `drivers/cpufreq/mediatek-cpufreq.c` | `2b251ca6a28525619e8bf2fd13064836df7b07beec8e571ae5a85652f91fb56d` |

The Linux source checkout has no usable Git `HEAD` identity in the VM, so the
Linux file hashes and reported kernel version are the reproducibility anchors.

## Recovered clock map

The vendor cpufreq path identifies four logical clock consumers:

| Consumer | PLL window | Mux field in `ARMPLLDIV_MUXSEL` | Divider field in `ARMPLLDIV_CKDIV` | Backend |
| --- | --- | --- | --- | --- |
| LL (A53) | `0x200/0x204/0x208` | bits `3:2` | bits `9:5` | ordinary ARM PLL register path |
| L (A53) | `0x210/0x214/0x218` | bits `5:4` | bits `14:10` | ordinary ARM PLL register path |
| B (A72) | backup window exists at `0x230/0x234/0x238`, but active path is special | bits `1:0` | bits `4:0` | secure BigiDVFS path for PLL and SRAM LDO |
| CCI | `0x220/0x224/0x228` | bits `7:6` | bits `19:15` | ordinary ARM PLL register path |

The common divider register offsets are `ARMPLLDIV_MUXSEL = 0x270` and
`ARMPLLDIV_CKDIV = 0x274`. Divider selectors are vendor-encoded (`1 → 8`,
`2 → 10`, `4 → 11`) and the vendor waits about 2 µs after a divider change.
The ARM PLL math is a good candidate for reuse from the generic MediaTek CCF
helper: a 26 MHz parent, post-divider bits `26:24`, PCW bits `20:0`, change
strobe bit 31, and about 20 µs PLL settle time are present in the source.
Reuse of that math does not imply reuse of the register access path.

## Cross-owner protection is part of the hardware contract

The vendor `mt_freqhopping.c` source maps MCUMIXED at `0x1001a000` (4 KiB)
and protects all access to the CPU PLL/divider window there with DVFSP/CSPM semaphore register
`0x11015000 + 0x440`. It enables the CSPM internal clock using `0x0b160001`,
waits up to 2000 µs, disables local IRQs, takes a kernel spinlock, and then
performs the read/write before releasing the hardware semaphore. The source
explicitly says that ATF, SPM, and the kernel share this ownership boundary and
that all `0x1001axxx` clock access must use the wrapper API.

This is stronger than an ordinary CCF spinlock. A mainline provider that maps
the CPU PLL registers and performs direct `readl()`/`writel()` would race secure
firmware or SPM and is not a safe port of the vendor behavior. The provider
must either establish an upstreamable semaphore/ownership mechanism or expose
the clocks read-only until that mechanism is proven.

## B-cluster secure path

The B cluster does not use the ordinary ARM PLL write path in the vendor
cpufreq code. It calls BigiDVFS for PLL frequency, post-divider, SRAM-LDO, and
cluster control operations. The ARM64 vendor header assigns secure-monitor
services in the `0xc20003b0`–`0xc20003c1` range, plus secure read/write services
`0xc200035f`/`0xc200035e`. The implementation accesses secure offsets including
PLL PCW `0x102224a4`, PLL enable/post-divider `0x102224a0`, SRAM selector
`0x102222b0`, and control `0x10222470` through those services rather than
ordinary Linux MMIO. The vendor range checks allow PLL output from 250–3000 MHz
and SRAM-LDO requests from 50000–120000 in its `mV × 100` units.

Therefore B-cluster support needs a separately documented firmware binding and
an SMCCC-facing backend. It must not be represented as a normal writable CCF
ARM PLL until the secure monitor contract is confirmed on the target firmware.

## Linux 7.1.3 gap and reusable pieces

Linux 7.1.3 already provides the generic MediaTek PLL operations, cpufreq
target/OPP notifier flow, regulator tracking, and clock reparenting patterns.
Its MT6797 clock provider, however, has no ARMPLL, CPU mux, or CCI clock, and
the generic cpufreq consumer requires `cpu` and `intermediate` clocks. The
current Gemini description only supplies static `clock-frequency` hints; it
does not provide an OPP table, CPU clock phandles, or `proc`/`sram` supplies.

The missing implementation is consequently platform-specific clock-provider
data and ownership plumbing, not a wholesale replacement of MediaTek's CCF or
cpufreq framework. A new driver/backend is justified because the MT6797 CPU
clock block is absent upstream and has materially different secure/protected
access semantics.

## Staged implementation boundary

1. Add a disabled-only MT6797 CPU clock resource contract and provider shape;
   expose read-only clock descriptions or register no transition callbacks.
2. Prove MCUMIXED semaphore ownership and the SPM/ATF interaction with a
   bounded read-only probe. Do not infer that a normal `regmap` lock is enough.
3. Once ownership is explicit, add LL/L/CCI ARM PLL, mux, and divider clocks
   using the generic CCF math and the vendor field map.
4. Add regulators, EEM/SVS voltage adjustment, and OPP/cpufreq only after the
   clock backend is independently stable and a booted kernel can be recovered.
5. Keep the B cluster disabled until the target secure monitor exposes a
   reviewed BigiDVFS SMCCC interface; do not substitute direct MMIO.

No step above authorizes writes to a preloader, NVRAM, GPT, or device in this
experiment. The current conclusion is design-ready but runtime-inconclusive.
