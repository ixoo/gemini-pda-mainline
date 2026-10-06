# After Wi-Fi: remaining driver gaps (detailed order)

Detailed per-block plan derived from the eleven `2026-10-04-gemini-*-re`
source reviews. Moved here from `docs/ROADMAP.md` on 2026-10-05 so the
[roadmap](../../docs/ROADMAP.md) can state the order in one line per block.
This file keeps the reasoning, the shared-dependency table and the grouped
device tests. Each record named below owns its facts (F) and hypotheses (H).
Nothing here admits a device test.

## Scope and ranking rule

This section orders the non-Wi-Fi gaps. It was rewritten on 2026-10-04 from
the eleven source-only reverse-engineering records under
`experiments/2026-10-04-gemini-*-re/` (charging, display, PMIC basics,
Bluetooth, GPS, lid/microSD/USB, audio, sensors, GPU, cellular, camera); each
record owns its facts (F) and ranked hypotheses (H), and this section only
orders them. It does not change the Wi-Fi order above and admits no device
test; each runtime step still needs its own reviewed experiment. Steps marked
**(local)** need Julien's machine, because Buildbox and the device are not
reachable from cloud sessions. Everything else is offline patch, schema or
documentation work that can start now.

Ranking rule, unchanged in spirit: first the item that protects the battery
and the lab, then the shared foundations (PMIC interrupt path, CONSYS task
demultiplexer, I2C1), then the two usability blockers (charging, native
display), then the blocks that ride on finished foundations, grouped so that
one boot or one Gemian session answers several records at once.

### Safety first

