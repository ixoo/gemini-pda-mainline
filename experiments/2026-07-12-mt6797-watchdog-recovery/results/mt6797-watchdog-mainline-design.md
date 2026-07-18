# MT6797 watchdog mainline design

## Contract comparison

| Property | Vendor/live evidence | Linux 7.1.3 | Decision |
| --- | --- | --- | --- |
| Register block | TOPRGU `0x10007000`, 0x1000 vendor window | `watchdog@10007000`, 0x100-byte mapped window | Reuse generic driver resource; keep board range conservative |
| Compatible | `mediatek,mt6797-toprgu` in vendor DT | `mediatek,mt6797-wdt`, fallback `mediatek,mt6589-wdt` | Use upstream watchdog compatible pair |
| Mode/keys | MODE key `0x22000000`, restart `0x1971`, SWRST `0x1209` | Same constants and operations | No new register driver |
| Bark/pretimeout IRQ | GIC SPI137, `IRQ_TYPE_EDGE_FALLING`; live global IRQ169, zero count in sample | Optional `interrupts` accepted by binding/driver | Add SPI137 on the Gemini board node |
| Standard user ABI | None; vendor WDK kicks external WDT | `watchdog` core and `/dev/watchdog0` | Replace private ABI with standard watchdog core |
| Reset controller | Vendor exposes broad SWSYSRST and private request paths | Upstream TOPRGU reset provider | Reuse only generic reset-controller IDs already described upstream |

## Why this is not a new driver

The vendor and Linux implementations agree on the core register offsets,
write keys, timeout tick conversion, restart sequence, and reset-controller
shape. Linux already lists the MT6797 compatible as a fallback to the MT6589
watchdog data. The missing Gemini-specific fact is the bark IRQ, not a
different chipset protocol.

The vendor WDK layer also controls SPM, modem, thermal, EINT, and power-key
request routes. Those are policy and cross-subsystem reset contracts, not
requirements for a standard watchdog probe. Copying them would silently make
mainline resets depend on vendor firmware and modem state.

## Probe-time side effects

The Linux reuse decision does not make a watchdog probe read-only. In
`mtk_wdt_probe()`, an optional bark IRQ is requested before registration, and
`mtk_wdt_init()` reads `WDT_MODE`; if the retained firmware left the TOPRGU
timer enabled, it calls `mtk_wdt_set_timeout()`, which writes `WDT_LENGTH` and
reloads the timer through `WDT_RST`. A mainline boot can therefore alter an
already-running watchdog even before userspace opens `/dev/watchdog0`.

The vendor capture proves only that no standard watchdog device exists and
that the separate external WDK keepalive is active; it does not expose the
TOPRGU `MODE` bit. The first mainline boot must therefore treat watchdog probe
as a state-changing operation, capture the early console, and keep the node or
driver disabled if the retained boot handoff cannot guarantee a quiescent
TOPRGU state. Do not describe this as a read-only probe.

## Board change

The Gemini board patch adds the vendor-confirmed interrupt to the existing shared node:

```dts
&watchdog {
	interrupts = <GIC_SPI 137 IRQ_TYPE_EDGE_FALLING>;
};
```

No reset-output disable, timeout, nowayout, SPM request, or modem-watchdog
property is added. The inherited node remains available to the generic driver,
but no user-space watchdog action is implied by the DTS change alone.

## Runtime correction (2026-07-18)

Candidate L strongly reached its tracked external `/init`, where
`/dev/watchdog0` was absent through the visible `remaining=5s` check. The
consumer's falling-edge flag is routed through MediaTek SYSIRQ, which programs
the polarity inverter and presents a rising edge to the parent GIC; replacing
it with rising or level-high would therefore be unsupported. Because the
upstream watchdog probe requests an optional IRQ before registering the device
and returns if that request fails, the next diagnostic omits the optional bark
IRQ while retaining the basic upstream watchdog and reset path. This does not
retract the vendor/live SPI137 observation; it defers pretimeout support until
the mapping/request failure is captured. See the
[registration audit](../../2026-07-17-uart-pstore-observability/results/watchdog-registration-audit-20260718.txt).

## Bring-up gates

1. Build the board DT with `CONFIG_MEDIATEK_WATCHDOG=y` and verify the driver
   probes without changing the active hardware state.
2. Boot with external console/recovery access and check that only the standard
   watchdog device enumerates; do not open it or issue `KEEPALIVE`.
3. Confirm the bark IRQ is requested and remains quiet while no pretimeout is
   armed. A zero interrupt count on the vendor kernel is baseline evidence,
   not a test of mainline delivery.
4. Review reset-controller consumers independently. Do not attach display,
   modem, SPM, or thermal reset-request routes until their ownership is
   documented.
5. If a pretimeout or restart test is approved, use a short, externally
   monitored trial with a known-good image and a physical recovery path.

## Source identities

The VM analyzer records the complete input hashes. Key audited identities are:

- vendor MT6797 watchdog implementation:
  `drivers/watchdog/mediatek/wdt/mt6797/mtk_wdt.c`;
- vendor MT6797 register header:
  `drivers/watchdog/mediatek/wdt/mt6797/mt_wdt.h`;
- Linux watchdog driver SHA-256:
  `6e8230dff7db590f16bdc83918220da48be57c8a594cd3f0917f4c0e0018da9b`;
- Linux watchdog binding:
  `mediatek,mtk-wdt.yaml`.

Vendor files remain cited as Git evidence only and are not copied into this
repository.
