# Phase C compile 19: packet sockets restored for the supplicant

Status: validated compile-only; no candidate composed, no device test.

- Repository input: `9aa567d732777f11ed91864579db159895f730d7`, clean, the revision accepted in review.
- Profile: `mt6797-a53-wifi-phase-b-compile`, 656 patches, the compile-18
  selection unchanged (patchset `1750462f…`, source `be41c068…`); the only
  input change is `CONFIG_PACKET=y` in the profile's last fragment.
- Builder: Buildbox-1, 32 jobs, one heavy build through the managed backend
  after capacity, lock and free-space checks; generated `2026-10-10T01:12:05Z`.
- Job: `9aa567d732777f11ed91864579db159895f730d7-mt6797-a53-wifi-phase-b-compile-m0`.
- Validated package inventory SHA-256: `46f3682fd941047e169b0855025a17e86130c5c8242e6ba54b642ee67093368f`.
- Release: `7.1.3-gemini-a53-wifi-phase-b-compile`.
- `kernel.config` SHA-256: `975f8703e4061d8676dff6fc7835312f949f9ce3317b3fd900a3219cce0c312d`,
  exactly the configuration reproduced offline before the build: the
  compile-18 configuration (`153ea2d0…`) with line 946 `CONFIG_PACKET=y` and
  the new line 947 `# CONFIG_PACKET_DIAG is not set`, nothing else.
- `Image.gz` SHA-256: `ce526e77f3f447381859f1e7432dfadba053e656ce80462ffc4f44e354abd261`
  (decompressed 15960072 bytes, 2048 more than compile 18).

The board DT is unchanged (123 DTBs, checksums passed at validation).
Warnings against the documented baseline: the unused-function warning in
`kernel/cpu.c` only; the trailing-whitespace note of v7.1.3 patch 0261 did
not appear because the managed job reused the already prepared source tree
(no patch application in this job). Zero MT6797 driver warnings.

## Candidate 14 composition

The owner composes candidate 14 privately with the reviewed composer at the
pushed head: this package, the same private parent, release gate, Phase C1
helper `bc499f28…` and supplicant `0487b710…` (63 RAM-root members, as
candidate 13). `build-candidate.py` now permits exactly the packet-socket
delta against the Phase A parent configuration (release name, station join,
`CONFIG_PACKET=y` with `PACKET_DIAG` left off) and refuses any other
configuration change; the board DT, PSCI method and clock flag checks are
unchanged. Expected: board DT `25ab60f4…`, initramfs `449832a3…` unchanged
from candidate 13; new kernel image, boot image and padded partition. The
candidate-14 receipt then binds deployment 14 (over the installed candidate
13, full padded boot2 `ec412ce9…`) and runtime 15 with fresh `capture-15`
and `session-15`, the first possible handshake measurement.
