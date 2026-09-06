# MT6797 mainline connectivity interface and lifecycle design

## Result

The default hypothesis is supported: MT6797 connectivity needs no new
userspace lifecycle ABI. A standard platform-driver split, kernel firmware
loading, cfg80211/rfkill operation and an optional standard health reporter can
cover every admitted lifecycle responsibility. The retained
`wmt_loader`/`wmtdetect` ioctl sequence is compatibility evidence only. It is
not copied, emulated or made a prerequisite for a distribution.

This is an implementation-facing design, not a driver or binding. It performs
no power, reset, remap, protection, firmware, DMA, radio or device action. It
does not establish runtime or hardware support. [decisions.json](decisions.json)
records all eight decisions and the tested hypothesis;
[state-model.json](state-model.json) records the lifecycle and typed errors;
[proposal-map.json](proposal-map.json) classifies every proposal input.

## Standard ownership boundary

One common CONSYS provider owns the effect-bearing shared state:

- island power admission and the coherent OFF result, while the established
  genpd, clock and reset providers keep their physical resource authority;
- coordination of common reset and every affected WMT, WLAN, BT, GNSS,
  firmware or secure-world claim;
- the shared remap register fields, including serialized masked updates,
  generation validation and readback;
- the boot-resolved reserved EMI resource, its WLAN and WMT subranges, mapping
  lifetime, copy visibility and secure protection policy/result; and
- admission of a WLAN HIF epoch and coordination of AP-DMA shared prerequisites.

The WLAN consumer owns its immutable `request_firmware()` buffer, complete
private image plan, ordered protocol ledger, HIF transaction, firmware
readiness observation and cfg80211 objects. It never receives a raw physical
EMI address, shared MMIO pointer, reset operation or permission word. A future
DMA backend obtains one channel through the normal controller interface; the
DMA controller owns the block and the CONSYS provider coordinates only the
channel's shared clock/protection prerequisites. PIO does not activate or reset
AP-DMA.

The provider should live under `drivers/soc/mediatek/`; the WLAN client belongs
under `drivers/net/wireless/mediatek/`. Their connection is a private typed
kernel interface and device relationship described by reviewed DT bindings.
Generic MT6797 SoC data and Gemini board description stay separate. Final path,
binding and maintainer choices remain review questions, not facts claimed here.

## No-new-ABI hypothesis test

The design tested the vendor lifecycle operations by responsibility rather than
assuming the default:

| Need | Standard owner/interface | Why no new ABI is needed |
| --- | --- | --- |
| Dependency and bind order | Platform probe, device relationships and probe deferral | Missing common ownership prevents WLAN publication without a user command. |
| Firmware identity and bytes | Compatible data plus `request_firmware()` | Stable firmware names can be reviewed without exposing private bytes or a loader protocol. |
| Network registration and control | cfg80211, normal net-device interfaces and rfkill | User policy remains standard; registration follows firmware readiness and radio-on is never automatic. |
| Suspend, resume, remove and shutdown | Driver-core and PM callbacks plus the provider/client contract | These transitions are kernel resource lifetime, not distribution policy. |
| Diagnostics and recovery | Structured kernel diagnostics and, if justified, devlink health | A bounded owner recovery can be observable without an ioctl command multiplexer. |
| Chip selection | DT compatible data and provider-owned discovery | The retained property/query-derived scalar is conditional evidence, not an ABI that userspace must reproduce. |

The hypothesis must be reopened only if attributable hardware evidence proves a
necessary operation has no suitable kernel owner or standard subsystem
representation. That review may design a narrow standard interface; it must not
adopt the vendor character device merely to execute the retained loader.

## Probe and activation

Provider probe is passive. It resolves the platform dependencies, validates
the reserved-memory identity and constructs one opaque nonzero generation. It
does not power CONSYS, publish a successful empty lease or start firmware.
Missing dependencies defer; malformed or unsupported immutable resources fail
with a typed error before a client handle is published.

