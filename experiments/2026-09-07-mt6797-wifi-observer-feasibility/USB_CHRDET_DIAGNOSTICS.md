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
unchanged. Full compilation and linked inspection now pass at
`520fddb9ef17eccb73ebf836e120a0e582ab7a21`; the selected candidate is described
below. The inherited native compiler warning suppression and 69 section
mismatches remain; this is not warning-clean or hardware-support evidence.

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
role request, radio operation, direct retained-slot write or userspace control. Two
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

## Selected session

The [candidate receipt](results/usb-chrdet-diagnostics-candidate.json) binds the
complete kernel package and independently verified container. All eleven remote
and fetched package files match. Configuration and the 130833-byte DT are
unchanged. The 723-member filesystem differs only in session metadata;
independent reassembly, seventeen container mutations and six input refusals
pass. Runtime and startup bytes retain their earlier ARM64 validation.

Linked inspection confirms eight charger-marker calls and the one original
indirect charger callback. Original operational call inventories remain. The
16-byte getter contains address calculation, one ordinary mask load and return.
The shutdown report still tests and sets bit 15 before reading that mask or
printing, and returns directly when already consumed. The first private getter
check expected one fewer address-calculation instruction; inspecting the emitted
ADD corrected that expectation without changing the kernel. Call inventories
are not a claim of complete binary control-flow equivalence.

The [session receipt](results/usb-chrdet-diagnostics-session.json) selects cycle
`87c24209-c8af-40e9-b443-7a0397fa185f` from the preserved changed-boot Gemian
identity. The primary coordinator holds sole custody. The installer is unchanged
after reversing five identity/destination substitutions; Bash and ShellCheck
pass. It retains the live-GPT, block-identity, inactive/non-root, size, power and
full-readback gates, followed by clean shutdown. The prior console is already
preserved. Physical selection remains an owner action after collectors are armed.

The return collector changes only the preceding Gemian UUID. Host attribution,
receiver, route helper and transport budgets are unchanged. The v2 decoder
passes 22 attribution, malformed-record and mask cases. No capture clear,
radio action or host network change is added. Physical runtime was pending at arming.

The [deployment receipt](results/usb-chrdet-diagnostics-deployment.json) now
confirms installation from the expected Gemian boot. Live GPT resolved inactive
boot2, all guards passed, and both the remote full checksum and independent
readback stream matched the candidate. Clean shutdown followed evidence
preservation. Both collectors were observed armed before the owner handoff;
physical start has not yet been reported. Hosted checks for the published
candidate passed. This installation is not a USB runtime result.

## First collection window

Both collectors completed their 600-second windows. The
[window receipt](results/usb-chrdet-diagnostics-window-1.json) preserves three
host USB inventory changes: a `0e8d:2000` parent reporting `MT65xx Preloader`
appeared and disappeared, followed by a `0e8d:20ff` parent reporting `Unknown`.
None had an Ethernet child; the final sample matched the last change. No
expected gadget, receiver, snapshot or acknowledgement was observed. The
return collector obtained no authenticated changed-boot Gemian or console.

These USB identifiers do not prove boot2 selection, candidate execution or the
current OS. The latter pair has appeared in earlier
[charging/intermediate-stage observations](ARMED_EXPORT.md#fresh-collection-using-the-verified-installation),
without uniquely establishing their cause. No start report or diagnostic
summary arrived in this window, so the new charger-branch hypothesis remains
untested by attributable runtime evidence.

The image remains installed and verified. Both collectors are stopped; await
the owner's physical-start and current-screen report before another device
action. Preserve this USB sequence and the original installation. No unchanged
candidate repeat, recovery action, role override or capture clear is selected.


## Retained physical result

The owner returned on September 24, confirmed the PDA powered off with left
USB-C connected, and reported physical start after fresh collectors were armed.
The verified installation was reused without a reinstall or preboot device
re-verification. The [second-window receipt](results/usb-chrdet-diagnostics-window-2.json)
attributes candidate boot `d720e10f-30f9-499b-b8ca-87fd9f0590a2` and this cycle.
CPU preflight passed; startup reached USB setup and waited for a host request,
then recorded `stopped` and normal restart. The single retained summary reads
`paths=865d cable=00010000 chrdet=39`.

The charger helper entered its existing detection callback, returned, and
recorded a zero detection result. Initialization-not-ready, charging-suspended,
and the later host/device return bits were absent. These cumulative markers
cover all callers: they do not identify the actual callback pointer or correlate
a particular invocation with USB work. The independent USB mask records ready,
host and device paths, cable false and controller stop; controller start is
absent. Its last cable sample remains unknown charger type, false software VBUS,
not connected and normal cable mode. This is not a physical voltage measurement.

The owner start report arrived approximately 520 seconds after host arming.
No expected Ethernet gadget or receiver was observed before the 600-second
window expired; complete runtime coverage is not established. The initial return
collector also expired. After the owner's Gemian return report, one fresh
unchanged return collector authenticated changed Gemian boot
`05eb32a4-0958-4f90-aef1-842d37a03928` and preserved one 65524-byte console.
No new boot, capture clear or recovery action was performed. The retained
console has no checked fault tokens after the return marker. No snapshot or
acknowledgement was exported.

The diagnostic resolves the previously ambiguous refusal to the callback's
zero-result branch. Next inspect the selected charger-detection callback and
PMIC field/accessor ownership and error contract. Preserve the distinction
between a zero software result and physical cable or VBUS conditions; no role
override, constant VBUS value or unchanged-candidate repeat is selected.
