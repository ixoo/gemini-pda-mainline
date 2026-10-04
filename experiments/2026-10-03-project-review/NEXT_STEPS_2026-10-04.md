# Follow-up review: plan and peripheral RE, 2026-10-04

Reviewed origin at `880683045693aa36872f34fbb3a26d4681e92fe4` after a
fast-forward pull. Local documentation changes were preserved and reapplied
without conflicts. This is an offline review checkpoint: no build, boot,
device access or driver implementation occurred. The [roadmap](../../docs/ROADMAP.md)
continues to own priorities; this note records review findings and the gates
needed to carry out its current order.

## Assessment

The eleven `2026-10-04-gemini-*-re` records make the peripheral work more
concrete. Their source inventories name revisions, sizes and hashes; all
eleven JSON files parsed, and their path/hash entries had sizes and URLs.
This check did not re-fetch every input or independently reproduce every
source conclusion. Most records use Gemian `8cfe6596`; the current Wi-Fi
join uses `59e00a91`. Board DTS and running binary differences remain explicit
limits. None of the new records establishes new mainline hardware support.

The highest-value dependency findings are PMIC IRQ delivery shared by keys,
RTC, cable detection and jack detection; I2C1 shared by sensors and panel
bias; and one CONSYS owner shared by Wi-Fi, Bluetooth and GNSS. Source work
on these can proceed before Wi-Fi receives its first frame. Device tests
still need exact candidates, finite effects and stop conditions.

## Corrections to resolve before implementation

1. **Charger probe is not read-only and the proposed DT limits are not
   enforced in read-back mode.** Charging F20 and the roadmap combine
   `linux,skip-reset`, `linux,read-back-settings` and conservative DT limits.
   The existing [IRQ preflight review](../2026-09-12-bq25890-irq-preflight/README.md)
   already records probe writes. Inspection of its retained driver confirms:
   `bq25890_fw_probe()` returns before parsing the limit properties in
   read-back mode; `bq25890_rw_init_data()` reads existing values;
   `bq25890_hw_init()` explicitly enables charging when reset is skipped,
   disables the watchdog and configures ADC conversion. Thus those properties
   neither enforce 4.2 V nor guarantee 500 mA input. First collect the existing
   Gemian REG06 log and baseline state. Before enabling a mainline node,
   review the exact pinned driver, every probe/notifier write, IRQ handling,
   and how safe limits are programmed and verified before charging can start.
   Keep observation and charge-policy enablement as separate stages.
2. **Bluetooth before common init is a hypothesis.** Bluetooth H1 has medium
   confidence and a negative branch; the roadmap's statement that it needs
   no common init is stronger than the evidence. A bounded BT-on/HCI Reset
   test can decide this. A missing function-control event alone cannot prove
   patches are required: power, framing and ownership must also be checked.
   Do not advertise Bluetooth readiness or design the whole driver around an
   unmeasured ROM assumption. Defer malformed-frame and vendor-opcode probes
   until the positive Reset control passes and their effects are reviewed.
3. **The connectivity AFE finding belongs before MCU release.** GPS F12/H2
   identifies an omitted hardware power-on stage, not a GNSS-only operation.
   The retained `59e00a91` source used by the current Wi-Fi audit also has the
   eleven active writes before reset release; the WF_TX_02 write is commented
   out. Join the exact offsets, values, configuration branches and ownership
   into the [common-init review](../2026-10-03-mt6797-wifi-audit/COMMON_INIT_REVIEW.md)
   before implementation. Do not copy the vendor's unchecked mapping or bulk
   debug dump. A stock register image corroborates state, not register meaning
   or proof that these writes explain zero reception.
4. **Session grouping does not make every action passive.** Camera-app open,
   playback, GNSS tracing, OTG attach and GPU load change running hardware.
   I2C register selection is a bus transaction; arbitrary MMIO reads can have
   side effects or fault on unpowered blocks. Split ordinary log/DT/sysfs
   collection from these individually bounded actions. Resolve safe access
   paths and read-sensitive registers before collecting windows.
