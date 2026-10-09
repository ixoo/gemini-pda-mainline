# Eighth Phase B deployment, runtime 9: candidate 8 composed, not installed

Status: candidate 8 is composed and offline-validated on the laptop; it is
not installed, no device action has happened, and the device remains in
changed-boot Gemian. Installation over the installed candidate 7 and the
owner's physical boot2 start follow this record.

The committed receipt [results/candidate-8.json](results/candidate-8.json)
(SHA-256 `6d5183ec…`) pairs the [compile 13](COMPILE_13.md) package
`07caf6b5…` (input `8efe639e`) with the Phase A3 parent and the Phase C1
helper: boot image `2a52212f…` (11444224 bytes), full padded boot2
`1eed3948…` (16 MiB), kernel image `4bed248e…` (6621361 bytes), initramfs
`dc8a4479…` (4788636 bytes, 62 members: every parent byte, the same Phase B
release gate and the pinned `bin/join-connect` `bc499f28…`, 665552 bytes).
Kernel config `153ea2d0…` and board DT `25ab60f4…` are byte-identical to
candidates 4 to 7. Against candidate 7, the kernel image changed by proposals
0140 and 0148 and the initramfs by the helper alone. The laptop's offline
gates passed (Android v0 header, LK, 16 MiB pad, PSCI/SMC and
`clk_ignore_unused`, all 801 package checksums). Both receipt slots and the
runtime-9 identity copy carry the receipt digest; the bound runtime-9 join
script is prepared privately and the runtime-9 evidence root exists empty.

The runtime-9 protocol is the one in [PHASE_C](PHASE_C.md): one passive scan,
one privacy-flagged WPA2-PSK CCMP connect carrying the RSN element, no key,
no payload transmission, no EAPOL reply; the driver deauthenticates within
250 ms of activation or at the first observed EAPOL frame, then the ordered
teardown. Decision branches: accepted association with one or two `eapol
observed` records and a healthy cleanup; accepted with zero observations;
denied with any non-zero status, 45 included; or a refusal with its branch.
