# Twelfth Phase B deployment, runtime 13: candidate 12 composed, not installed, HELD

Hold (2026-10-09): a source mismatch is known before any boot. The pinned
wpa_supplicant 2.11 claims WMM whenever the AP's BSS carries the WMM vendor
element (`wpa_supplicant.c` 2112 to 2117) and then declares 16 PTKSA replay
counters in its RSN capabilities (`rsn_supp/wpa_ie.c` 108 to 114, value
0x000c), while candidate 12's driver admits only the exact C1 RSN body with
capabilities 0. The owner's metadata-only check of the retained runtime-12
scan shows the target's WMM element present, so candidate 12 would stop at
the association admission. Candidate 12 is preserved unused; no identical
artifact is booted; proposal 0157 (admit capabilities 0x0000 or 0x000c only)
is under review and a later compile supersedes this candidate.

Status (before the hold): candidate 12 is composed and offline-validated by the owner on the
laptop with the reviewed composer; it is not installed, no device action has
happened, and the device remains in changed-boot Gemian `999c7b7-431c…`.
Installation over the installed candidate 11 and the owner's physical boot2
start follow this record; the owner alone prepares and executes the guarded
installer once these bindings are reviewed.

The committed receipt [results/candidate-12.json](results/candidate-12.json)
(SHA-256 `e8d9900f…`, the owner's receipt byte for byte) pairs the
[compile 17](COMPILE_17.md) package `1997dffb…` (input `0e333617`,
proposals 0153 to 0156) with candidate 11's RAM root plus the reviewed static
supplicant: boot image `135888f6…` (12277760 bytes), full padded boot2
`ec707495…` (16 MiB), kernel image `0c24f88f…` (6624463 bytes), initramfs
`449832a3…` (5621445 bytes: the parent's 61 members unchanged, the release
gate, the Phase C1 helper `bc499f28…` as the 62nd and `bin/wpa_supplicant`
`0487b710…` as the 63rd), board DT `25ab60f4…` and kernel config
`153ea2d0…` byte-identical to candidates 8 to 11. The owner checked every
file independently: the exact parent DT, the PSCI and clock flags, the LK
checks and the package provenance. Both receipt slots and the runtime-13
identity copy carry the receipt digest. The predecessor for deployment 12 is
the installed candidate 11, full padded boot2 `1c491341…`.

The runtime-13 protocol, hypothesis and decision branches are those stated
in [Phase C2](PHASE_C.md#device-protocol-stated-in-advance): the pinned
supplicant owns the connection from a private PSK-bound script that the
preparation tool and the host require; one passive channel-40 scan, the
open-system authentication and RSN association, the two EAPOL frames each
way, the two key commands with their credits, the hold, the driver's
deauthentication, then the two key removals and the three-stage teardown;
reviewed native recovery after the private export of the complete supplicant
log. The unique observation is the driver handshake path (`eapol delivered`,
`eapol sent`, `key command … submitted`, `key credit returned`, `key removal
… submitted`) with the supplicant's fixed phrases (one scan result set, key
negotiation completed, connected). Branches, stated in advance: the
conjunction holds and the healthy ordered teardown follows (C2 passed, no
installed-key or operational claim); the supplicant does not complete while
the framing is admitted (its phrases and the driver records decide, the
healthy teardown still runs at the hold's end); a key command is refused or
its credit ambiguous or late (fail-stop, seal, reviewed recovery); a scan or
association shape is refused (named refusal, fail-stop); or the AP's
behaviour differs. No branch repeats a boot without a decision-changing
change. Wi-Fi remains incomplete in every branch.
