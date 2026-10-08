# Fifth Phase B deployment, physical boot pending

Status: candidate 5 is installed and fully read back; the device is cleanly
powered off; no mainline boot, host RF transmission or join result has been
observed for it. The laptop has handed the physical boot2 selection to the
owner. The laptop remains the sole custodian.

The [guarded deployment receipt](results/deployment-5.json) pins candidate 5:
receipt `c7a93e94…`, full padded boot2 `e6fe0e8d…`, written over predecessor
candidate 4 `eeb2ce9b…`, synced and flushed, with the independent
whole-partition digest and byte comparison matching. The installer was
prepared at source `d3b678ea` (generated installer SHA-256 `c013c02c…`) and
executed once under the standing boot2 authorization with the private
repository variable supplied through its final local receipt validation
(exit 0); the live guard passed on Gemian boot
`41113925-3f02-41e3-af9c-6e5225bb1a32`, target `179:30`, root `179:29`, stable
power; no fresh predecessor backup. Native Gemian power-off was requested
after the evidence flush, the SSH session ended with status 255 as the normal
disconnect, the device was confirmed unreachable, and nothing was rebooted.

Runtime-6 preparation on the laptop at `d3b678ea`: a fresh evidence root with
`wifi-phase-b/session-5` holding the true deployment-5 summary and `capture-5`
absent; both offline preflights passed with no RF.

The committed receipt [results/candidate-5.json](results/candidate-5.json)
(SHA-256 `c7a93e94…`) pairs the [compile 10](COMPILE_10.md) package
`7ee0f058…` with the candidate-4 RAM root and helper: boot image `ad91f738…`
(11442176 bytes), full padded boot2 `e6fe0e8d…`; initramfs, kernel config and
board DT byte-identical to candidate 4, so only the kernel image changed.
Both receipt slots and the runtime-6 identity copy carry the receipt digest.

Next: the owner's physical boot2 selection, then exactly one capture and one
session under the unchanged budget (one passive 500 ms scan on channel 40,
one bounded open-system join, no keys, no data). The hypothesis is that 0145
fills mac80211's rate record for the scanned BSS, so the boot's
decision-changing observation is the first management frame: join TX, RX and
acknowledgement records with an authentication or association status, or a
new specific failure; the helper's `connect_request` line should now read
acknowledged.
