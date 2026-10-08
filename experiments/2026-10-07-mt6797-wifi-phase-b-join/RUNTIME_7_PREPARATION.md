# Sixth Phase B candidate composed, not installed

Status: candidate 6 is composed and offline-validated on the laptop at source
`1d54360a`; it is not installed, not booted and untested. The device is on the
live Gemian boot `e128be1a-a40b-4d63-a7f4-892a1293c2bf` with candidate 5
(boot2 `e6fe0e8d…`) still installed. The laptop remains the sole custodian.

The committed receipt [results/candidate-6.json](results/candidate-6.json)
(SHA-256 `e4fbd0e2…`) pairs the [compile 11](COMPILE_11.md) package
`86b0a208…` with the candidate-4 RAM root and helper: boot image `59d1ee6f…`
(11442176 bytes), full padded boot2 `e6b7dd4e…`; initramfs, kernel config and
board DT byte-identical to candidates 4 and 5, so only the kernel image
changed, and that only by the diagnostics of proposal 0146. Both receipt
slots and the runtime-7 identity copy carry the receipt digest.

Next, under the standing authorization and in this order: the guarded
`install-passive.py prepare` for deployment 6 over predecessor `e6fe0e8d…`,
the two offline preflights, the owner's physical boot2 selection, then the
runtime-7 protocol with a fresh root under the unchanged radio scope (one
passive scan, one open-system authenticate-and-associate attempt, no keys, no
data). The boot's decision-changing observation is the join footer's branch
tag with its accompanying refusal line, which locates the runtime-6 protocol
error.
