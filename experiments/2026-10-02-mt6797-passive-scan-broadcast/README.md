# MT6797 passive scan with normal broadcast reception

Status: source-reviewed successor; build and candidate validated, runtime pending. The consumed
[non-DFS scan](../2026-10-02-mt6797-passive-scan-5g/results/runtime-1.json)
exposed channel 40 and completed without any management packet or BSS result.
Changed-boot Gemian remained connected at 5200 MHz.

## Concrete setup difference

The [source receipt](results/sources.json) pins the gen3 RX-mode call site.
`gl_init.c:832–885` runs `wlanoidSetCurrentPacketFilter` from
`ndo_set_rx_mode`, selecting broadcast when IFF_BROADCAST is present.
`wlan_oid.c:6109–6168` accepts that supported bit and sends normal CID 0x0a
with a four-byte little-endian filter word, set=true and response=false.
The mainline scan parent sends no such command. This establishes a missing
normal setup operation, not its role in the observed absence of frames.

The [retained filter analysis](../2026-09-08-mt6797-wlan-offloads/RECEIVE.md#retained-packet-filter-handler)
joins broadcast bit 0x08 to clearing bit 6 in a local callback value. Its GET
and SET callbacks remain unresolved. A private follow-up of the existing
complete scan state graph identifies uses of those same callback slots:
it saves the initial value and clears bit 11, or bits 4 and 11, on the selected
scan setup branches. Those local changes preserve bits 5, 6 and 7. This does
not establish callback success, a hardware register, or every runtime path.
No register write is derived from these value bits.

## Small change

Patch 0078 admits only bytes `08 00 00 00` after immutable board-record
submission. The one-shot scan owner sends this command once before its BSS
activation and V2 scan request. It uses the existing normal sequence history,
TC4 debit and PIO sender. Any unsupported word, truncated payload or earlier
phase is refused. Returned credit and scan completion never claim filter
application. This is a synthetic experiment archive without DCO certification.

The isolated `mt6797-a53-wifi-passive-scan-broadcast` profile inherits the
validated parent and appends only this patch. The advertised channels,
cfg80211 restrictions, private board record, firmware and receive parser remain
the parent's. The focused C test covers wire bytes, invalid filter words and
lengths, phase gating, sequence reuse and transport failure.

## One-boot hypothesis and branches

Hypothesis: the missing broadcast-filter setup prevents delivery of native
beacons during the otherwise completing passive scan. The new observation is
whether the exact candidate receives a valid native beacon and exposes a BSS
through standard iw after this one added setup command.

The protocol permits one filter submission, one BSS activation and one passive
scan. The existing five-second scan deadline, 256 polls, sixteen RX packets per
tick and 4096 packets overall remain finite. It retains the existing maximum
one cancellation and one BSS deactivation on healthy permitted terminal paths.
No command is retried after uncertainty; no second scan or lifetime reuse is
allowed. No monitor/promiscuous mode, active probe, peer TX, association, key,
packet DMA, IRQ or direct filter-register operation is admitted.

A valid beacon/BSS result supports management reception for the exact candidate
and permits the next association design. Completion without management packets
refutes this as a sufficient fix and requires a different receive/tuning
measurement before another boot. Submission, transport, ownership or protocol
failure stops I/O and keeps the lifetime consumed. Preserve the complete private
log and standard output before the already reviewed recovery; require changed
Gemian boot, carrier and A53/provider regression. No working Wi-Fi claim follows
from filter submission alone.

Build with `./scripts/build-kernel --backend buildbox` from committed, pushed,
clean inputs. Candidate composition, guarded boot2 installation, full readback,
clean shutdown and owner physical selection remain separate mandatory steps.
Raw firmware, calibration, captures, SSIDs and peer addresses stay private.

## Build and candidate preparation

The [Buildbox receipt](results/build.json) records the exact clean pushed
compile, package validation and source identities. The changed MAC compiled
without diagnostics; historical whitespace and unused CPU-helper warnings
remain. C11/Werror ASan/UBSan filter and inherited scan tests pass. Checkpatch
reports zero errors, warnings and checks with synthetic-signoff checking
intentionally excluded; its optional spelling/const lists were unavailable.
All 261 manifest profiles preserve canonical series order.

The [candidate](results/candidate.json) validates the complete tested 5 GHz
parent, exact package, unchanged proven booted DT, Android container and full
16 MiB padding. Its 59-member RAM root changes only the release string in
`init`; firmware, private board record, authentication and all six userspace
ELFs are byte-identical. The published RAM transform reproduced that output.
The [offline preflight](results/preflight.json) covers candidate/session
identity, private authentication, the reviewed recovery closure, generated
installer guards and shell checks. That initial preflight preceded deployment;
the actual deployment follow-up is recorded below. No runtime scan or radio
operation has been performed for this candidate.

The [actual boot2 deployment](results/deployment-1.json) resolved inactive boot2
from the live GPT in known-good Gemian and verified identity, distinct root,
unmounted state, exact size and stable power. It preserved the predecessor
checksum, wrote/synced/flushed the exact padded image, matched the full 16 MiB
readback and confirmed clean shutdown. It relied on the verified project-wide
backup and made no fresh predecessor backup. The [deployed preflights](results/preflight-deployed-1.json)
pass against that actual receipt. Capture and firmware START remain unconsumed;
physical owner selection and the one scan remain pending.
