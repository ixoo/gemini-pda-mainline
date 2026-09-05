# Coordinator compile integration

The original proposal `7af83151` and style revision `a3f5be24` are retained.
The canonical payload is the styled complete patch, SHA-256
`2c2b243b862044dff6253602d1b3d283ceb4e836dfdb8350c392319250d3e22a`.
The coordinator independently reproduced it and reran all eight fixtures
against both header variants under strict C11, ASan and UBSan: all passed.
Source checkpatch findings are zero; absent DCO and the MAINTAINERS reminder
remain disclosed and this experiment is not submission-ready.

The new `mt6797-hif-compile` profile uses the extended provider series. This
intentionally changes source provenance for `mt6797-provider-compile`, with the
new symbol default off there. The prior provider source state becomes historical
when the managed builder refreshes it; original packages and receipts remain
valid for their exact old inputs. See [provider impact](provider-impact.json)
for reconstruction. Default, active boot candidates and reset-topic source are
unaffected. No duplicate Linux source tree is requested.

Actual kernel compilation and emitted-object acceptance passed in the
[Buildbox result](BUILD_RESULT.md).
This profile is compile-only and is not selected for device deployment.
