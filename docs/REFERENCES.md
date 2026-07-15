# References and prior art

This index points to evidence sources and related efforts. Linked content may be outdated, unsafe, proprietary, or incorrectly licensed. Treat it as untrusted input and independently validate technical claims.

## Upstream sources

- [Linux `mt6797.dtsi`](https://github.com/torvalds/linux/blob/master/arch/arm64/boot/dts/mediatek/mt6797.dtsi) — current SoC description in the upstream tree.
- [Linux kernel contribution guide](https://docs.kernel.org/process/submitting-patches.html) — patch preparation and submission.
- [Linux Device Tree bindings](https://github.com/torvalds/linux/tree/master/Documentation/devicetree/bindings) — binding schemas and examples.
- [Linux MediaTek mailing-list archive](https://lore.kernel.org/linux-mediatek/) — public review record for MediaTek platform work.

## Active and historical Gemini work

- [`bsg100/gemini-linux`](https://github.com/bsg100/gemini-linux) — independent MT6797X/Helio X27 Linux 6.6 bring-up, hardware inventory, and patch research. Treat its revisioned claims as comparative evidence; see the [2026-07-13 comparison audit](../experiments/2026-07-13-bsg100-gemini-linux-comparison/README.md). Coordinate before duplicating work.
- [`Jasu/gemini-pda-buildroot`](https://github.com/Jasu/gemini-pda-buildroot) — historical mainline/Buildroot experiment that reported UART-only BusyBox boot.
- [`gemian/gemini-linux-kernel-3.18`](https://github.com/gemian/gemini-linux-kernel-3.18) — downstream Gemini Linux 3.18 tree.
- [`ali1234/linux-gemini`](https://github.com/ali1234/linux-gemini) — legacy Gemini kernel history.
- [`planet-community/android_kernel_planetcom_mt6797`](https://github.com/planet-community/android_kernel_planetcom_mt6797) — community mirror of the vendor Android kernel.
- [`lineage-geminipda/android_kernel_planet_mt6797`](https://github.com/lineage-geminipda/android_kernel_planet_mt6797) — legacy LineageOS kernel tree.
- [`NotKit/kernel-4.9-geminipda`](https://github.com/NotKit/kernel-4.9-geminipda) — later vendor-derived kernel work.
- [`ixoo/gemini-flash-vagrant`](https://github.com/ixoo/gemini-flash-vagrant) — historical account-owned flashing helper; audit before reuse.

## SoC-adjacent work

- [`cooollawf/mt6797_mainline`](https://github.com/cooollawf/mt6797_mainline) — separate MT6797-named repository; evaluate status before overlapping SoC work.

## Reference policy

For every fact promoted into the hardware matrix, record:

- source URL or document identifier;
- exact file, symbol, register, or line context where possible;
- source revision/date;
- whether it is vendor-stated, inferred, observed, or hardware-tested;
- compatible licensing for any copied material.

Do not commit vendor firmware, firmware packages, full extracted Device Trees with unclear redistribution rights, proprietary PDFs, or personal device dumps. Small factual excerpts should be replaced with independently written summaries whenever possible.
