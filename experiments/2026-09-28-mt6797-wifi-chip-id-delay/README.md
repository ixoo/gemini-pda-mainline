# Bounded delayed MT6797 CONSYS chip-ID probe

The [first powered chip-ID read](../2026-09-28-mt6797-wifi-chip-id-probe/results/runtime-1.json)
returned zero after 30 µs while the CONN domain was confirmed ON and CONMCU
reset stayed asserted. The selected Gemian source retries misses at 20-ms
intervals, so that single sample does not establish a persistent zero.

The named `mt6797-a53-wifi-chip-id-delay` profile keeps the prior isolated
power and chip-ID probe. Its incremental [patch](../../patches/proposals/0038-soc-mediatek-bound-delayed-MT6797-CONSYS-chip-id.patch)
takes at most two additional read-only samples after 20 and 40 ms, stopping
early on `0x0279`. It confirms dual-status CONN ON and held CONMCU reset before
each read. It does not release reset, write the CONSYS window, execute
firmware, operate the radio or power off. The synthetic patch author is not
DCO-certified.

Before boot, require a clean pushed Buildbox build, exact package and boot2
candidate validation, guarded live-GPT installation with full readback, and a
fresh finite collector. The hypothesis is that one delayed sample returns
`0x0279`, identifying a settling window. A persistent zero at 40 ms directs
the next diagnosis to clock, bus-protection and power-control readback without
permitting reset release. An ON/reset recheck failure stops further MMIO;
a bus fault preserves available evidence and uses reviewed Gemian recovery.
Any unexpected ID also stops progression. None of these outcomes alone
demonstrates firmware execution or working Wi-Fi. Do not repeat this exact
candidate without a new decision-changing measurement.
