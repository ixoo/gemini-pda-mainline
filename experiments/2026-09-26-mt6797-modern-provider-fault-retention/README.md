# Modern MediaTek power-domain fault retention, compile-only

The Linux 7.1.3 child-domain provider unwinds clock, SRAM and bus-protection
state after a power-on error, even when it has already requested power and
cannot prove the island is OFF. For an eventual MT6797 CONN domain this could
remove prerequisites from uncertain hardware. The preceding
[initial-OFF admission proposal](../2026-09-26-mt6797-modern-provider-off-admission/README.md)
prevents a live island from being published as OFF at registration, but does
not cover transition failures.

The [single format-patch](../../patches/proposals/0009-pmdomain-mediatek-retain-opted-failed-domain-state.patch)
adds an opt-in fault latch to the direct-control callbacks. The flag requires
confirmed initial OFF. A post-request ON error retains acquired supply and
clock votes and avoids additional rollback register operations; an OFF error
latches without dropping the still-held base prerequisites. Later ON/OFF
callbacks return the first fault. An error before the first ON power request
uses the existing cleanup and permits a later retry. Existing domains do not
select this flag and keep their callback behavior. The pinned Linux 7.1.3
`checkpatch.pl --no-tree --no-signoff` reports zero errors and warnings.

This patch adds no MT6797 domain data, DT child or consumer. It does not
expose the fault to a client, and genpd may skip a callback after a failed
OFF. Any future shared CONSYS owner must query the latch before each hardware
use. The owner also needs SPM key and external rail/reset sequencing, writer
exclusion, and EMI/remap policy before activation. No boot2 image or device
test is admitted by this isolated compile profile.
