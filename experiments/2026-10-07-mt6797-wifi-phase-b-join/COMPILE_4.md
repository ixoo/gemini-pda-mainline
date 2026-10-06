# Phase B preparation compile 4

Status: validated compile-only; no candidate or device test.

- Repository input: `d783df519df594fb3388235ce5df279e97473bd0`, clean.
- Profile: `mt6797-a53-wifi-phase-b-compile`, patches `0122` through `0134`
  after the Phase A baseline; `CONFIG_MT6797_STATION_JOIN=y` is resolved.
- Builder: Buildbox-1, 32 jobs; one submission, completed
  `2026-10-06T00:46:06Z`.
- Job: `d783df519df594fb3388235ce5df279e97473bd0-mt6797-a53-wifi-phase-b-compile-m0`.
- Validated package inventory SHA-256:
  `3c5b8f7deba33c8a197adef69f478b365c575a543ecaf517f29cb0364c3ed1c3`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- Managed job log SHA-256:
  `f4ba35385f21420b1501d871b71474ddb6a71166a3468d8c4183e1d34883d19d`.

This fixes [compile 3](COMPILE_3.md). Patch 0133 now reads the normal
owner's idle state through `mt6797_hif_normal_idle()` in `hif.c`. That
accessor takes the HIF mutex with a trylock and reports "not idle" when the
mutex is busy, so callers fail closed. Both former direct-access sites use
it. Patch 0134 applies unchanged.

Before submission, the full series applied with the build's method
reproduced the locally compiled tree, a local `W=1` compile of the driver
directory had no warning, and `validate-manifest-series` and
`check-repository` both exited 0. The managed job JSON reports `validated`.
Package checksums passed after fetch, and the resolved configuration has
`CONFIG_MT6797_STATION_JOIN=y`. The log has no MT6797 Wi-Fi driver warning;
its two inherited warnings match [compile 1](COMPILE_1.md).

This verifies kernel integration of the scan-to-join lifetime and the guarded
directed-management filter preparation. It proves no firmware command
acceptance, callback behaviour, authentication, association or data path.
No image was composed and the device was not accessed.
