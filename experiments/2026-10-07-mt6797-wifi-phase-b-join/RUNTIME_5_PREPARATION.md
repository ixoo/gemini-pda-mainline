# Fourth Phase B candidate composed, not installed

Status: candidate 4 is composed and offline-validated on the laptop at source
`842a58d5`; it is not installed, not booted and untested. The device is on the
live Gemian boot `7339537d-9f66-4b20-8e9f-69ae4ec37290` with candidate 3
(boot2 `84f65eae…`) still installed. The laptop remains the sole custodian.

The committed receipt [results/candidate-4.json](results/candidate-4.json)
(SHA-256 `0d8bf089…`) pairs the [compile 9](COMPILE_9.md) package `bb1659e0…`
with the parent RAM root plus the reviewed `bin/join-connect` helper
(`b3851a4b…`, 665552 bytes): boot image `6bc99a30…` (11442176 bytes), full
padded boot2 `eeb2ce9b…`, initramfs `361e2fa9…` (4788477 bytes), kernel
config `153ea2d0…` and board DT `25ab60f4…` byte-identical to candidate 3.
Both receipt slots and the runtime-5 identity copy carry the receipt digest.

Next, under the standing authorization and in this order: the guarded
`install-passive.py prepare` for deployment 4 over predecessor `84f65eae…`,
the owner's physical boot2 selection, then the runtime-5 protocol with a fresh
root and a re-bound join script. The boot's decision-changing observation is
either a management exchange (join TX, RX and acknowledgement records, an
association status) or the 0143 refusal bitmask, with the helper's
`connect_request=…` line in the framed body saying whether the kernel
accepted the privacy-flagged connect request.
