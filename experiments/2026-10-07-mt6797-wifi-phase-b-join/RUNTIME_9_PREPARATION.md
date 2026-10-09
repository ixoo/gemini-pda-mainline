# Eighth Phase B deployment, runtime 9 awaiting the owner's boot

Status: candidate 8 is installed and fully read back; the device was cleanly
powered off and is unbooted, awaiting the owner's physical boot2 start. The
laptop, as sole custodian, will execute the reviewed runtime-9 capture and
session exactly once after that; no runtime evidence exists yet. Nothing in
the source, the build or the runtime bindings changes until it arrives.

The [guarded deployment receipt](results/deployment-8.json) pins candidate 8:
receipt `6d5183ec…`, full padded boot2 `1eed3948…`, written over predecessor
candidate 7 `820657ed…`, synced and flushed, with the full 16 MiB readback
matching. The installer was prepared at source `b625a864` (generated
installer SHA-256 `5d2df974…`) and executed once under the standing boot2
authorization with its final local validator passing; the live guard passed
on Gemian boot `51e41731…`, target `179:30`, root `179:29`, stable power;
no fresh predecessor backup, temporary readback removed. The clean shutdown
was confirmed with the device unreachable; nothing was rebooted.

Runtime-9 preparation on the laptop at `b625a864`: a fresh evidence root with
`wifi-phase-b/session-8` holding the true deployment-8 summary and `capture-8`
absent; both offline preflights passed with the bound runtime-9 script and no
RF.

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
runtime-9 identity copy carry the receipt digest.

The runtime-9 protocol is the one in [PHASE_C](PHASE_C.md): one passive scan,
one privacy-flagged WPA2-PSK CCMP connect carrying the RSN element, no key,
no payload transmission, no EAPOL reply; the driver deauthenticates within
250 ms of activation or at the first observed EAPOL frame, then the ordered
teardown. Hypothesis: the AP accepts the association once the request carries the RSN
element, and its first clear EAPOL-Key frame is observed with valid framing.
The boot's decision-changing observation is one or two `eapol observed`
records between the status-0 response and the deauthentication's TX done,
with a healthy cleanup. Branches: accepted with one or two observations;
accepted with zero observations (shape unresolved); denied with any non-zero
status, 45 included; or a refusal with its branch. Wi-Fi remains incomplete
in every branch.