5. **Keep PMIC power-off diagnosis before its replacement.** PMIC H2 asks
   first whether existing PSCI power-off works with the cable detached, then
   proposes a `pwrc` extension if it fails. The roadmap's first packet should
   preserve that baseline; adding the replacement first loses the comparison.
   TOP_RST_MISC must be read before the keys driver's unconditional write.

## Prepared execution order

| Next step | Deliverable | Exit criterion / branch |
| --- | --- | --- |
| 1. Finish the installed WMT-version measurement | Use the already validated [version-read experiment](../2026-10-03-mt6797-wmt-versions/README.md); preserve exact boot identity and classified chip/HW/ROM events | Checked tuple selects ROM applicability; unknown or incomplete tuple stops patch selection. Preserve evidence and use reviewed recovery. |
| 2. Join the AFE stage and finish common-init contracts offline | One source-backed power-on order, selected ROM sequence, DLM/MCU effects, two PA regulator handles, calibration validation and cleanup | Each operation has an attributable result, deadline and first-error cleanup; unresolved register/event semantics stay explicit gates. |
| 3. Prepare one Gemian reference packet after the mainline session | Logs first: charger REG06, power/adapter state, live DT, panel LK log, Bluetooth address privately. Then reviewed TOP_RST_MISC and I2C1 pinmux reads | Resolve charging discrepancy, long-press policy and bus pins; missing evidence defers the corresponding node. Expand to attended peripheral actions only with their protocols ready. |
| 4. Implement the re-triggerable common-init executor | Extend the existing owner, then the existing START/channel-40 passive-scan path; no new one-shot selector family | Successful ordered initialization plus nonzero firmware management count, host frame and BSS evidence. If still zero, compare remaining vendor differences in the same boot within its reviewed budget. |
| 5. Prepare the first PMIC/lid packet and a small STP channel interface | Explicit keys policy, early PMIC baseline reads, RTC/alarm and lid observations; task-0 delivery with WMT ownership retained | Key/RTC/lid results are independent; BT Reset is a separate positive control. Neither packet depends on claiming Wi-Fi traffic works. |
| 6. Enable charger only after the correction above | IRQ preflight plus an explicit, verified conservative charge-policy sequence in a named profile | Confirm actual register settings and telemetry; no boost, Pump Express or USB role changes. Gauge/ADC follows voltage comparison. |
| 7. Remove global flags incrementally | First retained simplefb MM/clock ownership; later regulator constraints with the ignore flag retained for observation | Stable console and recovery before further display, sensor or regulator ownership changes. Native display still needs clock, PHY and IOMMU/SMI gates. |

The installed image remains the checked-version candidate with full-partition
SHA-256 `391f44a8f5c79467f3a2741bcad51c95ea34791248585baae69b0a19f852ac73`.
Its receipt says installed and shut down, physical boot2 selection pending;
this review provides no new live boot evidence. Do not overwrite it to batch
peripheral tests before consuming its unique measurement.

After a received Wi-Fi frame, keep the product gate: WPA2 association, DHCP,
ping, ten minutes of SSH, then DMA/IRQ and restart/unbind evidence in a clean
profile. A build or successful scan completion alone does not satisfy it.
Later peripheral order remains display/I2C1, microSD/USB, headphone-first
audio, bounded fixed-point GPU, and GNSS only after common init and a stock
protocol trace. Cellular and camera remain feasibility work; A72, aggressive
DVFS, unprotected sustained GPU load and loader replacement remain parked.

## Validation and boundary

Only this note and its link in the project-review README are new review work.
Pre-existing local documentation and untracked research directories are
excluded. `./scripts/check-repository` passed, including local link and
sensitive-pattern checks; `git diff --check` passed. The Linux-only artifact
provenance fixture was skipped on this host. No kernel build, checkpatch,
DT-schema check or runtime test was performed for this documentation-only
review; future implementations retain the normal Buildbox, DT and device gates.
