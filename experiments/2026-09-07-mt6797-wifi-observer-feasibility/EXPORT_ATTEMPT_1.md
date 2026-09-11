# First native export attempt

Result: no attributed USB terminal; kernel/startup stage inconclusive. The
installed image's one physical attempt is consumed. Do not repeat it unchanged.

## Installation and observation

The [reviewed installer](EXPORT_INSTALLER.md) installed the validated
[native container](EXPORT_CONTAINER.md) through authenticated Gemian SSH.
Live GPT resolved boot2 to `/dev/mmcblk0p30` (`179:30`), separate from root
`/dev/mmcblk0p29` (`179:29`). The current device guard passed before writing.
Two power samples agreed: battery present, 96%, Good. The write was synchronized
and flushed; a complete independent 16,777,216-byte readback matched byte for
byte. The temporary upload/readback were removed. No fresh backup was made.

| Identity | SHA-256 |
| --- | --- |
| Predecessor boot2 | `7d9eb0e20f145594ba5b9e56bbb809998c813d2517ce2f43b17074828459ea2a` |
| Installed image and full readback | `f3df2816f813d2419d95e5c938f482fc7b537b9ebd1cb402105ed517820cdd97` |

The preceding Gemian boot was `9ed3b455-0e52-45e1-9812-c8895dbb1b95`.
The clean power-off command returned zero and SSH became unreachable. The
owner then reported starting boot2 and seeing the boot logo. No candidate
runtime boot UUID was obtained, so installation and physical selection do not
by themselves prove execution of the candidate kernel or PID1.

The host receiver watched for one new USB parent with the expected Android
descriptors and an unambiguous ACM child. Its 180-second observation ended
without an attributed terminal. No request was sent, no stream receiver was
invoked and no snapshot was saved. A separately requested check of the known
Gemian LAN endpoint timed out. The visible mass-storage device was the owner's
USB key; it was not treated as the Gemini or opened by this experiment.

Gemian's own USB enumeration was incorrectly treated as an initial deployment
prerequisite. The owner corrected that assumption: Gemian administration uses
LAN SSH. The installed image's USB path remains a real-device test obligation,
but the absence of Gemian USB enumeration is not a reason to block SSH-based
installation. No Gemian USB configuration was changed to work around it.

## Return and retained evidence

The owner later reported the device powered off, then started normal Gemian.
Authenticated inspection confirmed boot `302aaa99-de4b-4e25-88b1-feba649c2126`,
MT6797X, Linux 3.18.41+ aarch64, Debian 9 and running systemd. The agent issued
no recovery restart. This confirms a usable Gemian return, not a captured
reset reason or the failed image's runtime identity.

Both exposed retained records were saved privately without clearing:
`console-ramoops` and `pmsg-ramoops-0`, each 65,524 bytes. The console contains
routine native output but no identified startup marker or attributed failure
from this candidate. The records therefore cannot establish the failing stage.
The ordinary PMSG record is not the requested complete 65,536-byte same-boot
raw export and must not substitute for that missing result. Raw records, USB
inventories, command streams and checksums remain private.

## Bounded offline diagnosis

The exact linked kernel configuration includes initrd/gzip, script execution,
devtmpfs, proc, sysfs, tmpfs and pstore. Extracting the embedded configuration
from the verified ELF in the RE VM matched the packaged configuration exactly.
The historical working native ramdisk and new filesystem both use direct gzip
payloads; this comparison found no missing MediaTek ramdisk wrapper.

The actual compact filesystem's BusyBox executed the startup mount sequence in
an isolated RE-VM mount/PID namespace: proc, sysfs, read-only pstore, devtmpfs,
tmpfs and all six bind/remounts passed, and `/dev/console` existed as a character
node. The probe deliberately omitted opening that console, the SysRq write and
Python startup. It exercised no USB or PDA operation; the namespace and extracted
root were removed. This narrows command/runtime compatibility only, not native
Linux 3.18 boot behavior.

`CONFIG_FRAMEBUFFER_CONSOLE` is disabled in the candidate. Consequently the
boot logo is not a useful indicator of PID1 progress. The startup's generic
console-only failure message and late USB setup leave early failures without
an observed diagnostic path. A subsequent candidate must provide attributable
bootstrap failure evidence through a reviewed existing logging path before
the export transport can serve as a prerequisite for further Wi-Fi work.
No kernel or startup repair, replacement candidate, repeated boot, capture
clearing or radio action is justified by these negative observations alone.
