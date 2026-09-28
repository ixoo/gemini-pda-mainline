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

The committed script `969c306d` passed its on-device `--preflight` and ran
once as a transient systemd unit in the pinned primary Gemian boot. ConnMan
disconnected before WMT off; WMT on returned and the retained kernel log
shows WLAN probe. The watchpoint stayed enabled at `0x00880000` without a hit,
type or address after WMT on. Cleanup restored all five words, carrier returned,
and the boot ID remained unchanged. No new cfg80211 warning appeared. The
[sanitized result](results/firmware-load.json) pins the private capture.

This second no-hit is limited to the WMT-on interval. The stock kernel cannot
prove that the exact later firmware section copied in this cycle, and the
watchpoint has no positive hit control. Neither no-hit can establish absent
CONSYS traffic, effective domain or overlap priority. Do not replay this
radio cycle. The next investigation must resolve the observation path itself
or obtain an exact hardware routing/arbitration source before any mainline EMI
policy write.

## Owned-page positive control

Two no-hit windows do not validate the watchpoint as an observer. The
[one-use positive control](positive-control.py) tests its ability to latch a
known AP read without touching the CONSYS reservation or cycling the radio.
On the exact carrier-up Gemian boot, it allocates and locks its own 4 KiB page,
derives that page's physical frame through its own pagemap entry, and verifies
an eight-byte pattern through read-only `/dev/mem` before any register write.
The read-only feasibility probe already found a present nonzero frame with a
matching physical read. The script requires that the page fit the watchpoint's
32-bit offset from `0x40000000`; it refuses if that check,
identity, carrier, idle watchpoint words or its fixed single-use output gate
fails. Its `--preflight` mode stops there.

The effect window watches 16 bytes of that owned page, with read/write
selection and all error, suppression and interrupt controls clear. It makes
two bounded physical reads, records the raw hit words after each, then
disables, clears and verifies the original five register values. The budget is
seven EMI watchpoint-register writes, three eight-byte reads of the owned
page including preflight, and no radio, firmware, protection or partition
operation. It runs in a device-side transient service so host loss does not
interrupt cleanup; its mode-0700 output stays private under `/var/tmp`.

A latched hit with the known read address validates this observation path for
an AP transaction and supplies an AXI ID to decode. No hit despite a matching
read means the two WLAN no-hits cannot be interpreted as absence of traffic;
it requires a new observer design, not replay of either radio window. A hit
does not itself establish the CONSYS master/domain or region overlap rule.

The committed script `90a3ec84` passed the live read-only preflight and ran
once on the same primary Gemian boot. Both physical reads matched the owned
page's pattern, but `CHKER` remained `0x00880000` with no hit, type or address.
The device-side unit exited zero; an independent host check found all five
registers at baseline, the original boot ID and Wi-Fi carrier 1. The raw
mode-restricted log remains private; the [sanitized result](results/positive-control.json)
pins its hash. The exact positive-control window is consumed.

The register table confirms control value `0xc4` selects a 16-byte range and
both read and write without interrupt, slave error or suppression. A matching
`/dev/mem` read does not prove a new EMI bus transaction: CPU caching is one
possible explanation for no hit. The observation path remains unvalidated.
Do not interpret the two earlier WLAN no-hits as absent traffic or replay them.
The next path needs a verified bus-level witness or an exact routing/overlap
source before the mainline EMI policy can be chosen.
