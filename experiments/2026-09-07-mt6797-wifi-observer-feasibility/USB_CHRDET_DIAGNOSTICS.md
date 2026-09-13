# Observe the native charger-detection refusal

The [retained USB diagnostic](USB_ETHERNET_DIAGNOSTICS.md#retained-physical-result)
reached readiness and device-mode connection work, but recorded cable false
and no controller start. Its latest cable sample contained unknown charger
type and false software VBUS detection. The
[selected provider trace](USB_ETHERNET_DIAGNOSTICS.md#detection-provider-trace)
found four distinct false-return paths in `upmu_is_chr_det()`. That evidence
does not justify changing charger or role policy.

The [patch](patches/usb-chrdet-diagnostics/0001-usb-retain-native-charger-detection-rejection-branches.patch)
records eight cumulative bits as the selected battery helper executes its
existing branches. An ordinary getter returns that mask to the existing USB
shutdown report. The three changed files retain their GPL version 2 license
headers. This assistant-generated native experiment has no DCO certification
and is not an upstream submission or maintained driver interface.

The [source receipt](results/usb-chrdet-diagnostics.json) pins every parent and
changed file, exact patch replay and reversal, and strict Linux 7.1.3 Checkpatch
with sign-off checking disabled for this non-certifying archive. The first 49
native patches remain byte-identical. The only builder change admits the exact
50-patch count. Configuration and canonical upstream series/profiles are
unchanged. Full compilation, linked inspection, packaging and device admission
remain pending at source preparation.

## Observation and effect budget

The existing atomic report-consumed bit still limits output to one line from
the first `musb_shutdown()` entry, before its hardware operations. Its format
becomes `wifi-usb-v2 paths=hhhh cable=hhhhhhhh chrdet=hh`. The existing `paths`
and `cable` meanings remain in the [parent protocol](USB_ETHERNET_DIAGNOSTICS.md#observation-and-bounds).
The new `chrdet` bits mean:

| Bit | Existing decision or call boundary reached |
| --- | --- |
| 0 | Entered `upmu_is_chr_det()` |
| 1 | Battery initialization flag false; returning false |
| 2 | Charging suspension flag set; returning false |
| 3 | Immediately before the existing charger-detection callback |
| 4 | That callback returned |
| 5 | Its result was zero; returning false |
| 6 | Later role check reported host; returning false |
| 7 | Later role check reported device; returning true |

The mask starts at zero. Each event atomically sets one bit; it allocates no
memory, starts no work and creates no per-callback log. The getter performs one
ordinary memory read. The source adds no hardware accessor, charging write,
role request, radio operation, retained-slot write or userspace control. Two
single-statement conditionals gain braces for their markers; every original
decision, return and operational statement is preserved by exact reversal.
The new mask uses the same recovery diagnostic plus Ethernet-without-Android
gate as the existing report.

Interpretation requires the pinned configuration: smart battery and HAFG20
enabled; POWER_EXT, FPGA, external-power detection and dual-input charging
disabled. The header's zero fallback for other battery implementations is not
runtime evidence. The mask covers all callers of this helper, including native
battery work, and is independent of the USB path mask and last cable sample.
It supplies neither order, counts nor a joined per-call history. Both false and
true outcomes can accumulate. A call may still be in flight at report time.
False software VBUS remains distinct from a physical voltage measurement.

## Next physical session

Hypothesis: one or more existing battery initialization, charging suspension,
charger-detection or host-role checks explains the USB cable refusal. The
unique new observation is the retained rejection-branch mask. Keep the parent
CPU0–7 preflight, immutable snapshot, USB transport, 60-second exchange and
normal return path unchanged. Require a new exact build/container/session,
guarded boot2 deployment and full readback, clean shutdown and both collectors
armed before owner physical selection.

Attribute exactly one well-formed v2 summary after the new boot and cycle's
return marker and before normal restart. Preserve one console only after
authenticated changed-boot Gemian. Missing, malformed, duplicate, early or
late summaries are inconclusive; the first shutdown can be an error/remove
path and consume the report before normal return.

- Initialization or suspension refusal: inspect the responsible existing
  startup or policy owner before changing it.
- Zero detection result: inspect the PMIC field and selected callback's
  existing ownership/error contract; do not substitute a constant VBUS value.
- Host refusal: trace the software role selection and its inputs; do not force
  a device role from this bit alone.
- Multiple outcomes: preserve their independent-call ambiguity and select a
  measurement that distinguishes the remaining alternatives.
- Cable true/controller start or USB enumeration: follow the parent protocol's
  controller/transport branch. Only a verified snapshot, acknowledgement,
  preserved return marker and changed-boot Gemian complete export.

No capture clear or radio cycle is added. A timeout does not select an unchanged
retry. Source preparation alone does not authorize physical selection.