WLAN probe obtains the provider handle, requests the firmware through the
kernel firmware loader and builds a complete immutable image plan without a
hardware effect. A rejected activation that is proven to precede every effect
remains `BOUND` and may release only passive resources. Once any activation
effect is attempted, a failed or partial activation enters `FAULT_HELD` and
retains its lifetime regardless of the returned errno. Hardware download may
begin only after `activate` confirms the same plan/provider generation, powered
downloader state, reset and client exclusion, HIF access, remap identity and
reserved-range ownership. Ordinary
sections then complete in table order. EMI becomes writable once, every EMI
copy completes with visibility evidence, and a separate final seal succeeds.
Only then may START be submitted. Firmware readiness enters `FIRMWARE_READY`
and is observed separately before cfg80211/wiphy and the normal net device are
registered. Explicit successful registration alone enters `READY`.
Registration failure after firmware effects enters `FAULT_HELD`; it cannot
release the live epoch as ordinary failed-probe cleanup. Registration does not
itself turn on the radio.

Probe success therefore means that this driver's required provider, firmware,
readiness and wireless-registration work succeeded. It never means that a
vendor module-init arithmetic aggregate was nonnegative. Each failure returns
from the operation that owns it.

## State and error contract

The complete transition table is machine checked in
[state-model.json](state-model.json). Its key distinctions are:

```text
UNBOUND -> BOUND -> OWNER_ACTIVE
  -> ORDINARY_SUBMITTED -> ORDINARY_DONE
  -> EMI_WRITABLE -> EMI_COPY_SUBMITTED -> EMI_COPIED -> EMI_SEALED
  -> START_SUBMITTED -> FIRMWARE_READY -> READY -> QUIESCING -> OFF
          failure/registration failure \-> FAULT_HELD -> QUIESCING
```

`ORDINARY_SUBMITTED` and `EMI_COPY_SUBMITTED` retain the source, destination,
sequence and ownership until positive completion. `START_SUBMITTED` retains all
firmware-consumable resources and is neither `FIRMWARE_READY` nor `READY`.
`FIRMWARE_READY` proves only the firmware observation; it does not prove
successful standard wireless registration. Counts and per-section
ledgers—not Booleans—prove ordinary and EMI completion. A seal is a typed
provider result, not an `emi_done` flag. Compilation reaches none of these
runtime states.

Dependency absence uses `-EPROBE_DEFER`; unsupported hardware/operation uses
`-ENODEV` or `-EOPNOTSUPP`; malformed extents and plans use
`-EINVAL`/`-ERANGE`; competing ownership uses `-EBUSY`; generation loss uses
`-ESTALE`; protocol mismatch uses `-EPROTO`; reported or uncertain transport
failure uses `-EIO`; and an expired absolute deadline uses `-ETIMEDOUT`.
Those names classify the error, not the resource state. An effect-free
preflight `-EOPNOTSUPP` can remain passive, while an unsupported result returned
after a secure operation was marked attempted is possibly effective and must
enter `FAULT_HELD`. The same effect-history and ownership-certainty rule applies
to every errno. The first primary error, any containment error and a raw secure
result are kept separately. They are never added, overwritten by a later log
result or changed to success by cleanup.

Before any effect, a rejected passive binding can be destroyed. After power,
remap, protection, transfer or copy is attempted, uncertainty poisons the epoch
and retains every possibly effective resource. A reported timeout does not
prove cancellation. There is no command replay, credit refund, firmware/START
retry, automatic common reset or automatic radio action.

## Remove, shutdown, suspend and recovery

Teardown is derived from held resources and positive quiescence, not by
reversing vendor initialization or assuming a missing gen3-exit caller. WLAN
first blocks new cfg80211/netdev work and coordinates the affected clients. It
then drains queues, IRQ/NAPI, HIF and any admitted DMA channel, asks firmware to
quiesce and proves that firmware can no longer fetch the WLAN EMI range. Only
after those witnesses may the provider restore its owned remap/protection
fields, release reservation/channel claims and request coherent power-off.

If any activation, registration, drain or firmware-stop witness fails after an
effect, `FAULT_HELD` retains mappings, buffers, reservation, generation and
required power claims. It also pins consumer callbacks, HIF/transaction objects,
module/code lifetime and both provider and client references through failed
probe, remove or unbind. Those callable objects cannot disappear while the
owner may still invoke them or an operation may still complete. Only
owner-controlled quiescence followed by coherent `OFF` permits release. Neither
`pm_runtime_put()`, timeout, consumer detach nor memory free is a quiescence
witness. Shutdown reports the retained failure rather than concealing cleanup.

