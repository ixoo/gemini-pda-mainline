# Passive mainline WLAN firmware probe

The selected A53 kernel has a checked-OFF CONSYS owner and a compiled MTKE
firmware preparation helper, but no runtime caller. The retained private image
has four validated sections (two ordinary, two EMI); the authenticated mainline
RAM root requires the existing private firmware staging step. This experiment
connects those pieces without admitting hardware execution.

[Patch 0035](../../patches/proposals/0035-wifi-mediatek-probe-passive-MT6797-firmware.patch)
populates one `wifi` child only after the owner has acquired its reservation,
remap, VCN and CONMCU handles and attached to a confirmed-OFF CONN domain. The
child requests `mediatek/mt6797/WIFI_RAM_CODE_6797`, validates the complete
image, retains its immutable bytes through device lifetime, and logs only
section counts and byte totals. It has no power-domain link, HIF mapping,
transfer path, EMI policy setter, rail vote, reset, firmware START or radio
registration. The existing `-3` EMI-owner admission refusal remains in force.

## Build and boot decision

The `mt6797-a53-wifi-firmware-probe` profile extends the successful passive
owner and modern CONN-query inputs with exactly patch 0035 and an identifying
local version. Build from a clean pushed commit through Buildbox. Kernel,
Gemini DTB, schema and patch validation must pass before packaging. The exact
private initramfs is produced by the [pinned staging script](../2026-09-27-mt6797-wifi-firmware-prepare/scripts/stage-private-initramfs.py);
it and the LK boot container stay ignored and private. Verify exact image,
DTB, initramfs and full boot2 readback under the reviewed guard, then shut
down cleanly for one owner-selected boot2 start.

**Hypothesis:** on a changed mainline boot with the staged image, the owner
binds with CONN checked OFF and the WLAN child logs four sections, two ordinary
(14,832 bytes) and two EMI (396,688 bytes), without a CONN transition. The
unique observation is the first on-device `request_firmware()` and complete
MTKE plan result from a client below the real owner. Preserve the full kernel
log and authenticated boot identity. A missing child or firmware request
redirects DT/probe/initramfs investigation. A parser rejection redirects
private-image or parser investigation. An unexpected power/EMI/radio effect,
missing recovery path, or A53 service regression stops promotion. A matching
passive result permits work on the retained-fault owner and EMI-routing gate;
it does **not** establish working Wi-Fi. Return through the reviewed recovery
path only after preserving evidence and checking live identities; require a
changed-boot Gemian return with WLAN carrier.

No boot2 installation or mainline boot has occurred for this candidate yet.
