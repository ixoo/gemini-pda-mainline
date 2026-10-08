# Sixth Phase B deployment, physical boot pending

Status: candidate 6 is installed and fully read back; the device is cleanly
powered off; no mainline boot, host RF transmission or join result has been
observed for it. The laptop has handed the physical boot2 selection to the
owner. The laptop remains the sole custodian.

The [guarded deployment receipt](results/deployment-6.json) pins candidate 6:
receipt `e4fbd0e2…`, full padded boot2 `e6b7dd4e…`, written over predecessor
candidate 5 `e6fe0e8d…`, synced and flushed, with the independent
whole-partition digest and byte comparison matching. The installer was
prepared at source `f408f15e` (generated installer SHA-256 `df3dc9de…`) and
executed once under the standing boot2 authorization with the private
repository variable supplied through its final local receipt validation
(exit 0); the live guard passed on Gemian boot
`e128be1a-a40b-4d63-a7f4-892a1293c2bf`, target `179:30`, root `179:29`, stable
power; no fresh predecessor backup. Native Gemian power-off completed with SSH
status 0 and the device was confirmed unreachable; nothing was rebooted.

Runtime-7 preparation on the laptop at `f408f15e`: a fresh evidence root with
`wifi-phase-b/session-6` holding the true deployment-6 summary and `capture-6`
absent; both offline preflights passed with no RF; the reviewed join script is
unchanged.

The committed receipt [results/candidate-6.json](results/candidate-6.json)
(SHA-256 `e4fbd0e2…`) pairs the [compile 11](COMPILE_11.md) package
`86b0a208…` with the candidate-4 RAM root and helper: boot image `59d1ee6f…`
(11442176 bytes), full padded boot2 `e6b7dd4e…`; initramfs, kernel config and
board DT byte-identical to candidates 4 and 5, so only the kernel image
changed, and that only by the diagnostics of proposal 0146. Both receipt
slots and the runtime-7 identity copy carry the receipt digest.

Next: the owner's physical boot2 selection, then exactly one capture and one
session under the unchanged radio scope (one passive scan, one open-system
authenticate-and-associate attempt, no keys, no data); the candidate-5 runtime
is not repeated. The hypothesis is that the 0146 diagnostics identify the
runtime-6 protocol error's branch. The decision-changing observation is the
join footer's branch tag with its accompanying refusal line: a ledger or
credit state versus an unexpected control event or frame is then diagnosed
offline, and a healthy cleanup means the protected association, key exchange
and data path proceed under their own reviewed protocol.
