# Phase B preparation compile 3

Status: failed compile; no package, not retried.

- Repository input: `b476d530d756146e0e425274d2be9e02cb02f0c6`, clean.
- Profile: `mt6797-a53-wifi-phase-b-compile`, patches `0122` through `0134`
  after the Phase A baseline; the fragment sets
  `CONFIG_MT6797_STATION_JOIN=y`.
- Builder: Buildbox-1, 32 jobs; one submission.
- Job: `b476d530d756146e0e425274d2be9e02cb02f0c6-mt6797-a53-wifi-phase-b-compile-m0`.
- Result: `build-kernel` exit 2. No job JSON and no package were published.
- Managed job log SHA-256:
  `65e5709b346b691fad0fb3c9720e09bc5112d315498d72ebd5e12c65ea84b0b7`.

Compilation of `drivers/net/wireless/mediatek/mt6797/mac.o` stopped with 16
errors of one kind, `invalid use of undefined type 'struct mt6797_hif'`, at
`mac.c` lines 250–260 and 534–538. Patch 0133 read fields of the HIF context,
which is private to `hif.c`. There was no other error. The two inherited
warnings match [compile 1](COMPILE_1.md).

[Compile 4](COMPILE_4.md) records the fix.
