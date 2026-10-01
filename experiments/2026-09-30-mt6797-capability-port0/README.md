# Query capability while receive port 0 is occupied

The [preceding boot](../2026-09-30-mt6797-capability-admit/results/runtime-1.json)
reached firmware-ready, then stopped before sending the capability command:
WRPLR was `0x00000059`. Its low half reported 89 queued bytes on port 0;
the high half, for port 1, was zero. The packet was not read, so its identity
and cause remain unknown. No radio command or packet DMA ran.

The pinned gen3 `nicRxWaitResponse()` reads the selected port's half of
WRPLR and the corresponding data port. Its capability query selects port 1.
This was checked against Planet revision
`c5b0be85017ad0c599725e8273842efdbecdd88a`: `nic/nic_rx.c`
SHA-256 `a844bdf75065a152e78d30c789aabb398b0d0f336d30d6ffd028793bf091412b`
at lines 3637–3688, and `common/wlan_lib.c` SHA-256
`56bf99536fcb96de5a5198943aec96c9efccb8af89261b29c62046e6560c422f`
at lines 3775–3789. The source shows a separate port-1 reply path; it does
not identify the pending port-0 packet or prove firmware will reply here.

[Patch 0056](../../patches/proposals/0056-wifi-mediatek-admit-capability-with-port0-pending.patch)
therefore refuses a pre-existing port-1 packet but leaves port 0 untouched.
After submission it waits only for a port-1 reply and preserves the full
WRPLR word in the trace. It retains the one-attempt limit, deadline, strict
reply size/header checks and no-radio/no-DMA scope. It does not drain or
silently classify port 0. A port-1 timeout, unexpected length or transport
failure ends this boot's HIF session.

The [focused host test](tests/test-capability.c) uses the actual patched HIF
source. It checks START-to-capability on one HIF object, a pending 89-byte
port-0 length before and after a successful port-1 capability reply, refusal
of a pre-existing port-1 packet, all 69 scalar access faults and the prior
malformed/deadline cases. The former all-ports guard fails the new success
case; the corrected guard passes with C11, warnings as errors, ASan and UBSan.
[Validation details](results/host-validation.json). No live capability reply
has yet been observed.

## Build and candidate

The clean pushed kernel-input commit `3f2a0903d7e8631d561a08c6539ef4f0a0ff9bab`
built on Buildbox as profile `mt6797-a53-wifi-capability-port0`, release
`7.1.3-gemini-a53-wifi-capability-port0`. Its validated package inventory
is SHA-256 `70d910c493c9a0973e8506e7d0afb9e0a9544926136d44a8720e949b79834db9`.
The 52-member private RAM root changed only `/init`'s release gate; firmware
remained hash-identical. The board DT matches the previously booted candidate
at SHA-256 `cef9373ea3aa0e1a8a45a13b953ae95e48939b211e41a73052543be784ee3214`.
The [sanitized candidate receipt](results/candidate.json) pins the 16 MiB
boot2 image at SHA-256 `503126de747a15bc922d845dd4cfe6709eb6ba30ea5b150b62d051b9b6a20f39`.
The [build receipt](results/build.json) records the package and candidate identities.
No device write or boot has yet occurred with this candidate.

The guarded installer is bound to known-good Gemian boot
`064c5064-690b-46e1-9673-3f78eb802831` and previous boot2 checksum
`f066866c178e38d77f18722f9e3286a6e98316997e28f2157c62f434f1aa1d4b`.
It resolves logical boot2 from live GPT, checks the device guard, then writes,
flushes and verifies a full readback before clean shutdown. The owner selects
boot2 physically. The next boot will test whether port 1 receives a valid
capability response while port 0 remains unread. A valid response permits
later planning for calibration, standard wireless interfaces and packet
transport; it is not usable Wi-Fi by itself.
