# Refused descriptor framing: two retained failure-only scalars

Status: authored and locally tested observation, no build or candidate yet, 2026-10-18 UTC. [C8](CCMP8_RESULT.md) is consumed. The complete
goal remains ordinary secure Wi-Fi, DHCP/three replies/ten-minute authenticated
SSH and healthy reconnect; this observation does not replace those gates.

## Concrete missing distinction

C8 passed four CLOSED length checks before refusing advertised/header 88/40.
Its selected-from-one-word cleanup sequence was exercised and insufficient.
The four-byte staged hint (`0x4000` type/group word) does not contain header
translation, header length/offset or status flags. It cannot identify native
versus translated framing, a null frame or a valid descriptor.

Pinned public gen3 source at
[59e00a9, nic_rx.h](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/wlan/gen3/include/nic/nic_rx.h#L103-L156)
defines the base descriptor fields; its
[structure](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/wlan/gen3/include/nic/nic_rx.h#L455-L467)
is 16 bytes. Header-control byte 6 contains header length (low six bits),
two-byte offset (bit 6) and translation (bit 7). Little-endian bytes 10-11
contain status flags, including NULL (bit 12) and DATA (bit 13).
The independently retained header matches the existing public-contract pin
`0645985217a887e6c2d367955fa656b45f716a6aeeee13a29a2b462eb8dea5cb`.

These layout facts support retaining two raw scalar hints. They do not certify
that refused bytes are a descriptor, that firmware modified a queued packet,
or that a 48-byte transformation exists. No accepted-packet parser may consume
the refused buffer. No packet/PN/address/key bytes are to be logged.

## Hypothesis, observation and branches (before implementation)

Hypothesis: the refused base's header-control and status fields distinguish
native-header-shaped records from translated records or an unsupported shape,
allowing the pending-length/monitor-disable source review to target the right
framing path. This does not by itself distinguish conversion from wrong pairing.

Unique observation: on the existing fatal header-length refusal only, retain
raw byte 6 and LE16 at offset 10 from the already completed transfer. Require
both advertised and header lengths at least 16, at least 16 staged bytes,
complete setup/transfer and the existing untrusted type hint's class 2.
A separate valid bit means only those bounds were met; zero values are not
absence. No further hardware read, group walk, payload parse or caller copy.
Emit one extra fixed-prefix line at the existing failure site, including the
valid bit (also 0 on refusals that do not meet the bounds).

1. Translation bit clear: compare the header-length/offset and status hints
   with the public native framing path. A 24-byte hint plus declared 40 may
   be consistent with a header-only shape; arithmetic is not packet identity,
   proof of a null frame or a producer mechanism.
2. Translation bit set: compare with the translated header contract. Do not
   synthesize an 802.11 header or infer integrity/PN/key attribution from it.
3. Absent/nonsensical/unsupported hint: preserve that limit; do not treat the
   layout as established or expand acquisition at runtime.
4. Earlier/different failure: classify separately. No identical retry to fill
   missing data and no deadline/credit adjustment.
5. Healthy cleanup/network: retain separate actual DHCP/ping/SSH and cleanup
   verdicts. One bounded compatibility lifetime is not ordinary crypto,
   key-retirement, healthy reuse or ten-minute acceptance.

## Small implementation and validation boundary

Keep exact C8 arbitration and all existing I/O, complete-transfer span,
selected/header equality, poison/no-copy, fatal retirement and deadline paths.
Add only two raw result fields, their validity bit and one failure-only log.
Default zero remains absence. No extra accepted-RX interpretation, source
control command, monitor operation, credit refund or ordinary PN bypass.
Initialization/bookkeeping can affect timing; success would not prove causality.

Reuse actual HIF transport fixtures. Compare the legacy boot/requested-runtime
and selected-runtime operation/publication tables with C8, both ports and all
five observed mismatch pairs (76/28, 80/32, 449/401, 427/379, 88/40). Test the
new fields on class-2 versus other hints, small/invalid lengths, capacity,
partial transport, guard deadline, valid-zero values and every reachable I/O
fault. Failures retain no caller packet bytes; poison forbids second I/O and
clears new result validity on that later call. Compile the actual MAC formatter
and verify named refusal/hint output without changing classifier verdicts.
Other driver files and MAC code outside that formatter remain byte-identical.

Only after these checks: one logical format-patch, canonical-order named
profile with the same fragments, clean pushed Buildbox build, validated package
and real receipt, exact installer/recovery bindings and guarded boot2 readback.
The later one-capture/one-session/one-return protocol retains all inherited
budgets and source pins. Owner physically selects boot2 after clean shutdown.
No device action or next boot is selected by this design record alone.

Remove this diagnostic when the RX producer/ownership contract is resolved.
A maintained implementation targets Linux's wireless subsystem and needs its
normal review; this internal non-certifying archive is not an upstream submission.

## Authored C9 input

[Proposal 0199](../../patches/proposals/0199-wifi-mt6797-retain-refused-descriptor-framing-hints.patch)
adds the two fields and validity bit to the HIF result, guarded capture within
the existing refusal, and one separate MAC failure line. It adds no helpers,
cache or register access. Other source files and all MAC code outside the
formatter are byte-identical to C8. This is one logical observation change.

The [actual-source fixture](tests/run-refused-framing-test.py) passes locally
under ASan/UBSan: 3956 paired cases including 3632 injected faults, in addition
to the retained C8 selected/legacy cases. It covers both ports, three receive
APIs, all five mismatch pairs, class/base-size/capacity bounds, valid zero
values and expiration at the guard after a complete read. No-copy, poison,
no second I/O and absence of stale hint validity pass. Parent/child I/O and
publication tables match exactly. The actual MAC formatter emits one extra
hint line only at a named protocol refusal; classifier/helper negative cases
still pass and the new hint cannot manufacture a pass or fault.

Profile `mt6797-a53-wifi-ccmp-framing-hint` selects C8's 693 ordered patches
plus 0199 with identical 26 fragments. All existing named profiles/series are
unchanged; canonical order and all 32 profile checks pass. Strict checkpatch
reports only the deliberately absent truthful DCO sign-off (one error, zero
warnings/checks) on this internal non-certifying archive. Linux tests and an
ordinary clean pushed Buildbox build remain required before a real package,
receipt or deployment. No C9 runtime is selected by these host test results.

Proposal SHA-256: `c3dba8b04ec1a9c3f509e497d915dc9b487d74637f1670827715beb79fce461a`.
