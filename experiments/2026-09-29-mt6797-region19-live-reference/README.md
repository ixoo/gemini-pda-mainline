# Read-only Gemian region-19 memory reference

The [firmware-start diagnostic](../2026-09-28-mt6797-firmware-start-probe/results/runtime-1.json)
left the neighboring CONSYS region 19 uninitialized and suffered a separate,
unattributed workqueue panic after START. The selected WMT source protects the
second 512 KiB of the CONSYS reservation as region 19 and clears a smaller
control/coredump extent there; an [instrumented Gemian boot](../2026-09-26-gemian-wifi-reference/results/runtime-1.json)
requested that policy before WLAN carrier. This read asks only whether the
same physical window contains live data in the returned known-good Gemian boot.

The current Gemian boot was identified before and after inspection by kernel
release `3.18.41+`, boot ID `84119e90-08f7-4754-a1d7-0df3c7b21c2c`, root
`/dev/mmcblk0p29`, and WLAN carrier 1. Its `/proc/iomem` has the same 2 MiB
hole at `0xbfa00000..0xbfbfffff` as the previously validated CONSYS reservation.
A root read-only `/dev/mem` mapping sampled only the second 512 KiB at
`0xbfa80000..0xbfafffff`. No register, firmware, radio, partition or memory
write was requested. Raw bytes were not transferred or published.

The [sanitized receipt](results/runtime-1.json) records 74,457 nonzero bytes
across 37 of 128 pages in one snapshot, including the first and last pages.
Two further snapshots ten seconds apart in the same boot differed by 29 bytes
in pages 0 and 4. A preceding one-second pair was identical. This is direct
evidence that the window was populated and changed during this Gemian boot,
not proof of which agent wrote it. The 512 KiB reads are not atomic with
respect to concurrent writers; the hashes identify only the copied snapshots.

This strengthens the need to resolve the WMT control-memory initialization
and ownership gap before another firmware START candidate. It does not prove
that missing region 19 caused the workqueue fault, that any particular content
is required for firmware startup, or that the broad region-23 policy is safe
to reproduce. Preserve possible diagnostic content before any future clear.
