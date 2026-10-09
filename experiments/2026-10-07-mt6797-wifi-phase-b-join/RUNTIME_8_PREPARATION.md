# Seventh Phase B candidate composed, not installed

Status: candidate 7 is composed and offline-validated on the laptop at source
`757ff487`; it is not installed, not booted and untested. The device is on the
live Gemian boot `8599964c-c0d6-4a63-9081-5747400b45c9` with candidate 6
(boot2 `e6b7dd4e…`) still installed. The laptop remains the sole custodian.

The committed receipt [results/candidate-7.json](results/candidate-7.json)
(SHA-256 `e3134657…`) pairs the [compile 12](COMPILE_12.md) package
`784aef75…` with the candidate-4 RAM root and helper: boot image `1fb75cff…`
(11442176 bytes), full padded boot2 `820657ed…`; initramfs, kernel config and
board DT byte-identical to candidates 4 to 6, so only the kernel image
changed, and that only by the reviewed proposal 0147. Both receipt slots and
the runtime-8 identity copy carry the receipt digest.

Next, under the standing authorization and in this order: the guarded
`install-passive.py prepare` for deployment 7 over predecessor `e6b7dd4e…`,
the two offline preflights, the owner's physical boot2 selection, then the
runtime-8 protocol with a fresh root under the unchanged radio scope (one
passive scan, one open-system authenticate-and-associate attempt, no keys, no
data). The boot's decision-changing observation is one or two logged
`bss absence` records followed by the final cleanup line, which would make the
denied-association exchange a healthy bounded join, or a new specific refusal
with its branch.
