# Experiment: MT6797 TOPRGU watchdog recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-12-mt6797-watchdog-recovery` |
| Status | `inconclusive` for mainline runtime; generic driver reuse and board IRQ recovered |
| Subsystem | MT6797 TOPRGU watchdog, pretimeout, reset controller, and vendor WDK boundary |
| Device variant | Gemini PDA running Gemian, `MT6797X` / `mediatek,MT6797` |
| Date(s) | 2026-07-12 |
| Investigator(s) | Repository maintainer with Codex assistance |
| Tracking issue | Not yet assigned |

## Question or hypothesis

Does Gemini require a new watchdog driver, or does Linux 7.1.3 already model
the MT6797 TOPRGU register and reset protocol? Which board-specific resource is
missing from the shared Linux device-tree node?

## Provenance and environment

- Live device: Gemian Linux `3.18.41+`, read-only SSH capture.
- Vendor source evidence: Gemian reference commit
  `d388d350cb2dda8f23b99be6fa5db9628896e87f`.
- Mainline comparison: prepared Linux `7.1.3` tree in the development VM.
- Private capture: `artifacts/device-inventory/20260712-live/watchdog.txt`
  (Git-ignored).
- Refreshed read-only capture: `artifacts/device-inventory/20260714-live/watchdog.txt`
  (SHA-256 `87110c1907b2707e5e2224669d135fa4b1b5f4323abff7e32c1b74980cdbfb16`,
  Git-ignored and mode 0600).
- Board DTS change: [`0053-arm64-dts-mediatek-gemini-add-toprgu-watchdog-irq.patch`](../../patches/v7.1.3/0053-arm64-dts-mediatek-gemini-add-toprgu-watchdog-irq.patch).

## Safety assessment

All collection and source analysis are read-only. The collector does not open
`/dev/watchdog`, read or write watchdog registers, change timeout or nowayout,
send a keepalive, request a reset, or reboot the device. It only reads sysfs,
procfs, the flattened DT, and filtered kernel messages.

Watchdog start/stop/restart testing is explicitly deferred. A failed watchdog
test can reset the device within seconds and can destroy an otherwise useful
debug session. Before testing, provide an external console, a known-good
recovery/boot path, a named hardware owner, an independent timer, and a clear
stop condition. Do not enable vendor WDK or modem reset side channels in the
mainline board ABI.

## Associated code

- [`scripts/analyze-mt6797-watchdog-contract.sh`](scripts/analyze-mt6797-watchdog-contract.sh)
  compares vendor register/DT code with Linux 7.1.3 source and hashes the local
  board patch.
- [`scripts/collect-live-watchdog.sh`](scripts/collect-live-watchdog.sh)
  collects standard watchdog, interrupt, DT, configuration, and log metadata
  without touching watchdog state.
- [`results/mt6797-watchdog-mainline-design.md`](results/mt6797-watchdog-mainline-design.md)
  records the reuse decision and bring-up gates.
- [`results/mt6797-watchdog-source-audit.txt`](results/mt6797-watchdog-source-audit.txt)
  contains bounded analyzer output from the pinned VM trees.
- [`results/mainline-watchdog-validation-20260713.txt`](results/mainline-watchdog-validation-20260713.txt)
  records the historical 72-patch DT/config/schema validation without opening or
  starting the watchdog.
- [`results/watchdog-probe-safety-audit-20260713.txt`](results/watchdog-probe-safety-audit-20260713.txt)
  records the source-level probe-time side effect audit.
- [`scripts/audit-current-package-policy.sh`](scripts/audit-current-package-policy.sh)
  and [`results/mainline-watchdog-current-72-policy-20260714.txt`](results/mainline-watchdog-current-72-policy-20260714.txt)
  refresh that audit against the authoritative 72-patch package, including the
  watchdog-core boot-enabled policy. The older 71-patch result remains
  historical provenance.

Run the source audit from the VM:

```sh
./experiments/2026-07-12-mt6797-watchdog-recovery/scripts/analyze-mt6797-watchdog-contract.sh
```

Run the device collector only through the authorized private SSH path:

```sh
ssh -i artifacts/credentials/gemini_ed25519 \
  -o IdentitiesOnly=yes -o IdentityAgent=none -o BatchMode=yes \
  gemini@192.168.1.50 'bash -s' \
  < experiments/2026-07-12-mt6797-watchdog-recovery/scripts/collect-live-watchdog.sh \
  > artifacts/device-inventory/20260712-live/watchdog.txt
```

## Procedure

1. Inspect the vendor MT6797 TOPRGU header, implementation, common reset
   provider, and DT node at `0x10007000`.
2. Inspect Linux 7.1.3 `drivers/watchdog/mtk_wdt.c`, its binding, and the
   inherited MT6797 SoC watchdog node.
3. Collect live watchdog device nodes, interrupts, DT properties, configuration,
   and bounded kernel messages without changing state.
4. Add only the vendor-confirmed bark IRQ to the Gemini board DTS; do not add
   reset-output policy, timeout policy, or vendor character interfaces.

## Observations

