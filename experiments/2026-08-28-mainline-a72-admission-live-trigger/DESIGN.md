# Serviceability-first admission design

## Exact endpoint

The mode is selected only by
`CONFIG_MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER=y`. The base and historical
profiles remain unchanged when it is disabled.

- Platform device: the existing DT-bound A72 admission controller.
- Attribute group: `gemini_admission`.
- Status: read-only `status` (`0444`).
- Action: write-only `trigger` (`0200`).
- Exact accepted bytes: `run-a72-admission-20260828-a\n`.

No attribute is exposed by the base Gemini DT because that DT has no admission
controller node. The candidate-only derivative supplies the node.

## Boot and trigger order

1. `late_initcall` registers the existing platform driver.
2. Candidate probe allocates controller and trigger state, sets driver data,
   adds the sysfs group, and reports `state=armed`.
3. Probe performs no phandle lookup, device link, source registration,
   publication, retained write, or CPU request.
4. The initramfs brings up the established USB/netcat service.
5. The host stores an exact pre-trigger frame before any action.
6. Root temporarily remounts virtual sysfs writable and writes the exact token.
7. The trigger gate atomically consumes its sole execution before resolving
   binder, platform-state, clock, and BigiDVFS suppliers.
8. Resolution success initializes the same physical-source context and calls
   the existing admission core synchronously from that task.
9. A returning result is stored before trigger state becomes `terminal`.
10. Sysfs is restored read-only before post-trigger capture.

Invalid input returns `-EINVAL` without consumption. A second exact token
returns `-EALREADY` and cannot resolve a supplier or call the core. The first
valid token is acknowledged once even when the underlying operation returns an
error; the exact error is read from status. This makes the action acceptance
and operation outcome unambiguous.

## Exact status wire

One bounded line:

```text
GEMINI_A72_ADMISSION_LIVE_V1 state=<armed|running|terminal> trigger_consumed=<0|1> trigger_executions=<0|1> operation_ret=<int> core_consumed=<0|1> cpu_requests=<0|1> cpu9_requests=0 cpu_off_requests=0 retries=0
```

Before the token, the required state is `armed`, both consumed fields and both
counters are zero, and `operation_ret=-115` (`-EINPROGRESS`).

## Runtime decision map

| Observation | Classification | Next action |
| --- | --- | --- |
| Changed-ID Gemian before exact USB/armed frame | pre-trigger nonserviceable | audit candidate DT/supplier enablement; do not trigger or repeat |
| Exact armed frame, then transport loss/reset | trigger-boundary interruption | recover changed boot ID and corroborating records; localize within supplier resolution/admission |
| Terminal with trigger consumed, core not consumed, zero requests | pre-core/prerequisite refusal | use `operation_ret` and bounded dmesg tag to select one repair |
| Terminal with core consumed, zero requests | source/derive/publish terminal | use trace/status result; no retry |
| Terminal with one request and CPU8 offline | CPU8 request returned failure | use transition ledger/status; repair the named terminal stage |
| Terminal with one request and CPU8 online, CPU9 offline | CPU8 admission success | retain live proof and move to stability/CPU9 planning |

Screen color and reboot timing are contextual observations only. Retained
ramoops bytes may corroborate a result but cannot negate execution.

## Effect ceiling

- Trigger executions: at most 1.
- Admission-core consumptions: at most 1.
- CPU8 requests: at most 1.
- CPU9 requests: 0.
- CPU_OFF requests: 0.
- Retry paths: 0.
- Automatic probe action: 0.
- Device storage writes by the runtime probe: 0.
- Native VM kernel builds: 0.
