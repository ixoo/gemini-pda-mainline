# Experiment: live vendor-to-mainline gap audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-14-live-vendor-mainline-gap-audit` |
| Status | `completed` for a read-only comparison; mainline runtime remains untested |
| Subsystem | boot handoff, UART, eMMC, PMIC, CPU power, reservations, transport |
| Device variant | Gemini PDA running Gemian; exact retail sub-variant is not independently established |
| Date(s) | 2026-07-14 |
| Investigator(s) | Codex |
| Tracking issue | — |

## Question or hypothesis

Which live vendor-kernel contracts already have a directly reusable Linux 7.1.3
representation, and which observations still require a new driver or a runtime
boot experiment? The vendor capture is evidence for comparison, not proof that
the candidate mainline DT or driver has operated on hardware.

## Provenance and environment

- Vendor runtime capture: `artifacts/device-inventory/20260714T210731Z-vendor-baseline-refresh/mainline-runtime.txt`
- Mainline package result: `experiments/2026-07-13-mainline-handoff-closure/results/handoff-closure-current-77-package-20260714.txt`
- Mainline source: Linux `7.1.3`, patchset SHA-256 `b7721ab55e41e5c19df07b6f542354dca1e39d9d236087a6caf725f31317a963`
- Mainline package: `linux-7.1.3-gemini-b7721ab55e41`
- The raw capture is private, mode 0600, and Git-ignored. Only the sanitized
  fields emitted by the comparison script belong in `results/`.

## Safety assessment

This investigation is read-only. It uses an already captured vendor snapshot
and static package evidence; it does not flash, reboot, bind or unbind a
driver, scan a bus, write a register, or use sudo on the device.

## Associated code

- `scripts/compare-runtime-boundaries.sh` — deterministic allow-list comparison
  of the private runtime capture and the tracked static handoff result.

Run it with:

```sh
experiments/2026-07-14-live-vendor-mainline-gap-audit/scripts/compare-runtime-boundaries.sh \
  --runtime artifacts/device-inventory/20260714T091601Z-vendor-baseline/mainline-runtime.txt \
  --handoff experiments/2026-07-13-mainline-handoff-closure/results/handoff-closure-current-72-package-20260714.txt \
  --output experiments/2026-07-14-live-vendor-mainline-gap-audit/results/runtime-boundaries-current-20260714.txt
```

The checked-in result below was generated from the refreshed capture and is
byte-repeatable when those two inputs are unchanged.

See [`results/runtime-boundaries-current-77-20260714.txt`](results/runtime-boundaries-current-77-20260714.txt).

## Observations and analysis

The refreshed vendor image reports `3.18.41+`, `mediatek,MT6797`, ten possible/present
CPUs with only a subset online (`0-1` in this capture; an earlier read reported
`0-1,4`), `mt-cpufreq`, four `mtk-uart` platform devices,
an active DF4064 eMMC, 32 regulator entries, and no module namespace. The
standalone vendor `mt-pmic` and `mt-rtc` devices are bound while the
`1000d000.pwrap` platform device is unbound. It also
reports BTIF DMA/IRQ activity, WLAN wakeups, vendor CPU-DVFS transitions, and
dynamic CONSYS/SCP/SPM/CCCI reservations. The mainline package statically
contains the generic PSCI/timer/GIC/8250-MTK/MSDC/watchdog handoff and the
pre-LK dynamic reservation classes, but deliberately has no MT6797 CPU-DVFS,
BTIF/WMT, CCCI, or active multimedia consumer path.

The comparison therefore separates direct reuse from gates:

- UART, PSCI/timer/GIC, and eMMC are resource-level reuse candidates, pending a
  non-primary boot and logs.
- PWRAP/MT6351 is a first-boot dependency. The vendor pwrap platform device is
  unbound because its PMIC functionality is exposed through standalone bound
  `mt-pmic`/`mt-rtc` devices; mainline's parent-PWRAP/child-MT6351 model is an
  architectural replacement, not a one-to-one vendor binding match. Successful
  mainline PMIC probe is still not established by this capture.
- Vendor `mt-cpufreq` and suspend activity are not evidence for enabling a
  generic mainline DVFS policy. Keep CPU power consumers disabled until the
  MT6797 clock/voltage/EEM contract is recovered.
- BTIF/WLAN, modem CCCI, and their firmware/shared-memory ownership remain new
  transport work; generic Linux subsystem interfaces can still be reused.
- The vendor's dynamic reservation roles correspond to the retained pre-LK
  handoff design, although runtime `mblock-*` labels differ from the static
  mainline names; only a mainline boot can verify final allocator ownership.

## Conclusion

`confirmed` for the scoped static comparison and `inconclusive` for runtime
mainline support. The vendor snapshot is a useful baseline, not a mainline
hardware-support result.

## Follow-up

- Boot a non-primary candidate and rerun the same collector with
  `--kind mainline-candidate`.
- Compare final `/proc/iomem`, CPU online state, eMMC probe, PWRAP/MT6351 logs,
  and driver bindings against this result before enabling additional consumers.
- Keep the [handoff closure](../2026-07-13-mainline-handoff-closure/README.md),
  [MT6797 source census](../2026-07-14-upstream-mt6797-coverage-audit/README.md),
  and subsystem experiments as the authoritative implementation inputs.
