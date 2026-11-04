# Release readiness

Audit of 2026-11-03: what a first test release needs, and what stands in the way of
daily use. It comes from reading the records, patches and logs, not from new device
runs. Effort sizes (S, M, L) and the proposed scope are judgement. The
[support matrix](HARDWARE_SUPPORT.md) owns demonstrated support.

## Where it stands

It isn't a daily driver. A credible first release is a RAM-root, boot2-only hardware
test image for technical owners. Nobody but the author can build or install today's
image, and it has run on one unit.

| Area | State | Blocker |
| --- | --- | --- |
| Install | Partial | `flash-boot2` from a running station. No first-install tool or tester guide |
| Recovery, boot selection | Works, one unit | Primary boot untouched; hold the side key for boot2. The 11 s long press has never run |
| Reproducibility | Partial | Kernel pinned and built on Buildbox. RAM root derives from a private retained parent |
| Unit dependence | Yes | Parent carries keys and firmware; fixed USB addresses; `iw reg set US` |
| Root filesystem | RAM only | No distro path; `linux` mounts Gemian's partition read-write |
| Suspend, cpuidle, cpufreq | Not started | Off. Decides battery life and heat |
| A72 | Partial | Module, nothing loads it, fixed 750 MHz |
| Thermal | Partial | Trips armed, none has fired; no CPU cooling without cpufreq |
| Charging, running | Partial | 80% guard and temperature window shown by moved limit and emulation, not a real charge or a real 50 °C |
| Charging, powered off | Not limited | The loader decides; it can pass 80% |
| Display, backlight, lid | Works, one unit | Native at 54 Hz, adopted from the loader |
| Keyboard | Partial | Fn map captured once; rollover open; side key reports with no action |
| Touch | Partial | Module, one boot, accuracy untested |
| GPU, desktop | Partial; not started | Panfrost hand-loaded; no compositor |
| Speakers, headphones | Works | 48 kHz, station only |
| Internal mic, jack | Partial | Capture follows speech; headset type and buttons open |
| Wi-Fi | Partial | Two 5 GHz channels on one network, WPA2-PSK. No rekey, WPA3, DFS or power save. Idle link lost at about 6 min. `ip link down` is one-way until `mac` reloads |
| Bluetooth | Partial | A2DP heard, one headset. mSBC opened by the kernel, heard clean on one run. Hand-started from a private chroot, placeholder address, no audio bridge for voice, unexplained link timeouts |
| USB | Partial | Gadget works; no host or role switch |
| microSD, sensors | Unknown | Prepared, never booted |
| GNSS | Partial | No position on mainline |
| Modem, camera | Not started | No mainline path |

## Blockers for a first test release

| # | Blocker | Effort |
| --- | --- | --- |
| 1 | RAM root from public sources, with no keys or firmware; host key made on first boot, tester's own SSH key | M |
| 2 | Tester supplies firmware from their own device, with hash check; Wi-Fi absent cleanly otherwise | S-M |
| 3 | Release profile, below | S-M |
| 4 | Leave Gemian's root read-only by default, or use one dedicated directory | S, owner decision |
| 5 | A country setting replaces fixed US; radio off until set | S, owner protocol |
| 6 | First-install tool from Gemian using the existing guard; backup, restore and removal steps | M |
| 7 | Evidence: ten cold boots, a real charge reaching 80%, the 11 s reset, the Wi-Fi baseline, a soak | M, needs the device |
| 8 | One non-author unit follows the guide unaided | M, availability risk |
| 9 | Tester docs, refreshed matrix, sanitized bug-report tool, source for all shipped binaries | S |

Items 1 to 3 change boot files, so batch them into one image.

### Release profile

- Forced command line today: `initcall_debug`, `panic=0`, `nokaslr`, `earlycon`,
  `clk_ignore_unused`, `console=ttyS0` only, and a test-named USB identity with a fixed
  address.
- `panic=0` is a safety question. There's no lockup detector or `panic_on_oops`, so a
  crashed kernel stays hung, and a kernel stuck like that no longer kicks the charger
  watchdog, which restores charging in about 47 s (inference from the guard record). A
  panic restart also keeps the crash record, as
  [pstore T1](../experiments/2026-11-03-gemini-pstore-retention/README.md) showed.
