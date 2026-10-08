# Fifth Phase B candidate composed, not installed

Status: candidate 5 is composed and offline-validated on the laptop at source
`750d5ad6`; it is not installed, not booted and untested. The device is on the
live Gemian boot `41113925-3f02-41e3-af9c-6e5225bb1a32` with candidate 4
(boot2 `eeb2ce9b…`) still installed. The laptop remains the sole custodian.

The committed receipt [results/candidate-5.json](results/candidate-5.json)
(SHA-256 `c7a93e94…`) pairs the [compile 10](COMPILE_10.md) package
`7ee0f058…` with the candidate-4 RAM root and helper: boot image `ad91f738…`
(11442176 bytes), full padded boot2 `e6fe0e8d…`; initramfs, kernel config and
board DT byte-identical to candidate 4, so only the kernel image changed.
Both receipt slots and the runtime-6 identity copy carry the receipt digest.

Next, under the standing authorization and in this order: the guarded
`install-passive.py prepare` for deployment 5 over predecessor `eeb2ce9b…`,
the two offline preflights, the owner's physical boot2 selection, then the
runtime-6 protocol with a fresh root and a re-bound join script. The boot's
decision-changing observation is the first management frame: join TX, RX and
acknowledgement records with an authentication or association status, or a
new specific failure; the helper's `connect_request` line should now read
acknowledged.
