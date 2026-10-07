# Fourth Phase B deployment, physical boot pending

Status: candidate 4 is installed and fully read back; the device is cleanly
powered off; no mainline boot, host RF transmission or join result has been
observed for it. The owner's physical boot2 selection has not yet been
requested. The laptop remains the sole custodian.

The [guarded deployment receipt](results/deployment-4.json) pins candidate 4:
receipt `0d8bf089…`, full padded boot2 `eeb2ce9b…`, written over predecessor
candidate 3 `84f65eae…`, synced and flushed, with the independent whole-partition
digest and byte comparison matching. The installer was prepared at source
`526e34cd` (generated installer SHA-256 `7a8d262c…`) and executed once under
the standing boot2 authorization; the live guard passed on Gemian boot
`7339537d-9f66-4b20-8e9f-69ae4ec37290`, target `179:30`, root `179:29`, stable
power; no fresh predecessor backup. Native Gemian power-off completed with SSH
status 0 and the device was confirmed unreachable; nothing was rebooted.

Footnote on the installer exit status: the installer wrapper returned 2 only
because its final local receipt-validator step was invoked without
`GEMINI_PRIVATE_REPO` in the environment, after the device write, readback
verification, evidence flush and shutdown had already completed. The receipt
validator alone was then rerun with the environment set and passed with no
device action, sealing the final checksum; there was no duplicate write and no
second shutdown.

Offline preflight for runtime 5 found a host-side refusal before any trigger:
`passive-session.py` still required the parent's 61 RAM-root members, while
candidate 4 carries 62. That check now requires 62 and verifies the added
`bin/join-connect` member explicitly (size, digest, mode 0755, root ownership,
one link), with the release, firmware, private-record, receipt, kernel, config
and DT guards unchanged; [tests/session-ram-root-test.py](tests/session-ram-root-test.py)
covers the admitted shape and the refusals. This is a host-only fix; the
installed candidate is unchanged.

The committed receipt [results/candidate-4.json](results/candidate-4.json)
(SHA-256 `0d8bf089…`) pairs the [compile 9](COMPILE_9.md) package `bb1659e0…`
with the parent RAM root plus the reviewed `bin/join-connect` helper
(`b3851a4b…`, 665552 bytes): boot image `6bc99a30…` (11442176 bytes), full
padded boot2 `eeb2ce9b…`, initramfs `361e2fa9…` (4788477 bytes), kernel
config `153ea2d0…` and board DT `25ab60f4…` byte-identical to candidate 3.
Both receipt slots and the runtime-5 identity copy carry the receipt digest.

Next: the laptop repeats only the offline preflight at this revision, then the
owner's physical boot2 selection, then the runtime-5 protocol with the fresh
root and the re-bound join script already prepared. The boot's decision-changing observation is
either a management exchange (join TX, RX and acknowledgement records, an
association status) or the 0143 refusal bitmask, with the helper's
`connect_request=…` line in the framed body saying whether the kernel
accepted the privacy-flagged connect request.
