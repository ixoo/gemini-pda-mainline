# One-use Gemian EMI watchpoint discriminator

The working Gemian boot `636e12fb-65de-4eb3-88c8-70c3e4cec71e` has WLAN
carrier and reports region 18 at `0xbfa00000..0xbfa7ffff` while the broad
region 23 also covers that span. A one-second watchpoint on region 18 can
identify the AXI master of a naturally occurring access without changing the
MPU policy. A CONSYS hit would join an access to the WLAN reservation with the
source-labelled CONSYS bus master; it would not identify which CONSYS client
issued it. An AP/other hit or no hit would not establish that routing. This
observation alone cannot report the EMI domain or establish overlap priority.

The [MT6797 register table](https://www.96boards.org/documentation/consumer/mediatekx20/additional-docs/docs/MT6797_Register_Table_Part_1.pdf), pages 372–373, defines the watchpoint range,
read/write selection, hit flag and AXI ID. It also identifies controls that
can return a slave error, suppress reads/writes or raise an interrupt. The
pinned Gemian `emi_wp_vio` sysfs setter enables slave errors, so this test
does not use that setter. The [one-use script](one-shot.sh) requires exact
boot, kernel, carrier, region range and idle register state before any write.
It selects a 512 KiB read/write watchpoint with all error, suppression and
interrupt bits zero, records the latched words after one second, disables the
watchpoint, clears only its captured status and verifies the original register
state. Its `--preflight` mode checks the same starting conditions without
writing. A tmpfs marker refuses an unchanged-boot retry. Raw output stays
private under ignored `artifacts/`.

The exact read-only host preflight found `WP_ADR=0`, `WP_CTRL=0`, `CHKER=0x00800000`,
`CHKER_TYPE=0` and `CHKER_ADR=0` with carrier 1 and a stable boot ID. The
`CHKER` value selects all ports for the separate non-alignment checker; its
enable bits are clear. The script admits at most seven writes to three
registers and one second of active observation. Any preflight mismatch makes
zero writes; an unexpected hit identity or incomplete restoration stops the
Wi-Fi investigation for review. No protection setter, SMC, firmware load,
radio-cycle request or partition operation is in this protocol.

## Device result

The reviewed script from commit `1b6da20a` passed its root-only read-only
`--preflight` and ran exactly once in the named Gemian boot. The one-second
window returned `CHKER=0x00880000`, `TYPE=0`, and `ADR=0`: the enable bit was
set but no watchpoint hit or master ID was latched. Its cleanup restored all
five observed words to their preflight values; the host command exited zero.
A separate authenticated check found the same boot ID, WLAN carrier 1,
`CHKER=0x00800000` and the one-use marker present. The raw host capture
remains ignored and private; its SHA-256 is recorded in the
[sanitized result](results/runtime.json).

This negative result covers connected idle traffic during this one-second
window only. It neither excludes CONSYS accesses at firmware load nor
establishes routing, domain or overlap priority. Do not repeat the same
window. A decision-changing successor must place the non-blocking watchpoint
at an attributable firmware-load or active data interval and retain the same
non-disruptive bit and cleanup checks. No mainline EMI write is admitted by
this result.

## Firmware-load window

The [single-use firmware-load script](firmware-load.sh) tests the narrower
hypothesis that the WLAN WMT-on firmware-load path accesses region 18 and can
latch an AXI master ID. It is pinned to the still-running primary Gemian boot
above. The earlier instrumented-Gemian disconnected WMT off/on cycle reached
`kalFirmwareLoad`, restored carrier, and produced no new cfg80211 warning.
This successor disconnects with ConnMan and waits for three carrier-down,
unassociated samples before WMT off. It arms the same non-blocking watchpoint
only after the WLAN netdev disappears, then requests one WMT on and immediately
records the latched registers. A device-side exit handler records any pending
hit, restores and verifies the five watchpoint words, requests WMT on only if
off was attempted without an on attempt, enables ConnMan and waits up to 90
seconds for carrier. The script runs as a transient systemd unit so LAN SSH
loss does not interrupt cleanup. It retains private logs under a fixed,
single-use mode-0700 directory in `/var/tmp`.

The effect budget is one ConnMan disable/enable, one WMT off/on pair, seven
watchpoint register writes, and no EMI MPU protection writes. A failed identity,
power, association, WMT-node, region or idle-register gate refuses before any
effect; `--preflight` exercises those gates without changing the radio. A
non-CONSYS master or no hit leaves CONSYS routing unresolved. A CONSYS hit
would prove that this master accessed the watched address during WMT on, but
the watchpoint cannot report its EMI domain or region-18/23 arbitration.
The only next step then is a separately justified domain/overlap discriminator;
the result does not authorize copying Gemian's EMI policy into mainline.