Suspend uses the same boundary. Resume starts a new generation and repeats
passive validation and activation; it does not replay the old epoch or restore
radio activity automatically. Only the common provider may attempt one
explicit bounded recovery after all affected clients are coordinated. A future
devlink health recover operation is optional and cannot exist until that
quiesce/OFF sequence is demonstrably implemented.

## Proposal disposition

All twelve Wi-Fi-series proposals remain non-runtime inputs:

| Patch | Component | Disposition |
| --- | --- | --- |
| 0001 | Private HIF/INIT transport | Keep bounded helpers; replace raw MMIO allocation/free with an opaque owner epoch. |
| 0002 | MTKE parser | Retain compile-only parsing under owned firmware lifetime and typed errors. |
| 0003 | Image plan | Change to an immutable, private, generation-bound snapshot. |
| 0004 | START/readiness | Bind to complete-image and owner evidence; retain separate submission/readiness. |
| 0005 | Image binding | Move effect-bearing lifetime and close authority into the provider. |
| 0006 | Reserved-memory descriptor | Resolve only through the provider; export no base or mapping to WLAN. |
| 0007 | Dynamic declaration | Keep descriptive only; declaration syntax is not an allocated resource. |
| 0008 | EMI ABI | Keep encoding/decoding behind provider-selected policy and raw status retention. |
| 0009 | Remap fields | Retain pure masked helpers as provider-private operations with lock/readback. |
| 0010 | Resource layout | Construct only from the real boot resource and provider generation. |
| 0011 | EMI service gate | Integrate one attempt into provider state and retain containment results. |
| 0012 | Ordinary transfer | Derive requests from the bound plan and record each submission/completion. |

The separate `0001-lib` patch is a compile precursor whose `lib/Kconfig.debug`
placement is superseded by the private WLAN series, not an upstream location.
The `0001-clk` unwind fix and unselected `0001-pmdomain` deferred-activation
mechanism are independent prerequisites: neither owns CONSYS, selects a domain,
provides a WLAN caller or proves runtime readiness. Exact per-file status and
required API changes are in [proposal-map.json](proposal-map.json). No proposal
is promoted to runtime-ready or submission-ready by this design.

## Smallest next implementation slice

The bounded next slice is an effect-free passive CONSYS provider descriptor and
WLAN client binding. It validates the boot resource and no-map/subrange rules,
publishes one opaque generation-bound handle, and permits an immutable plan to
bind. Its fault-injection tests must prove zero power, reset, remap, protection,
firmware, radio and DMA calls. Missing provider state must defer; malformed,
overlapping or insufficient resources must refuse; stale generations and
competing images must refuse; removal of a never-active binding must release
only passive references. Kernel compilation and DT-binding checks are required
if code or a binding is added, but they still do not establish runtime support.

This slice deliberately stops before owner activation. A later effect-bearing
slice requires independent shared-ownership review and one reversible effect at
a time. Ordered project priority remains owned by the roadmap.

## Scope, rights and handoff

[inputs.json](inputs.json) pins the parent and all forty-two frozen repository
inputs, including the twelve Wi-Fi-series patches and three separate `0001`
companions. No additional manifest-Linux file or page was needed; the six-item
budget remains unused. [FREEZE.md](FREEZE.md) records independent canonical
digests and [verify.py](verify.py) exercises the required policy refusals.

Only independently authored design text and structured metadata are retained.
No vendor code, raw binary, disassembly, firmware, calibration, private path,
credential or device identifier is included. Existing proposal patches remain
evidence and compile experiments; their synthetic non-certifying authorship is
not made submission-ready. No redistribution or hardware authority follows.

Observed start: `2026-09-06T20:02:55Z`. Corrected review-ready:
`2026-09-06T20:23:28Z`. Independently accepted:
`2026-09-06T20:25:29Z`.
Measured credits: unavailable.
