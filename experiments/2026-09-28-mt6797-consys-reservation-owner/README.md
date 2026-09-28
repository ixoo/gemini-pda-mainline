# MT6797 CONSYS boot-reservation identity

The authenticated [HIF boot](../2026-09-28-mt6797-wifi-hif-probe/results/runtime-1.json)
reached WCIR `0x00100279` and validated the staged four-section firmware
plan. The next image executor needs the exact boot reservation for its first
512 KiB EMI window. The present CONSYS probe validates a dynamic `no-map`
reservation of at least 1 MiB, but then checks the busy iomem resource as
**exactly** 1 MiB and retains only its base. A valid larger reservation would
fail probe, and the later image owner could not revalidate its full extent.

[Patch 0042](../../patches/proposals/0042-soc-mediatek-retain-full-MT6797-CONSYS-boot-reservation.patch)
retains the complete resource returned by the reserved-memory API and requires
the busy boot resource to match its start and end. It changes no power, HIF,
firmware, remap or EMI protection operation. The
`mt6797-a53-wifi-reservation-compile` profile extends the tested HIF series
solely for compilation; it is not a new boot2 candidate.

The full resource identity is necessary but does not grant WLAN access to the
neighboring WMT half-MiB or exclude external firmware writers. Active image
entry remains refused. The next implementation must bind the immutable whole
image, prove same-boot ownership and protection policy, and retain resources
through partial transfer or failure before START is allowed.
