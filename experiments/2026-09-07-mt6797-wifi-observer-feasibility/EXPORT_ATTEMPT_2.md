# Second native export attempt

Result: no attributed USB terminal or recovered bootstrap marker. Kernel entry
and startup stage remain inconclusive. The owner-controlled Esc restart returned
to authenticated Gemian. This image's one physical attempt is consumed; do not
repeat it unchanged.

## Installation and physical selection

The [second session](EXPORT_SESSION_2.md) used the exact
[bootstrap container](results/bootstrap-container-1.json), with the same native
kernel as the first attempt and the new bounded startup diagnostics. Live GPT
resolved boot2 to `/dev/mmcblk0p30` (`179:30`), separate from root
`/dev/mmcblk0p29` (`179:29`). The device guard passed. Stable power samples
reported battery present, 100%, Good. The write was synchronized and flushed;
an independent complete 16,777,216-byte readback matched byte for byte.

| Identity | SHA-256 |
| --- | --- |
| Predecessor boot2 | `f3df2816f813d2419d95e5c938f482fc7b537b9ebd1cb402105ed517820cdd97` |
| Installed image and full readback | `a0661c7a0a02cf690516cc026ee07209eb14e815bc3ef939f18a8de684bc95dd` |

The preceding Gemian boot was `302aaa99-de4b-4e25-88b1-feba649c2126`.
Temporary staging and readback files were removed; no fresh backup was made.
After the clean power-off request, its SSH invocation returned 255 and subsequent
SSH became unreachable. That exit status alone is not a shutdown-success code.
The owner then reported selecting boot2 and seeing the Gemini logo without a
console. No candidate runtime boot UUID was obtained.

The receiver was armed before physical selection. Its 180-second observation
ended without one new expected USB parent and unambiguous ACM child. No serial
terminal was opened, no receiver exchange was invoked, no request was sent and
no snapshot was retrieved. The baseline/final USB inventories, output streams,
timing and checksums remain private. The logo does not establish kernel entry;
the candidate also has framebuffer-console support disabled.

## Recovery and retained evidence

After preserving host evidence, the owner explicitly agreed to one Esc-only
restart under the reviewed twelve-second maximum, first-indication release
procedure. The owner reported vibration followed by the expected Gemian restart.
No exact hold duration was reported. The agent issued no restart command or
power-off fallback.

Authenticated LAN inspection confirmed boot
`8876d666-547d-4538-9387-8c46819ca5cf`, MT6797X, Linux 3.18.41+ aarch64,
Debian 9, systemd and running userspace, with matching before/after UUIDs.
This establishes the return; it does not attest the intervening kernel.

The one console preservation attempt stopped when `stat` found no
`/sys/fs/pstore/console-ramoops`; zero bytes were saved. The private collector's
existence test was the left side of an AND list under `set -e`, so a failed test
could proceed to the failing `stat`. Its output therefore does **not** show that
the record existed and then disappeared. No read or clear occurred. A subsequent
bounded metadata check found pstore mounted and empty, and no saved-log directory
at either `/var/lib/systemd/pstore` or `/var/lib/ramoops`. A literal search of
systemd/init service definitions found no matching archive hook; that bounded
search does not exclude another consumer.

The alternate `/proc/last_kmsg` interface was inspected only after checking its
source read path. One read capped at 65,536 bytes returned **74 bytes**, with
the same Gemian UUID verified before and after. RE-VM inspection identified
only a reset-status header: no kernel banner or `wifi-bootstrap-v1` marker.
Its hardware-status, FIQ-step and old-status fields were zero, with `Not Clear`;
these fields do not prove retention of the candidate's console RAM or identify
its reset cause. No raw record is published.

The returned Gemian's filtered current kernel log reports successful ramoops
registration, console enablement and attachment at `0x44410000`, size `0xe0000`,
with 64 KiB console and PMSG sizes. This is evidence about the **returned boot**,
not proof that the candidate registered its backend or that its records survived.

## Read-path check and next boundary

In the pinned native source `59e00a9144d782e148332009a835b99c43382467`,
`drivers/misc/mediatek/ram_console/mtk_ram_console.c:735–750` connects
`last_kmsg` to the saved RAM-console buffer. Lines 535–583 emit its header and,
when configured, request old console records through `pstore_console_show()`.
The latter serializes backend reads and frees temporary copies; it has no erase
call. This source file's SHA-256 is
`c2f2c38fc42b92c5c8f32a2a2fe3afeb9577a86d07ae7acec8fc3d4498fc0991`.
The baseline `fs/pstore/ram.c` read path was also checked, SHA-256
`7ba661c230fb71d7d2768bb3cddb95d1deb36810531cfc992bc5c7297113a391`.
This is source evidence for the bounded inspection, not a new running-binary
equivalence claim. Original sources and retained logs stay outside Git.

The changed diagnostic image supplied a real device test, but neither USB nor
retained userspace markers established its failing stage. The next investigation
must distinguish kernel entry from console-retention failure before another
physical attempt. Do not infer an init failure, blame the recovery action, or
repeat the image on these observations alone. Capture clearing and a WLAN cycle
remain unadmitted. Gemian is left running.

Publication changes only documentation. Repository, whitespace, local-link and
sensitive-data checks passed; no new kernel build was needed. Installation,
negative USB observation and authenticated recovery are the hardware results,
not usable Wi-Fi or a successful export.