- Vendor MT6797 TOPRGU is at `0x10007000`; its register layout uses the same
  `MODE`, `LENGTH`, `RESTART`, `STATUS`, `SWRST`, and `SWSYSRST` offsets as the
  upstream MediaTek driver. The vendor header uses the same key values
  (`0x22000000`, `0x1971`, `0x1209`, and `0x88000000`).
- Vendor DT identifies `mediatek,mt6797-toprgu` and supplies
  `GIC_SPI 137 IRQ_TYPE_EDGE_FALLING`.
- The live DT confirms the same `0x10007000` node and encoded SPI137 edge-fall
  resource.
- Live vendor interrupts show `mt_wdt` on global IRQ169 with zero interrupts in
  the sample. Modem watchdog lines `MD_WDT` and `MD2_WDT` are separate and also
  idle; they are not the application TOPRGU watchdog resource.
- The live vendor kernel exposes no standard `/sys/class/watchdog` device and
  no `/dev/watchdog*`. Its configuration has `CONFIG_MTK_WATCHDOG=y` but no
  `WATCHDOG_CORE`; vendor WDK logs show an external watchdog keepalive roughly
  every 20 seconds.
- Linux 7.1.3's `mtk_wdt` binding already lists
  `mediatek,mt6797-wdt` as a fallback to `mediatek,mt6589-wdt`. The driver
  implements the standard watchdog core, optional bark/pretimeout IRQ, system
  reset, and TOPRGU reset-controller operations.
- The authoritative current 72-patch package sets
  `CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED=y`.
  If LK leaves TOPRGU running, watchdog-core starts a keepalive worker when
  the driver registers and continues pinging it until userspace takes over;
  this is an explicit boot policy, not a passive device description. The
  current package-specific source/config/DT evidence is in
  [`mainline-watchdog-current-72-policy-20260714.txt`](results/mainline-watchdog-current-72-policy-20260714.txt).
- Linux probe is not guaranteed read-only: `mtk_wdt_init()` checks `WDT_MODE`
  and, if retained firmware left TOPRGU enabled, writes `WDT_LENGTH` and
  reloads `WDT_RST` before userspace opens `/dev/watchdog0`. The vendor capture
  does not expose that mode bit, so the first mainline boot must treat watchdog
  probe as state-changing until a quiescent handoff is proven.
- The shared Linux `mt6797.dtsi` node has the correct compatible and register
  range but no interrupt property. Without the board override, Linux can
  expose a basic watchdog but cannot request the Gemini bark/pretimeout IRQ.

## Analysis

This is a reuse case, not a new-chip driver case. The register offsets, write
keys, timeout conversion, restart sequence, and reset-controller shape match
the upstream generic MediaTek driver. The vendor WDK and `wd_api` interfaces
are larger policy surfaces (SPM request bits, modem watchdog routing, AEE
diagnostics, power-key reset semantics); they are not evidence that Linux must
reproduce those private interfaces.

The board patch adds only:

```dts
&watchdog {
	interrupts = <GIC_SPI 137 IRQ_TYPE_EDGE_FALLING>;
};
```

It deliberately does not set `mediatek,disable-extrst`,
`mediatek,reset-by-toprgu`, `timeout-sec`, or any modem/SPM request property.
Those choices change reset policy and need a separate controlled experiment.

## Conclusion

`inconclusive` for mainline runtime, but the driver decision is confirmed at
the source/resource level: reuse Linux `mtk_wdt`; add the Gemini bark IRQ as
board data; do not write a new MT6797 watchdog implementation. The vendor
watchdog’s active keepalive and absence of a standard watchdog node make a
mainline boot test safety-sensitive, not evidence of a missing driver.

Runtime evidence on 2026-07-18 supersedes the earlier assumption that adding
the bark IRQ was ready for first use. Candidate L reached external `/init`, but
`/dev/watchdog0` was absent through its reported `remaining=5s` check. The
falling edge is not itself invalid: the inherited MediaTek SYSIRQ driver
programs the polarity inverter and translates it to a rising edge for the
parent GIC. The optional mapping/request path remains unproven, however, and
`mtk_wdt_probe()` returns before watchdog registration if that request fails.
The next diagnostic therefore omits the optional IRQ while retaining the
generic MMIO watchdog; it does not guess a different polarity. See the
[registration audit](../2026-07-17-uart-pstore-observability/results/watchdog-registration-audit-20260718.txt).

## Follow-up

- [Mainline watchdog design result](results/mt6797-watchdog-mainline-design.md)
- [Source audit output](results/mt6797-watchdog-source-audit.txt)
- [Hardware support matrix](../../docs/HARDWARE_SUPPORT.md)
- [Live resource map](../../docs/hardware/mt6797-live-resource-map.md)
- [Candidate L registration audit](../2026-07-17-uart-pstore-observability/results/watchdog-registration-audit-20260718.txt)

The next test is a mainline boot with an explicit watchdog safety decision:
either keep the node/driver disabled until TOPRGU state is known quiescent, or
have an external console and recovery owner monitor the probe-time writes. Only
after that should `/dev/watchdog0` enumeration, IRQ registration, or a
separately owned pretimeout/keepalive test be considered.
