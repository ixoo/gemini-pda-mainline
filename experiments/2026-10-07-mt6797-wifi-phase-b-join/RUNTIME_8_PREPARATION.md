# Seventh Phase B deployment, runtime 8 in progress

Status: candidate 7 is installed and fully read back; the device was cleanly
powered off, and the owner has since physically started boot2. The laptop,
as sole custodian, is executing the reviewed runtime-8 capture and session
once; no runtime evidence has been returned yet. Nothing in the source, the
build or the runtime bindings changes until it arrives.

The [guarded deployment receipt](results/deployment-7.json) pins candidate 7:
receipt `e3134657…`, full padded boot2 `820657ed…`, written over predecessor
candidate 6 `e6b7dd4e…`, synced and flushed, with the independent
whole-partition digest and byte comparison matching. The installer was
prepared at source `dddb6e93` (generated installer SHA-256 `d8d4d7fd…`) and
executed once under the standing boot2 authorization with its final local
validator passing; the live guard passed on Gemian boot
`8599964c-c0d6-4a63-9081-5747400b45c9`, target `179:30`, root `179:29`, stable
power; no fresh predecessor backup. The clean shutdown was confirmed with the
device unreachable; nothing was rebooted by the laptop.

Runtime-8 preparation on the laptop at `dddb6e93`: a fresh evidence root with
`wifi-phase-b/session-7` holding the true deployment-7 summary and `capture-7`
absent; both offline preflights passed with no RF.

The committed receipt [results/candidate-7.json](results/candidate-7.json)
(SHA-256 `e3134657…`) pairs the [compile 12](COMPILE_12.md) package
`784aef75…` with the candidate-4 RAM root and helper: boot image `1fb75cff…`
(11442176 bytes), full padded boot2 `820657ed…`; initramfs, kernel config and
board DT byte-identical to candidates 4 to 6, so only the kernel image
changed, and that only by the reviewed proposal 0147. Both receipt slots and
the runtime-8 identity copy carry the receipt digest.

The runtime-8 protocol runs exactly once under the unchanged radio scope (one
passive scan, one open-system authenticate-and-associate attempt, no keys, no
data). The boot's decision-changing observation is one or two logged
`bss absence` records followed by the final cleanup line, which would make the
denied-association exchange a healthy bounded join, or a new specific refusal
with its branch.
