# Candidate J post-attempt-1 exact-tree source audit

## Record

| Field | Value |
| --- | --- |
| Date | 2026-07-17 |
| Scope | Read-only audit of the exact Candidate J source, build, configuration, DTB and shared I/J `/init` after runtime attempt 1 |
| Kernel source | `/home/julien.guest/src/gemini-pda/linux-7.1.3` |
| Kernel build | `/home/julien.guest/build/gemini-pda/linux-7.1.3-usbdiag-clkignore` |
| Kernel package | `/home/julien.guest/artifacts/gemini-pda/linux-7.1.3-gemini-usbdiag-clkignore-3d92a7e9-d1224166` |
| Resolved-config SHA-256 | `283570babf78d9299948a35c8133dfa906b04a0c35a2d0d2997309326d607f0d` |
| Shared I/J initramfs SHA-256 | `85059d3128e643deaafc3989c745ed21ec94ec5f24f5002839e0d080d13dfe85` |
| Raw boot-image SHA-256 | `6d5bad08c2f93eba7fbd66ea5c54de2437f81e44832426a97d4d65d550c659f4` |
| Installed full-partition SHA-256 | `465e4c747138e12191d38fd6b4cde68cd0b9a19f918030dea05c9b8dbdd4d3fc` |

This audit changes no candidate, package, partition or device. Its purpose is
to constrain the next test using the code that was actually built, not a
generic description of Linux initialization.

> [!IMPORTANT]
> Follow-up on 2026-07-17: the one-repeat gate described at the end of this
> post-attempt-1 audit has been consumed. The owner's subsequent two-bullet
> report is provisionally interpreted as two additional intended Candidate J
> selections, with owner confirmation pending; see the
> [repeat report](runtime-candidate-j-repeat-report-20260717.txt). Do not use the
> historical gate below as authorization for another J selection. Further J
> repetition is stopped, and no Candidate I rollback is authorized. The
> completed reassessment selected
> [Candidate K](../../2026-07-17-fbcon-newline-boundary-diagnostic/README.md),
> an exact-J initramfs-only newline-boundary diagnostic now synchronized to
> `boot2`; its single attended runtime gate is pending.

## Observation and exact marker boundary

The only direct runtime observation supplied for attempt 1 was:

> The last line I saw before the screen went dark is 4/60.

The owner did not transcribe the complete line or explicitly recognize its
marker. The exact shared I/J source is
`experiments/2026-07-16-fbcon-refresh-timing-diagnostic/initramfs/init`:

- lines 10–15 require the initial devtmpfs mount to succeed or enter a
  different permanent static hold;
- lines 27–37 start at zero, run `sleep 1`, increment the counter, and emit one
  line to `/dev/tty0` and `/dev/ttyS0`; and
- line 36 emits the exact tick-04 line
  `GEMINI_FBCON_REFRESH_20260716_I T+04 ACTIVE REFRESH 04/60`.

Only this tracked shared initramfs emits the `NN/60` sequence. Combined with
the independently verified J image, full-partition readback and intended
`boot2` selection, the visible suffix is strong evidence that Candidate J:

- entered Linux;
- mounted devtmpfs and reached the external `/init` loop;
- completed at least four one-second sleeps after that loop began; and
- produced visible tty0/fbcon output through tick 04.

It does **not** measure four seconds from slot selection. Selection-to-loop
time, selection-to-black time and the upper bound on loop progress are unknown.
Later ticks could have been emitted after display visibility was lost. Because
of that uncertainty, the observation does not distinguish loss during the
active-refresh phase from loss after the planned T+60 static-hold transition.
The refresh-versus-hold timing hypothesis remains unestablished.

## Exact initialization order

The relevant exact-tree paths and functions are:

- `init/main.c`: `do_basic_setup()` calls `do_initcalls()`;
  `kernel_init()` calls `kernel_init_freeable()`, then
  `async_synchronize_full()`, and only afterward executes the ramdisk
  `rdinit`/`init` program.
- `drivers/clk/clk.c`: `clk_ignore_unused_setup()` sets the diagnostic flag;
  `clk_disable_unused()` is registered with
  `late_initcall_sync(clk_disable_unused)`. When the flag is set,
  `clk_disable_unused()` logs the diagnostic warning and returns without
  performing the unused-clock sweep.

The exact Candidate J `vmlinux` initcall symbols have this order:

| Address | Initcall |
| --- | --- |
| `ffff800080a941b8` | `deferred_probe_initcall` |
| `ffff800080a941e0` | `clk_disable_unused` |
| `ffff800080a941e4` | `genpd_power_off_unused` |
| `ffff800080a941e8` | `regulator_init_complete` |

All four initcalls therefore run before external `/init`. Candidate J's exact
configuration has `CONFIG_CMDLINE_FORCE=y`, and its forced command line ends in
`clk_ignore_unused`; the normal CCF cleanup is skipped before tick 01. Tick 04
cannot be the first normal CCF unused-clock sweep after the visible marker.

## Display and clock ownership in Candidate J

The exact Candidate J DTB describes
`/chosen/framebuffer@7dfb0000` as a 1080-by-2160 `a8r8g8b8` simple framebuffer
with stride 4352 and region `0x7dfb0000 + 0x01f90000`. Its two clock references
resolve to `CLK_INFRA_DISP_PWM` and `CLK_TOP_MUX_MM`.

