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


## Offline result

The clean pushed commit `5b4e8726` applied all 544 selected patches and built
Linux 7.1.3 and the Gemini DTB on Buildbox. The fetched immutable package passed
its full checksum inventory; [build identity](results/build.json) records the
exact inputs. `System.map` contains the owner probe, WLAN firmware probe and
summary functions. The built DTB contains the single `wifi` child with no
power-domain link. Focused `dt-doc-validate` and `dt_binding_check` including
the example compilation passed. Strict Checkpatch has no source-style finding; synthetic
DCO, combined DT-binding, MAINTAINERS and long commit-description warnings
remain for this internal proposal.

The first private composition was superseded before any device action: its
RAM-root `init` still required the prior kernel release. The
[retarget tool](retarget-initramfs.py) changed that one release gate, retained
all other 51 archive members byte-for-byte, and verified the retained firmware
hash and a serialization round trip; the [sanitized receipt](results/initramfs.json)
pins its new identity. The [candidate builder](build-candidate.py)
verified the corrected private archive and its exact retained image, then added only the
`wifi` child to the previously boot-tested passive CONSYS DT. It checked all
preexisting nodes and properties, parsed the LK boot image, and padded it to the
16 MiB boot2 size. The [sanitized candidate receipt](results/candidate.json)
records full checksums; the image and firmware stay ignored and private. This
composition deliberately avoids carrying unrelated changes from the current
full compiled board DT into this first on-device probe. The current Gemian
boot reports live logical `boot2` at 16 MiB with the exact prior tested image
checksum `98269081…a56a525`; the guarded installer pins that predecessor.

The [session wrapper](passive-session.py), [USB collector](passive-host.py) and
[stage watcher](watch-boot.py) pin the 52-member RAM root, the new release,
the provider and owner records, exact four-section firmware plan, A53 service
regression and changed-boot Gemian return.

No boot2 installation or mainline runtime result has occurred yet.
