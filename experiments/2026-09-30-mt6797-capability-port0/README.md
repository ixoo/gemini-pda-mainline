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

The next candidate must use the exact pinned profile and validated boot2
package, with the same WMT, START, A53 regression, evidence-preservation and
reviewed-return gates as the preceding experiment. Its unique question is
whether port 1 receives a valid capability response while port 0 remains
unread. A valid response permits later planning for calibration, standard
wireless interfaces and packet transport; it is not usable Wi-Fi by itself.