In `drivers/video/fbdev/simplefb.c`, `simplefb_clocks_get()` attempts to obtain
each listed clock and defers only on `-EPROBE_DEFER`; it logs and continues on
other acquisition failures. `simplefb_clocks_enable()` similarly attempts to
prepare and enable each acquired clock, but logs and continues on failure.
Successful clocks remain enabled for the device lifetime, but no surviving
runtime log establishes that either reference succeeded in this attempt. The
driver's `fb_ops` uses the default memory operations and `fb_setcolreg`; it has
no `fb_blank` callback. In `drivers/tty/vt/vt.c`, the static `blankinterval`
behind `consoleblank` is zero-initialized and the blank timer is armed only when
that value is nonzero. Candidate J supplies no `consoleblank` argument. The
ordinary VT blank timer is therefore not a source-supported explanation for
this transition, and adding `consoleblank=0` would be a no-op.

The clock-provider boundary is important. The exact configuration contains:

```text
CONFIG_COMMON_CLK_MT6797=y
# CONFIG_COMMON_CLK_MT6797_MMSYS is not set
# CONFIG_MTK_MMSYS is not set
```

`drivers/clk/mediatek/clk-mt6797.c` is present in the image and registers the
basic MT6797 top/infra clocks. The optional MMSYS gate provider in
`drivers/clk/mediatek/clk-mt6797-mm.c` is not compiled. Consequently,
`clk_ignore_unused` can preserve other registered-but-unclaimed top/infra
clocks, but cannot enable an already-off clock and cannot retain LK-active
MMSYS gates that Linux never registered. If either explicit simplefb clock was
successfully enabled, its nonzero enable count and parent references already
protect that path from the normal unused-clock sweep without the broad flag.
The exact registered clock affected by Candidate J, if any, remains
unidentified.

## Other cleanup paths audited

### Generic power domains

`drivers/pmdomain/core.c` implements `pd_ignore_unused` and registers
`genpd_power_off_unused()` as a late initcall. Candidate J has generic OF power
domains enabled, but its exact configuration also contains:

```text
# CONFIG_MTK_SCPSYS is not set
# CONFIG_MTK_SCPSYS_PM_DOMAINS is not set
# CONFIG_MTK_INFRACFG is not set
```

No MT6797 display power domains are registered by this image. Adding
`pd_ignore_unused`, or adding a `power-domains` reference to simplefb without
first supplying the provider, cannot retain an MT6797 display domain in this
candidate and is not a valid next diagnostic.

### Regulators

`drivers/regulator/core.c` implements `regulator_ignore_unused` and
`regulator_init_complete()`. The latter queues unused-regulator cleanup with a
30-second delay. Candidate J has the regulator core but not its relevant
MediaTek hardware provider stack:

```text
CONFIG_REGULATOR=y
# CONFIG_MFD_MT6397 is not set
# CONFIG_MTK_PMIC_WRAP is not set
```

`REGULATOR_MT6351` depends on `MFD_MT6397`, so it is unavailable and absent
from the resolved configuration. There is no registered MT6351 display-supply
provider for `regulator_ignore_unused` to preserve. That parameter would
therefore be a display no-op in the exact candidate, and the core's nominal
30-second delayed cleanup is not a direct tick-04 match.

### Deferred probing and async work

`drivers/base/dd.c` implements `deferred_probe_initcall()`. Candidate J has
`CONFIG_DRIVER_DEFERRED_PROBE_TIMEOUT=10` and no module support. The initcall
triggers and flushes the current deferred-probe work, marks initcalls complete,
triggers and flushes it again, then schedules the timeout work for ten seconds
later. `async_synchronize_full()` before `/init` waits for asynchronous init
code; it does not flush arbitrary delayed workqueues.

The timeout begins before `/init`, so its position relative to visible tick 04
is not measured. This audit found no enabled native display consumer/provider
path whose timeout would explain the transition. `deferred_probe_timeout=0`
is therefore lower-confidence and is not the next candidate.

### Watchdog

The exact configuration contains:

```text
CONFIG_WATCHDOG=y
CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED=y
CONFIG_WATCHDOG_OPEN_TIMEOUT=0
CONFIG_MEDIATEK_WATCHDOG=y
```

In `drivers/watchdog/mtk_wdt.c`, `mtk_wdt_init()` detects a firmware-enabled
watchdog, marks it running and resets its timeout; this driver's maximum/default
window is about 31 seconds. In `drivers/watchdog/watchdog_dev.c`, the
handle-boot-enabled path starts periodic keepalive pings immediately. These
paths do not source-support a four-second watchdog expiry. Runtime observation
of splash/reboot, LEDs and apparent power is still required to distinguish
display loss from a whole-device reset, power-off or hang.

## Ruled-out immediate candidates

For the exact Candidate J tree and configuration, do not create the next image
by merely adding any of the following:

- `consoleblank=0`: default VT blanking is already disabled;
- `regulator_ignore_unused`: no relevant hardware regulator provider exists in
  the image;
- `pd_ignore_unused`: no MT6797 SCPSYS provider exists in the image;
- a simplefb `power-domains` property alone: its provider would be missing; or
- `deferred_probe_timeout=0`: no matching display dependency has been shown.

A later clock-ownership experiment may need the upstream MTK MMSYS and
`COMMON_CLK_MT6797_MMSYS` provider stack plus explicit consumer ownership, but
only after identifying the LK-active gates and establishing a repeatable
runtime boundary. Broad retention is evidence gathering, not a final fix.

## Second-attempt gate

The next action remains exactly one more unchanged Candidate J selection after
returning to the known-good OS, restoring normal temperature and power, and
confirming the normal recovery path. Record video if possible and capture:

- the exact first and last readable line/tick;
- screen orientation and whether black pixels or backlight loss occurs;
- selection-to-first-text and selection-to-black wall time;
- LEDs, splash/reboot and apparent final power state;
- heat or charging changes; and
- the recovery action and its outcome.

Stop after attempt 2 and reassess. Do not infer J-versus-I causality from one J
attempt, do not build another candidate yet, and do not treat the earlier
unconfirmed Candidate I selection as a matched control.
