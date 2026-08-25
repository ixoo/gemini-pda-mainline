# Deferred provider dependency design

## Production order

```text
platform_driver probe
  -> resolve and require bound platform-state source
  -> resolve mediatek,provider
  -> require exact dlg,da9214-legacy I2C endpoint present and bound
  -> capture(platform, provider-ready)
       -> platform snapshot once
       -> checkpoint(before-provider)
       -> provider snapshot once
       -> checkpoint(after-provider)
  -> terminal three-line receipt
```

An unavailable provider returns `-EPROBE_DEFER` before `capture()`. The
provider device reference is held until capture and logging complete, then
released on every exit. The helper neither calls the registry nor touches the
I2C adapter.

## Injected proof

`mt6797_a72_pp_capture()` receives the already validated provider device
reference. A null provider represents the not-ready dependency and must return
`-EPROBE_DEFER` after clearing the destination but before invoking any injected
operation. A non-null provider retains the existing success and failure paths.

The focused suite therefore grows from six to seven cases. The new case proves
zero platform calls, zero retained-checkpoint events, zero provider calls, and
an all-zero destination when provider readiness is absent. The original
success case is the ready case and retains one platform call, two checkpoints,
one provider call, and the exact event order.

## Exclusions

The repair adds no I2C transfer, register read or write, retry loop, delay,
device link with PM semantics, provider lifecycle call, protected-clock or
BigiDVFS operation, secure call, publication, owner mutation, CPU request,
storage access, reset, reboot, or power action.
