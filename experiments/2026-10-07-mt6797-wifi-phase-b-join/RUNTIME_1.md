# First Phase B runtime: common init fails before WLAN

Status: consumed. One owner-selected boot of the installed
[candidate](results/candidate.json) ran under [PROTOCOL.md](PROTOCOL.md).
There was no scan or join attempt. The sanitized
[receipt](results/runtime-1.json) pins build, candidate, boot and evidence hashes.

Mainline boot `5a3407ba-85ee-476e-8be5-152efa3c2c3b` ran the expected
`7.1.3-gemini-a53-wifi-phase-b-compile` release. WMT preparation passed: the
two preflight retained-memory samples matched, the clear prefix read back zero,
the retained suffix matched, and all five setup records appeared once.
One negotiation/common-init trigger was sent. Negotiation passed; common init
returned `-EPROTO` (`-71`) with 5 of 285 steps completed.

The failed exchange is index 5, the MCU clock-divider masked register write.
Its command has 20 payload bytes and a 26-byte full STP frame. The recorded
FIFO progress was 16 bytes transmitted, zero received, two services and zero
parsed frames. The link snapshot was `6/6/5/5`. No raw interrupt-cause snapshot
was recorded. Both PA-rail software flags were zero; their enable steps and RF
calibration had not been reached. WLAN initialization did not run, and no wiphy
registered. These observations do not test the new management join code.

The failed prerequisite withheld the scan and join. The runner sealed the
complete 135349-byte log, passed the A53 RAM-service regression and used one
reviewed native recovery request. Changed-boot Gemian was confirmed as
`9b0bb289-0931-4521-ae0a-acaadf4672a1`. No trigger was repeated. Raw retained
memory, kernel logs and transport captures remain private.

The [Phase A parent](../2026-10-06-mt6797-wifi-common-init/RUNTIME_3.md)
previously completed all 285 steps. This first Phase B observation contradicts
an assumption that that prerequisite would complete on every boot; it does not
identify a kernel regression by itself. Review the early STP FIFO/IRQ path and
the exact source delta before selecting a changed candidate or another
decision-changing measurement. Association, data, WPA2 keys, DMA, interrupts
and operational network testing remain incomplete.

## Diagnosis and fixes (2026-10-06)

Offline review of the built source ([REVIEW_1.md](REVIEW_1.md)): nothing under
`drivers/soc/mediatek` differs from the Phase A runtime-3 source, the resolved
config differs only by `CONFIG_MT6797_STATION_JOIN=y` and the release string,
and the packaged DTB is identical. The join code runs only after WLAN
readiness. So this boot ran the same common-init code that completed 285/285.

The only code path consistent with the counters (`services=2`, 16 of 26 bytes
written, nothing received) is the strict non-initial guard in the WMT full
I/O: an interrupt entered mid-transmission with an IIR showing no RX, timeout
or THR-empty source, and the exchange was retired with `-EPROTO`. That is a
benign no-source interrupt race, by inference; the raw IIR was not captured.
It says nothing about the firmware's reaction to the clock write, which never
finished transmitting.

[Proposal 0141](../../patches/proposals/0141-soc-mediatek-tolerate-a-no-source-BTIF-interrupt-during-a-WMT-exchange.patch)
tolerates that candidate no-source case and records the IIR in the failure
footer. It does not confirm the hardware cause; the next runtime decides
whether the failure recurs, and its footer then shows the IIR either way;
[0142](../../patches/proposals/0142-wifi-mt6797-release-the-driver-owned-deauthentication-frame-on-teardown.patch)
fixes a frame-ownership bug found in the same review. The next candidate
should carry both. The installed boot2 `6ecc057c…` is consumed and is not
retried.