- Remove unless justified: `THERMAL_EMULATION`, `DEVMEM`, `I2C_CHARDEV`, `DEBUG_FS`.
- Log noise: 150 `dev_info` calls in Wi-Fi and CONSYS with no `dev_dbg`, and "one-shot"
  naming 82 times in Wi-Fi. `wait_for_bt_irq` printed 1939 lines in one Bluetooth run,
  55% of that log. Debug module parameters on Panfrost, panel and `mtk_drm`.

## Proposed v0.1 for testers

A signed-off tag from a public manifest and public RAM-root recipe, producing a 16 MiB
boot2 image with no firmware or keys, for owners who can use SSH and recover a device.

**It promises only, on the tester's unit:** boots from boot2 by holding the side key,
and never touches primary boot, NVRAM, GPT or the preloader. Console with keyboard and
native display, falling back to the loader framebuffer. USB SSH. Lid, charge guard
while running, thermal backstops. Speakers and headphones. Wi-Fi as a beta, with the
tester's own firmware. Bluetooth and touch as optional, unpromised modules; Bluetooth
needs a public userspace first, or stays out.

**It must say it doesn't:** replace Gemian or persist anything across reboot; suspend,
scale CPU clocks or offer useful battery life; limit charging while off; provide a
desktop, GPU by default, A72 by default, USB host, microSD, sensors, GNSS, modem or
cameras; offer reliable Wi-Fi; support unique Bluetooth addresses or more than one
nearby Gemini on Bluetooth; promise anything about other hardware variants.

**Tester safety:** back up every readable partition privately, since backups hold
calibration and identifiers. Confirm Gemian boots and `boot2` exists by GPT name. Use
stable power for writes. A plain `reboot` returns to Gemian. Stop on heat, swelling,
charging anomalies or watchdog loops. Holding Esc 11 s is expected to reset the device,
untested. Scrub logs of addresses and network names. Set the right country before radio
use.

## Code quality

Reviews read the code; sampled checkpatch found 0 errors, so style isn't the problem.
Structure is.

- **Series shape.** 712 patches, +113.6k lines. 95 of 136 new C and asm files (47.3k of
  73.1k lines) and 183 of 204 new Kconfig symbols are off in the station config. 303
  patches touch only files the series itself created. No maintainer could review this.
- **Numbering collision.** `0534`, `0535` and `0536` were each used twice in
  `proposals/`, by display and Bluetooth, on the same night. They apply, since the names
  differ. Renumber at the next series change.
- **Authorship.** 508 of 712 have a placeholder `From:`, and few have a true
  `Signed-off-by`. Only the owner can certify; none may be invented.
- **Generic code.** Diagnostics in `lib/kobject_uevent.c`, `kernel/ksysfs.c`,
  `kernel/cpu.c` and `i2c-mt65xx.c`; thermal maps TOPRGU registers directly.
- **Wi-Fi.** 14k lines; `mt6797_mac_join_work` is 1036 lines; polled receive. Expect
  rejection as it stands (inference).
- **CONSYS.** A static singleton with hardcoded addresses, and a 296-line probe.
- **`check-repository`.** It misses placeholder `From:` lines, orphan patches, and MAC,
  IP or SSID patterns.

**Proposed cut.** Phase A, days: a `release` profile from HEAD, leaving history alone.
Phase B: delete the off scaffolding, prove objects match today's build, and regenerate
about 60-80 patches by area, SoC foundation first, with A72 as a separate last topic.
The old series stays in Git as evidence.

## Upstream blockers from the patch review

Details are in each experiment's record.

- **Charge guard:** suspend and unbind fail open; DT properties encode policy; `0520`
  needs `i2c0` enabled in source; no cold stop between -20 and 0 °C, an owner decision.
- **Display and lid:** the `0515` hold doesn't hold against VT and DRM restore paths;
  `0503` uses a provider API from consumer drivers; `0502` and `0507` delete required DT
  properties; the backlight link exists only through `station-dt.sh`.
- **Bluetooth and CONSYS:** a resent STP frame may be transmitted twice, which would fit
  T13's `sent 0 < count 1` warnings, though the firmware mechanism is inferred, and
  `0525` keeps its resend until that's tested. btcvsd has no dependency on CONSYS being
  powered, so it stays hand-loaded with CONSYS up. Send blocks shorter than recovery;
  clients aren't told of a link stop.
- **GPU:** `0493` may wait on reclaim in the fence path.
