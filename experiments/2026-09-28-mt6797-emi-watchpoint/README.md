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

This source-derived diagnostic is a planned test, not evidence that a
particular master hit occurred or that the EMI policy is safe for mainline.
