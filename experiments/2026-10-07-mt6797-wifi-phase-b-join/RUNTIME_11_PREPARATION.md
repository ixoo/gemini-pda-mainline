# Tenth Phase B deployment, runtime 11: candidate 10 composed, not installed

Status: candidate 10 is composed and offline-validated on the laptop; it is
not installed, no device action has happened, and the device remains in
changed-boot Gemian `a51fe04d…`. Installation over the installed candidate 9
and the owner's physical boot2 start follow this record.

The committed receipt [results/candidate-10.json](results/candidate-10.json)
(SHA-256 `37fc49ad…`) pairs the [compile 15](COMPILE_15.md) package
`efb0b28a…` (input `89d60283`, proposals 0150 and 0151) with candidate 9's
RAM root: boot image `966d6426…` (11444224 bytes), full padded boot2
`57f9e65c…` (16 MiB), kernel image `92978591…` (6622699 bytes). The
initramfs `dc8a4479…` (62 members, the Phase C1 helper `bc499f28…`), board DT
`25ab60f4…`, kernel config `153ea2d0…`, helper and private parent are
byte-identical to candidates 8 and 9, verified independently by the laptop;
only the kernel image, and with it the boot image and the padded partition,
changed, and that only by proposals 0150 and 0151. The laptop's offline gates
passed (compositor, Android v0 header, LK, private parent, config, 62
members; 804 package checksums and the 650-patch provenance at fetch). Both
receipt slots and the runtime-11 identity copy carry the receipt digest. The
bound join script is the candidate-8 one, re-bound privately for runtime 11.

The runtime-11 protocol, hypothesis and decision branches are those of
[runtime 10](RUNTIME_10.md): one passive scan, one WPA2-PSK CCMP connect
carrying the RSN element, no key, no payload transmission, no EAPOL reply,
the driver's deauthentication within 250 ms of activation or at the first
observed EAPOL frame, then the ordered teardown. Two things differ: a clear
EAPOL-Key frame from the target is now observed with or without the RX vector
(`vector=0` records the absence), and a packet the frame gate refuses is
recorded with its bounded header summary. Branches, stated in advance: the
packet after the accepted association decodes as a clear EAPOL-Key frame and
is observed, then hold, deauthentication and teardown; or it is refused again
with its header named, which decides the next step without a further repeat
of this artifact; or the AP's behaviour differs and the existing branches
apply. Wi-Fi remains incomplete in every branch.
