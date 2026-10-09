# Eleventh Phase B deployment, runtime 12: candidate 11 composed, not installed

Status: candidate 11 is composed and offline-validated on the laptop; it is
not installed, no device action has happened, and the device remains in
changed-boot Gemian `5c61cd3e…`. Installation over the installed candidate 10
and the owner's physical boot2 start follow this record.

The committed receipt [results/candidate-11.json](results/candidate-11.json)
(SHA-256 `08764467…`) pairs the [compile 16](COMPILE_16.md) package
`642165d4…` (input `707e2d71`, proposal 0152) with candidate 10's RAM root:
boot image `b4deac77…` (11444224 bytes), full padded boot2 `1c491341…`
(16 MiB), kernel image `1541bc87…` (6621941 bytes). The initramfs
`dc8a4479…` (62 members, the Phase C1 helper `bc499f28…`), board DT
`25ab60f4…`, kernel config `153ea2d0…`, helper and private parent are
byte-identical to candidates 8 to 10, verified independently by the laptop;
only the kernel image, and with it the boot image and the padded partition,
changed, and that only by proposal 0152. The laptop's offline gates passed
(compositor, PSCI and clock, private members, 805 package checksums and the
651-patch provenance at fetch). Both receipt slots and the runtime-12 identity
copy carry the receipt digest.

The runtime-12 protocol, hypothesis and decision branches are those of
[runtime 11](RUNTIME_11.md): one passive scan, one WPA2-PSK CCMP connect
carrying the RSN element, no key, no payload transmission, no EAPOL reply,
the driver's deauthentication within 250 ms of activation or at the first
observed EAPOL frame, then the ordered teardown. One thing differs: a clear
EAPOL-Key frame carrying BSSID tag 15 is admitted after the accepted
association and until the successful BSS command credit completion is
recorded. Branches, stated in advance: the packet after the accepted
association decodes as a clear EAPOL-Key frame and is observed (`eapol
observed … vector=0 bss=15 activated=0`), then hold, deauthentication and
teardown; or it is refused again with its header named, which decides the
next step without a further repeat of this artifact; or the AP's behaviour
differs and the existing branches apply. Wi-Fi remains incomplete in every
branch.
