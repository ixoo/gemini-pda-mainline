# Ninth Phase B deployment, runtime 10: candidate 9 composed, not installed

Status: candidate 9 is composed and offline-validated on the laptop; it is
not installed, no device action has happened, and the device remains in
changed-boot Gemian `61bf9a0c…`. Installation over the installed candidate 8
and the owner's physical boot2 start follow this record.

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
receipt digest. The bound join script is the candidate-8 one.

The runtime-10 protocol, hypothesis and decision branches are exactly those
of [runtime 9](RUNTIME_9_PREPARATION.md): one passive scan, one WPA2-PSK
CCMP connect carrying the RSN element, no key, no payload transmission, no
EAPOL reply, the driver's deauthentication within 250 ms of activation or at
the first observed EAPOL frame, then the ordered teardown. The one difference
is that the association request is now admitted by the driver, so the boot's
decision-changing observation is the association TX record followed by the
AP's response. Wi-Fi remains incomplete in every branch.
