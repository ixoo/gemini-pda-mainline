# Twelfth Phase B deployment, runtime 13: candidate 13 composed, not installed

Status: candidate 13 is composed and offline-validated by the owner on the
laptop with the reviewed composer at `6c27507c`; it is not installed, no
device action has happened, and the device remains in changed-boot Gemian
`999c7b7-431c…` with the installed candidate 11 (full padded boot2
`1c491341…`) as the predecessor. Installation and the owner's physical boot2
start follow this record; the owner alone prepares and executes the guarded
installer once these bindings are reviewed.

Candidate 12 (receipt `e8d9900f…`, compile 17) was composed, held and never
installed: before any boot, the pinned wpa_supplicant 2.11 was found to
declare 16 PTKSA replay counters in its RSN capabilities (0x000c) whenever
the AP's BSS carries the WMM vendor element, which the exact C1 RSN
admission refused; proposal 0157 admits capabilities 0 and 0x000c only, and
[compile 18](COMPILE_18.md) built it. Candidate 12's receipt stays committed
as evidence; deployment 12 never happened.

The committed receipt [results/candidate-13.json](results/candidate-13.json)
(SHA-256 `adc7a4a5…`, the owner's receipt byte for byte) pairs the compile-18
package `49afb45d…` (input `eba4baa4`, proposals 0153 to 0157) with the RAM
root of candidate 12, byte-identical: boot image `3a727730…` (12277760
bytes), full padded boot2 `ec412ce9…` (16 MiB), kernel image `bea14180…`
(6624058 bytes), initramfs `449832a3…` (5621445 bytes: the parent's 61
members unchanged, the release gate, the Phase C1 helper `bc499f28…` as the
62nd and `bin/wpa_supplicant` `0487b710…` as the 63rd), board DT
`25ab60f4…` and kernel config `153ea2d0…` byte-identical to candidates 8 to
12. The owner checked every file independently (the composer's LK
validation, the parent members, the exact DT, the PSCI and clock flags); no
credential is composed into the candidate. Both receipt slots and the
runtime-13 identity copy carry the receipt digest. The owner's fresh
PSK-bound script was generated from the corrected join source (mode 0600,
single link) and is never uploaded or hashed publicly.

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
