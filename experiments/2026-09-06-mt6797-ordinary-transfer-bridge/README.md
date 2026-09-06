# MT6797 ordinary-transfer bridge

This is an offline, compile-only experiment for a dormant lower-level bridge
around the existing `mt6797_hif_download_section()` API. It copies a bounded
array of ordinary request descriptors, validates every descriptor and the
whole span graph before the first HIF call, then executes each request once in
original order under one absolute monotonic deadline.

The caller retains the real powered mapping, reset/IRQ and host exclusion,
whole-image generation and immutable buffers throughout. The bridge does not
inspect or weaken the private image binding, admit EMI, issue START, acquire
firmware, own hardware, or provide a production caller. A successful result
means only that the existing HIF function returned success for each supplied
ordinary request; it does not prove complete-image execution, firmware
readiness, real ownership or usable Wi-Fi.

`src/ordinary-transfer-test.c` supplies an inert HIF symbol and exhaustive
host refusal/progress fixtures. `scripts/verify.py` regenerates the exact
patch, runs normal and optimized builds, ASan/UBSan, and source-boundary
checks. No device, network, VM or private capture is accessed.

The patch is an internal synthetic-author experiment with no DCO and is not
submission-ready. The integrator alone may copy it into the provider series.