1. **Charger regulation voltage discrepancy.** The public Gemian source
   writes a fixed `VREG` of `0x24` (4.416 V) while the 2026-07-14 live capture
   read back 4.336 V ([charging F11, H10](../2026-10-04-gemini-charging-re/README.md#part-2-hypotheses-ranked-by-value-per-device-minute)).
   If the running binary matches the public source, the stock kernel is
   over-charging a 4.35 V cell. One read-only Gemian kernel-log check of the
   periodic `[bq25890 reg@]` dump (REG06) decides it **(local)** and should be
   the first item of the next Gemian session. The
   [passive successor](../2026-10-04-gemian-session-a/README.md)
   found selector `0x1f` / 4.336 V selection logs, no REG06 dump, a zero
   high-voltage DT flag and an 800 mA AC policy cell. The
   [matched-boot binary audit](../2026-10-04-gemian-session-a/CHARGER_CV_BINARY.md)
   proves computed-only logging followed by fixed `0x24` (4.416 V nominal)
   VREG write requests; errors are ignored and hardware readback remains
   unresolved. Treat stock Gemian as requesting 4.416 V and avoid long
   unattended charge sessions under it; the Gemian-kernel REG06 observer is
   parked because the answer changes no mainline decision. On mainline, the first charger observation
   is a userspace read-only register dump with no charger node bound. The
   upstream driver ignores DT limits under `linux,read-back-settings` and
   enables charging under `linux,skip-reset`, so binding it is a separate,
   reviewed charge-policy stage that must program and verify `VREG` 4.2 V and
   `IINLIM` 500 mA before charging starts. Pump Express, OTG boost and VBUS
   role changes stay out (charging H3, H4, H9).
2. **Battery floor during mainline sessions.** Mainline has no low-battery
   protection and relies on the PMIC hardware UVLO alone
   ([PMIC H10](../2026-10-04-gemini-pmic-basics-re/README.md#part-2-hypotheses-ranked-by-value-per-device-minute)).
   Keep mainline sessions on external power or above the vendor's 3.4 V first
   threshold until the gauge driver (step 3) exists. A mainline power-off with
   the cable attached re-enters LK charging mode and looks like a reboot
   (PMIC H11); judge power-off results with the cable detached.

### Shared dependencies and missing mainline pieces

| Shared piece | Used by | Status after the records | Open item |
| --- | --- | --- | --- |
| MT6351 MFD interrupt domain (0008–0015, 0062) | Power key (EINT176), RTC alarm (IRQ 9), `CHRDET` (46) for cable and USB device-port role, ACCDET jack detection (12/13) | Never exercised on mainline; every record that needs a PMIC interrupt names it | First proof is the power key (PMIC H1); it validates the path for charging H2, audio H5 and lid/USB H2 at once |
| MT6351 regulator constraints | Dropping `regulator_ignore_unused`; VCORE/VSRAM_PROC hardware control, VDRAM, VS1/VS2, modem bucks, VSIM1/2 | Vendor constraint set decoded (PMIC F8–F10, cellular H8) | Offline: write `always-on`/`boot-on` set and keep VCORE off-limits (PMIC H7); drop the flag only in a later reviewed boot |
| Power-off and restart | Every boot's clean shutdown | Restart proven (TOPRGU). Vendor power-off is an RTC BBPU write that bypasses PSCI; mainline PSCI `SYSTEM_OFF` is untested and probably wrong | New: `mt6351-pwrc` MFD cell plus a small `mt6323-poweroff` extension (PMIC H2) |
| CONSYS/WMT owner (BTIF, STP, common init) | Wi-Fi, Bluetooth, GNSS, FM | Drafted 2026-10-04: AFE stage before MCU release (0101–0102); task framing, shared sequence/ACK and task routing (0103–0106). No task-0/2 client wired; no hardware result | 0104+0105 consolidated; wire one task-0 binding for boot C3; executor owns AFE unconditionally |
| Clock and power-domain ownership (`clk_ignore_unused`) | Retained simplefb, display PWM, Wi-Fi, GPU | Display H2 gives the first removal path: a `simple-framebuffer` node carrying the MM domain and root clocks | Missing clocks: `mfg_52m_sel` parent and `INFRA_MFG_VCG` for the GPU (GPU H5). The DSI0 interface gate exists already (display H7 closed, 2026-10-06) |
| Bus protection and resets | MFG (GPU), MD1 (modem) | Local MFG domain (0047) has no `bus_prot_mask`; vendor asserts INFRA_TOPAXI bits 21/23 and writes GPU SRAM LDO words `0x10001fbc–0xfe4`; TOPRGU `MFG_RST` is not exposed (GPU H1, H2, H4). MD1 domain is absent from mainline (cellular H2) | Offline patches to 0047 and `mtk_wdt`; two Gemian reads decide the LDO words |
| I2C1 (disabled in the board DT) | Panel bias at `0x3e`, BMI160 `0x69`, STK3x1x `0x48`, candidate MMC35240 `0x30` | Pin pair unconfirmed, probably `SCL1_0/SDA1_0` GPIO55/56 (sensors H8) | One Gemian pinmux read, then one boot serves display bias and all sensors |
| EINT controller (0005/0006) | Lid (EINT5), card detect (EINT6), ALS/PS (EINT11), IMU candidate (EINT4), FUSB301 ID (EINT3), toggle (EINT16) | No dedicated consumer accepted yet | Lid (patch 0074 as-is) is the cheapest first consumer and can ride any boot |
| Gauge and ADC | Battery telemetry, temperature, low-battery threshold | Vendor gauge is the MT6351 FGADC coulomb counter plus AUXADC; mainline has no MT6351 ADC or gauge driver (charging F15–F18, F21) | New small IIO driver modelled on MT6357–MT6373 with MT6351 offsets (charging H5) |

### Corrected assumptions

- **Panel identity is settled, not contradictory.** The loader's NT36672 probe
  succeeds only on a real ID read while the SSD2092 probe always succeeds, so
  the live `nt36672` name is a positive identification pending one LK-log read
  (display F2–F4, H1). The SSD2092 variant question remains for other units.
- **Display clock.** The vendor lane rate is 880 Mbit/s; the retained 435 MHz
  is integer truncation and patch 0043's 138.839 MHz mode clock implies
  833 Mbit/s. The mode clock should become 146.667 MHz (display H3).
- **Charger interrupt.** The vendor never uses the BQ25896 `INT` pin; cable
  events come from PMIC `CHRDET`. The upstream driver requires an IRQ at probe,
  so either a real EINT is found or a small driver change is needed
  (charging H1, H2).
- **Power key and reset.** Public Gemian delivers `KEY_ESC`; mainline should
  use `KEY_POWER`. Mainline `mtk-pmic-keys` always writes the reset register,
  so the key node must state the long-press policy explicitly; one register
  read (`TOP_RST_MISC`) decides the value (PMIC F11–F13, H3).
- **RTC reload** is a vendor convention shared with MT6323, which mainline
  already serves; considered answered pending one read test (PMIC H5).
- **Bluetooth may not need common init to start (hypothesis).** The HCI
  parser lives in ROM, so BT-on, HCI Reset and version/address reads may run
  on the already negotiated full-mode STP session before ROM patches or
  calibration (Bluetooth H1, H2, medium confidence). Boot C3 decides it, with
  the AFE stage present.
  `btmtkuart` contributes framing and `btmtk_set_bdaddr` only.
- **GNSS has a userspace cost.** The kernel shape holds (one function-control
  command, GPIO69, a `gnss` device over task 2), but the stock position engine
  is proprietary; whether the receiver speaks NMEA or binary MNL decides if
  mainline GNSS ends at raw frames or at positions (GPS H4, H5).
- **Speaker path.** The stock path is MT6351 line-out plus pulse-enabled
  GPIO243/244 amplifiers; the `0x31` MAX98926 node is unbound in the stock
  kernel. Jack detection is PMIC ACCDET, no AP EINT (audio H1, H2, H5).
- **Sensors.** No controlled rail, no vendor IMU interrupt (GPIO65 is the only
  candidate), ALS/PS on GPIO88, STK `0x11` is a naming problem that
  `sensortek,stk3311` already drives, and the magnetometer is reopened because
  the vendor's unbuilt driver is the mainline `mmc35240` register family
  (sensors H1–H6).
- **GPU.** The missing pieces are specific and small (bus protection, LDO
  words, `mfg_52m` parent, optional reset, regulator timing), the safe first
  operating point is 520 MHz at 1.000 V, and the GPU does not depend on the
  PMIC step (GPU H1–H5, H8).
- **Camera.** The front sensor matches upstream `hi556`; the irreducible
  blocker is the SENINF/CSI-2 programming held in the proprietary HAL
  (camera H1, H4, H5). **Cellular:** the AP-side bring-up is a short register
  sequence over resources mainline mostly names, but no redistributable
  CLDMA/CCCI transport exists anywhere (cellular H1–H4).

### Ordered gaps

1. **PMIC foundation (offline now, one boot).** Patches: `mediatek,mt6351-keys`
   child with `KEY_POWER` and an explicit long-press policy after integrating
   the reviewed key fixes. Preserve PSCI power-off for C1; an `mt6351-pwrc`
   cell and `mt6323-poweroff` extension wait for that baseline to fail.
   Regulator constraint set from PMIC H7 while keeping `regulator_ignore_unused`
   and logging `regulator_summary`; a probe-time read of the ten
   decision-changing PMIC registers (PMIC H8), ordered before the key child
   probes so it records the inherited `TOP_RST_MISC` before the key driver
   writes it (PMIC H3, H4); no Gemian read is needed first. One combined boot **(local)** then covers key
   events, RTC read and alarm, and a power-off attempt with the charger
   detached (PMIC H1, H2a, H5, H6). This boot also carries step 2's `CHRDET`
   count and step 5's lid test.
   Records: [PMIC basics](../2026-10-04-gemini-pmic-basics-re/README.md);
   earlier topics [MFD](../2026-09-08-mt6351-mfd-upstream-preparation/README.md),
   [keys](../2026-09-08-mt6351-keys-preparation/RESET_POLICY.md).
2. **Battery and charging (first usability blocker).** Patches: disabled
   BQ25896 node at I2C0 `0x6b` with the conservative set from charging H3
   (4.2 V first, `ICHG` 512 mA, `IINLIM` 500 mA, `IPRECHG`/`ITERM` 128 mA,
   `SYS_MIN` 3.5 V, `ti,use-ilim-pin`, no Pump Express), `linux,skip-reset`
   and `linux,read-back-settings`, interrupt per charging H1 or a small
   `bq25890` change to accept `CHRDET` plus polling; the pending
   [IRQ preflight fix](../2026-09-12-bq25890-irq-preflight/README.md).
   Correction (2026-10-04 review): read-back mode skips these DT limits and
   skip-reset enables charging at probe, so the node is bound only in a
   reviewed charge-policy stage that programs and verifies the limits first.
   Device order: Gemian reads (VREG dump, adapter type and PE+ log, live
   `bat_meter` DT; charging H10, H6, H7) **(local)**; `CHRDET` count in the
   step 1 boot (H2); a charger probe boot that dumps REG00–REG14 first and
   reads telemetry unplugged and plugged (H3, H8, H4) **(local)**; a reviewed
   charging enable after that.
3. **Gauge and ADC driver (offline, after step 2's first read).** New MT6351
   AUXADC/FGADC IIO driver (channels BATSNS/ISENSE/VCDT/BATON, `FGADC_CON0`),
   `simple-battery` with design voltages only, and a low-battery threshold
   (charging H5, PMIC H10). First boot compares BATSNS with the charger ADC.
4. **Native display (second usability blocker).** Offline, in dependency order
   ([display Part 3](../2026-10-04-gemini-display-re/README.md#part-3-what-mainline-needs-beyond-the-retained-simplefb)):
   (a) `simple-framebuffer` node with MM power domain and root clocks so
   `clk_ignore_unused` can go (H2, first half built as
   [display H2](../2026-10-06-gemini-display-h2/README.md)); (b) the
   `DSI0_INTERFACE_CLOCK` gate already exists in `clk-mt6797-mm` (H7 closed,
   2026-10-06); (c) rebase and split
   0028–0044 per the [architecture refresh](../2026-09-07-mt6797-display-upstream-architecture/README.md),
   OF-graph for 0041, display PWM as an MT6797 variant with one `main` clock
   plus the MM domain and a `pwm-backlight` (H8); (d) board nodes: TPS65132
   bias at I2C1 `0x3e` with `outp`/`outn` 5.5 V and enable GPIOs 60/251
   (H5), panel `planet,gemini-pda-nt36672` with `reset-gpios` GPIO180 (H4),
   mode clock 146.667 MHz (H3), no `vddi` (H6), portrait rotation; (e) an
   MT6797 IOMMU/SMI decision for the first OVL/RDMA path. Device order
   **(local)**: Gemian reads of the LK log, bias registers, VIO18/LDO states
   and pin 180 across a display cycle (H1, H5, H6, H4a); simplefb adoption
   boot (H2); backlight boot under simplefb (H8); panel bring-up with a `0xDB`/
   `0xF4` read before any init table (H1, H3, H4, H9). Touch follows the panel
   (H10). Keep the console on simplefb meanwhile.
5. **Small standalone wins (ride other boots).** Lid: enable patch 0074 as-is,
   one attended close/open, no `wakeup-source` (lid H1, H8). microSD: add
   `ldo-vmch`/`ldo-vmc` regulator nodes and an `&mmc1` node (GPIO67
   active-high card detect, `no-1-8-v`, ≤ 50 MHz, pinmux-only pads), read PMIC
   trim fields `0xACE`/`0xAE2` on Gemian first, never port the trim arithmetic
   (H3, H9). USB: device-port role from `CHRDET` through a small `extcon`/
   `usb-conn` consumer so forced B-session (0077) becomes conditional (H2);
   host-port VBUS is GPIO94, whose source a USB meter decides before any
   `regulator-fixed` toggle (H4); FUSB301A ID on GPIO64 as `id-gpios` (H5);
   the toggle on GPIO93 needs an owner observation (H7).
   Record: [lid/microSD/USB](../2026-10-04-gemini-lid-microsd-usb-re/README.md),
   [microSD contract](../2026-07-12-mt6797-msdc-recovery/MICROSD_CONTRACT.md),
   [VBUS record](../2026-09-08-usb-vbus-ownership/README.md).
6. **Bluetooth (may start before common init is complete).** Offline: STP task
   framing, shared link state and routing are drafted (0103–0106); next is one
   task-0 binding for boot C3, and only after H1 passes a small
   `hci_dev` over task 0 reusing `btmtk_set_bdaddr` and the H:4 receive helper,
   no vendor sleep parameters at first (Bluetooth H4, H5); `mtk-btcvsd` node
   later (H9). Device: one Gemian read of the `hci0` address decides whether
   mainline must supply a `local-bd-address` (H6) **(local)**; one boot on the
   negotiated full-mode session with VCN33-BT at 3.3 V, function-control BT-on,
   HCI Reset, version and BD_ADDR reads, with the AFE resource present and the
   version baseline and full-mode WMT query/negotiation control (H1–H3, H5)
   **(local)**; the zero-CRC frame and `0xfc6f` probes (H4) only after Reset passes. Coexistence and radio trims come later (H7, H10).
   Record: [Bluetooth](../2026-10-04-gemini-bluetooth-re/README.md).
7. **GNSS (after proven common init).** The AFE register block is drafted
   in the common-init owner (0101–0102, GPS H2). Offline now: design the
   `gnss` device over task 2 with the GPIO69 pinctrl state and VCN28 from the common power-on
   (H1, H3, H6). Device: the Gemian trace of the first `/dev/stpgps` bytes in
   one stock GNSS session (H4) must precede any mainline GNSS boot, because it
   decides NMEA versus binary MNL (H5); then one boot sending GPS function-on
   and counting task-2 frames (H1) **(local)**. FM stays last.
   Record: [GPS](../2026-10-04-gemini-gps-re/README.md).
8. **Sensors (first I2C1 boot, shared with display bias).** Patches: enable
   I2C1 on the confirmed pin pair (H8); BMI160 node at `0x69` as in patch 0052
   with the direction-7 mount matrix and no interrupt (H1); `sensortek,stk3311`
   at `0x48` (H4); then `interrupts` GPIO65/EINT4 for the IMU (H2) and
   GPIO88/EINT11 level-low for proximity (H5). Device: Gemian pinmux read of
   GPIO53–60 first; one boot reads accel/gyro/ALS/PS and performs four single
   ID reads (`0x30` reg `0x20`, `0x77` reg `0xD0`, `0x5f` reg `0x0F`) that close
   the magnetometer, barometer and humidity questions (H6, H7) **(local)**. No
   upstream ID-table change for STK `0x11` until the marketed part name is
   known. Record: [sensors](../2026-10-04-gemini-sensors-re/README.md).
9. **Audio (after step 1's `mt6351-sound` child).** Offline: AFE node, MT6351
   codec child and `mt6797-mt6351` card routed to headphones only, line-out
   muted, amplifier GPIOs untouched (H3); a small MT6351 ACCDET driver modelled
   on `mt6359-accdet` with the F10/F12 parameters (H5); the AFE YAML topic.
   Device: Gemian reads of GPIO243/244 during a low-volume tone, an `0x31`
   probe, ACCDET interrupt counts across a headset plug and the live audio DT
   (H1, H2, H5, H6, H7) **(local)**; then a −40 dB headphone tone and an AIN0
   capture boot (H3, H4) **(local)**. An external-amplifier widget or MAX98926
   node comes only after H1/H2; if H2 wins, an MT6797 I2S DAI becomes its own
   topic. Record: [audio](../2026-10-04-gemini-audio-re/README.md).
10. **GPU (after display, before sustained load needs thermal).** Patches:
    `bus_prot_mask = BIT(21) | BIT(23)` on the MFG domain in 0047 (H1); an
    infracfg write of the GPU SRAM LDO words before MFG powers on if the
    Gemian read shows reset values (H2); `assigned-clock-parents` for
    `mfg_52m_sel` and `clocks = core (MFG_BG3D), bus (INFRA_MFG_VCG)` (H5);
    MT6797 `mtk_wdt` reset entry and `resets = <&watchdog 2>` (H4); RT5735
    `enable_time` 350 µs and `ramp_delay` (H8); a named profile (not
    `gemini.fragment`) enabling `DRM`, `DRM_PANFROST`, `mfgsys`, `i2c7` and the
    RT5735 fixed at 1.000 V. Device: Gemian reads of the LDO words, `CLK_CFG`
    bits for `mfg_52m_sel` and the decoded devinfo speed bin (H2a, H5, H7)
    **(local)**; one probe-and-power-cycle boot at a fixed 520 MHz with a
    serial console or pstore (H3) **(local)**. DVFS is clock flags plus the
    uncalibrated type-12 table below 780 MHz (H6), after H3 and the thermal
    step (H9). Record: [GPU](../2026-10-04-gemini-gpu-re/README.md).
11. **Cellular and cameras (feasibility only).** Cellular: a read-only
    observation boot printing the LK `ccci` tags, SPM MD1 status at both offset
    pairs and `MD1_CFG_BOOT_STATS0/1` (cellular H1) **(local)**; a Gemian
    `ccci_dump` read of the CLDMA queue-0 ring (H5) and SIM pinmux/LDO states
    (H8). MD1 domain, PLL replay and boot-vector release (H2–H4) each need their
    own reviewed experiment, and H4 is the first to run proprietary modem code.
    Camera: Gemian log read of the SLS sensor-ID line and `camtg_sel` clock
    summary (camera H1a, H2a); then a mainline `hi556` probe boot reading one
    register with an OF match, 24 MHz PLL entry and PDN GPIO (H1b) **(local)**;
    the receiver path waits for the MT8365 SENINF/CAMSV comparison (H4) and the
    bounded register-window capture during a stock stream (H5).
    Records: [cellular](../2026-10-04-gemini-cellular-re/README.md),
    [camera](../2026-10-04-gemini-camera-re/README.md).

### Device tests, grouped by session type

Deduplicated from the eleven records so Julien can batch them. Every test is
bounded and read-only in intent unless marked; none is admitted by this list
and each still needs its reviewed experiment with identity checks.

**A. One read-only Gemian session (known-good LAN SSH).** Order by value.
Take the log, live DT and sysfs items (1, 3, 5, 9, 13's ring) first. Items 7
and 12 change hardware state (OTG attach, slider, camera open) and belong
with group B. PMIC, I2C and MMIO reads (2, 4, 6, 8, 10, 11, 13's pinmux)
each need a reviewed access path; read the AFE window (11) only with CONSYS
powered:

1. Kernel-log `[bq25890 reg@]` dump, REG06 `VREG` (charging H10, safety).
2. `TOP_RST_MISC` `0x2b6` through the bounded `pmic_access` path, read twice
   with another register between (PMIC H3, H4).
3. LK log lines for the NT36672 ID and `we will use lcm` (display H1).
4. I2C1 `0x3e` registers `0x00`, `0x01`, `0x03`, `0xFF` (display H5); live
   pinmux of GPIO53–60 (sensors H8).
5. `hciconfig hci0` / `btmgmt info`, `BT.cfg`, `[HCI-STP]` log (Bluetooth H6).
6. PMIC `0xACE`/`0xAE2` bits 4:0 (microSD H3); GPIO69 state (GPS H6).
7. `/proc/interrupts` `iddig_eint` count across one OTG-adapter attach
   (USB H6); EINT16 count and `switch` state across one slider flip (toggle
   H7).
8. `i2cdetect -y -r 0` restricted to `0x31`, and register `0xFF` if it ACKs
   (audio H1b, H2); GPIO234/235 levels idle (audio H6).
9. Live DT nodes: `bat_meter` and `battery` (charging H7), audio section and
   `accdet` (audio H7), `i2c@11010000` children (GPU H7), `chosen/atag,devinfo`
   words 8, 22, 61 and EEM words, decoded values only (GPU H7).
10. INFRACFG `0x10001fbc–0x10001fe4` with the GPU idle (GPU H2a); `CLK_CFG`
    `0x10000104` bits 2:1 and `clk_summary` for `mfg_52m_sel` (GPU H5).
11. AFE window `0x180b6000+0x100`, 64 words (GPS H2); charger battery log with
    the bundled adapter attached (charging H6).
12. Camera: SLS `ReadOut sensor id` log line after one camera-app open,
    `camtg_sel` in `clk_summary`, `SUBAF` log errors (camera H1a, H2a, H6).
13. Cellular: `/proc/ccci_dump` queue-0 ring (H5); SIM pinmux GPIO126–128/
    155–157 and VSIM1/2 enable bits with and without a SIM (H8).

**B. Attended hardware actions inside that Gemian session** (owner at the
device; each is one short action):

- Display off/on cycle while sampling pin 180 state and MT6351 LDO enable
  states (display H4a, H6, H10).
- Low-volume tone through the stock stack while sampling GPIO243/244 (audio
  H1a); headset plug/unplug while counting ACCDET sources 12/13 and reading
  `switch`/key events (audio H5); record from the headset mic while sampling
  GPIO234/235 (audio H6).
- One stock GNSS session capturing lengths and first 16 bytes of the first
  `/dev/stpgps` writes and reads (GPS H4); this decides the GNSS plan.
- USB meter on the host port with a known hub attached and with nothing
  attached, GPIO94 low (USB H4a); no device write.
- Optional: short GPU load while re-reading `0x10001fbc` (GPU H2a).

**C. Mainline boots** (each a reviewed experiment with its own candidate):

1. **PMIC, charging and lid packet.** Key node, RTC node, lid node (0074),
   MT6351 irqchip visible in `/proc/interrupts`, the ten-register PMIC read,
   `TOP_RST_MISC` read before any write. Attended: one power-key press, one lid
   close/open, one cable plug/unplug (`CHRDET`, `VBATON_UNDET`), `rtcwake` 10 s,
   then the existing PSCI `poweroff` with the charger detached; `mt6351-pwrc`
   only if that fails (PMIC H1, H4, H5, H6, H8, H2a; charging H2; lid H1;
   USB H2). C2a rides here.
2. **Charger.** (a) Read-only REG00–REG14 dump from userspace with no charger
   node bound, unplugged and plugged (charging H3, H8, H4), riding on C1.
   (b) Later, a named profile binding the driver only after the reviewed
   sequence programs and verifies the conservative limits; telemetry, gadget
   idle then enumerated. Gauge driver boot comparing BATSNS with the charger
   ADC follows (H5).
3. **Bluetooth on the negotiated session.** Candidate on the squashed
   0101–0106 chain with the AFE resource present. Controls first: repeat the
   checked version baseline and the previously validated full-mode WMT
   query/negotiation; stop on any regression. Then VCN33-BT on, BT-on,
   HCI Reset, version and BD_ADDR, second Reset after 2 s, BT off (Bluetooth
   H1–H3, H5). The zero-CRC frame and `0xfc6f` probe (H4) wait until Reset
   has passed and their effects are reviewed.
4. **Display adoption and backlight.** simplefb node with MM domain and
   `clk_ignore_unused` removed (display H2); then display PWM plus
   `pwm-backlight` under simplefb with `CON_0`/`CON_1` readback (H8).
5. **I2C1 bus boot.** BMI160, STK3311, bias chip if not read on Gemian, four
   single ID reads at `0x30`/`0x77`/`0x5f`, device flat and on each edge
   (sensors H1, H4, H6, H7; display H5 fallback). Then interrupts (H2, H5).
6. **microSD and USB host.** `&mmc1` with VMCH/VMC, trim and IOCFG_B fields
   read at entry, one known file read (microSD H3, H9); GPIO94
   `regulator-fixed` toggled once with the meter on the port and charger
   unplugged, GPIO64 and FUSB301 status with and without a partner
   (USB H4b, H5).
7. **Audio card.** Headphone-only card, −40 dB tone, AIN0 then AIN2 capture,
   `AUDDEC_ANA_CON0` readback (audio H3, H4, H8).
8. **Panel bring-up.** `0xDB`/`0xF4` DCS read before any init table, PCW
   readback and vblank-derived refresh, two DPMS cycles reading `0x0A`
   (display H1, H3, H4b, H9). Touch probe at `0x62` and `0x53` after.
9. **GPU probe.** Fixed 520 MHz at 1.000 V, `clk_summary` before probe,
   INFRA_TOPAXI bits 21/23 and LDO words read, probe line, one runtime
   suspend/resume cycle; stop on any SCPSYS or TOPAXI timeout (GPU H1–H3).
10. **GNSS first frames** after proven common init (GPS H1, H3).
11. **Cellular observation** (tags, SPM status, boot status; cellular H1) and
    **camera probe** (`hi556` one-register read, I2C3; camera H1b, H6).

Boots 1–3 need nothing from the Wi-Fi order; the installed version-read
candidate has been consumed successfully; boot 4 removes a global flag and should precede
5–9; boot 10 waits for common init. Current order after review: C1 (with
C2a), C3, Wi-Fi common-init boot, C2b; remaining Gemian A items run when
convenient and gate none of these.

### Leads from owner-held reference documents

The owner keeps a local set of reference documents that is not in Git: the
public 96Boards X20 (MT6797) functional specification, schematic and BOM,
vendor datasheets (BQ25896, TPS65132, FUSB301A, DA9213/14/15, AW9523B),
2017 MT6351 mailing-list patches, and third-party Gemini notes (Gemian wiki
and bsg100). The SoC and X20 material is marked confidential and most
datasheets have no redistribution grant, so cite them by name only. They are
leads to check against this unit, not facts. Items the 2026-10-04 records
settled from source are dropped here; what remains:

- **Two panel/touch variants are likely.** bsg100 reports I2C4 `0x53`
  answering with nothing at `0x62` on its unit, while the retained 2019
  `novatek_ts_fw.bin` (see the [firmware boundary](../../docs/hardware/firmware.md)) is a
  Novatek NT36xxx-layout image. Make the touch probe read both addresses with
  touch reset released, and plan the board description for both variants.
- **Panel bias.** The TPS65132 datasheet gives fixed address `0x3e`, VPOS/VNEG
  at `0x00`/`0x01` and a ±5.4 V reset value, consistent with display H5.
- **Charger.** bsg100 reports boost enable on GPIO107 in addition to
  `OTG_CONFIG`; the BQ25896 watchdog reverts settings unless serviced or
  disabled (charging H8); the interrupt is an active-low 256 µs pulse
  (charging H1).
- **Sensors.** The marketed name of the STK `0x11` part may be in the Planet
  BOM notes; it is the discriminator for an upstream ID-table change
  (sensors H4).
- **USB.** GPIO93 (EINT16) has IDDIG as an alternate function; the records
  instead find the toggle there (lid/USB H7). FUSB301A at `0x25` implies its
  address pin is strapped high on both buses.
- **Connectivity.** MT6631 integrates FM; VCN18 feeds Wi-Fi/BT and GPS 1.8 V,
  VCN33 the Wi-Fi/BT 3.3 V supply, VCN28 the FM supply. The retained
  `WMT_SOC.cfg` holds four keys (shared antenna, no firmware GPS LNA pin,
  `co_clock_flag=0`) and no voltage, trim or calibration setting; GPIO69 LNA
  control belongs to the host (GPS H6).
- **GPU.** If the documents cover INFRACFG `0x10001fbc–0xfe4` or the
  `0x180b6000` AFE block, they settle GPU H2 and GPS H2 without a device read.
- **Board differences.** X20 addresses do not carry over: its `0x6b` is an
  MT6313 buck, while the Gemini has a BQ25896 there.

The [workstream registry](https://github.com/ixoo/gemini-pda-mainline/blob/164c2d3f/project/workstreams.json) keeps owners; this
section only orders the work. Start now with the offline items of steps 1, 2
and 6; the installed version-read candidate is consumed, so build and
schedule boot C1 next (see the 2026-10-04 review under Current plan).
