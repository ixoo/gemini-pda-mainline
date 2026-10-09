# Ninth Phase B deployment, runtime 10 awaiting the owner's boot

Status: candidate 9 is installed and fully read back; the device was cleanly
powered off and is unbooted, awaiting the owner's physical boot2 start. The
laptop, as sole custodian, will execute the reviewed runtime-10 capture and
session exactly once after that; no runtime evidence exists yet. Nothing in
the source, the build or the runtime bindings changes until it arrives.

The [guarded deployment receipt](results/deployment-9.json) pins candidate 9:
receipt `d6857436…`, full padded boot2 `8d2c87f9…`, written over predecessor
candidate 8 `1eed3948…`, synced and flushed, with the independent full 16 MiB
byte readback matching. The installer was prepared at source `00f89ce8`
(generated installer SHA-256 `27de88db…`; syntax and ShellCheck passed) and
executed once under the standing boot2 authorization with its final local
validator passing; the live guard passed twice on Gemian boot `61bf9a0c…`,
target `179:30`, root `179:29`, stable power; no fresh predecessor backup,
temporary readback removed. The clean shutdown was confirmed with the device
unreachable; nothing was rebooted.

Runtime-10 preparation on the laptop at `00f89ce8`: a fresh evidence root with
`wifi-phase-b/session-9` holding the true deployment-9 summary and `capture-9`
absent; both offline preflights passed with the bound script and no RF.

The committed receipt [results/candidate-9.json](results/candidate-9.json)
(SHA-256 `d6857436…`) pairs the [compile 14](COMPILE_14.md) package
`3ecfdecb…` (input `9ce81bc3`, proposal 0149) with candidate 8's RAM root:
boot image `7f1aa67f…` (11444224 bytes), full padded boot2 `8d2c87f9…`
(16 MiB), kernel image `b8e7c827…` (6622366 bytes). The initramfs
`dc8a4479…` (62 members, the Phase C1 helper `bc499f28…`), board DT
`25ab60f4…`, kernel config `153ea2d0…`, helper and private parent are
byte-identical to candidate 8, verified independently by the laptop; only the
kernel image, and with it the boot image and the padded partition, changed,
and that only by proposal 0149. The laptop's offline gates passed
(compositor, Android v0 header, LK, 802 package checksums, config, parent,
62 members). Both receipt slots and the runtime-10 identity copy carry the
receipt digest.

The runtime-10 protocol, hypothesis and decision branches are exactly those
of [runtime 9](RUNTIME_9_PREPARATION.md): one passive scan, one WPA2-PSK
CCMP connect carrying the RSN element, no key, no payload transmission, no
EAPOL reply, the driver's deauthentication within 250 ms of activation or at
the first observed EAPOL frame, then the ordered teardown. The one difference
is that the association request is now admitted by the driver, so the boot's
decision-changing observation is the association TX record followed by the
AP's response. Wi-Fi remains incomplete in every branch.
