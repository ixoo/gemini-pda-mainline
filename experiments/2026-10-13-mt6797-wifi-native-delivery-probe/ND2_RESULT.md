# ND2 result — local deadline refusal; native firmware mode untested

One completed negative run, followed by one reviewed recovery and independently
confirmed Gemian return. This is not a firmware-capability result. Device
operations and observations were performed by the sole laptop custodian.

## Exact identities

- Kernel input: `2e9cae6ea4fb3b79221ed8c18829c03326018265`;
  profile `mt6797-a53-wifi-native-delivery-diag`.
- Package inventory: `2d2c66154d686b94c384f835e154c2370c4891f5af84752b8f69875134c1c201`.
- Image.gz: `e376bbd4fdf234501284db7ae95bed2e0a295300de337d9825e899862c3bc31a`.
- Compositor: `f3d08b94a70cc21f2ebcef398e340b63cd8c4016`;
  runtime executable pin: `4341cb5e7359a2122d6ae420ade6ae1c9cd1c487`.
- [Candidate receipt](results/native-delivery-candidate-2.json):
  `9e8e008f2e8028aa26edfa9c6083b5edb09ba28aff75982187759cc8aa6f2898`.
- Raw boot image: `d0340e7eee39b307a3df6b3a63b30633212388cc706e0c550c2ca1e7a6c26069`,
  12668928 bytes; full boot2:
  `306ca76fb3136ec96f369bdce72ccbce52a10bd4b05d99f5b763938e551bc533`.
- Mainline boot: `9f148559-5c83-47be-b424-e4c0dfe510cc`.

Board DT, configuration and the private 64-member RAM root were byte-identical
to ND1; only the kernel changed. The live-GPT guarded installation selected
boot2 p30 (`179:30`), not root p29 (`179:29`), matched full-partition readback
and ended in clean shutdown before physical boot2 selection.

## Observations and negative result

Phase A passed all 285 common-init steps with `ready_for_scan=true`. The
associated data-phase budget was 6184 ms plus 5000 ms teardown margin.

```text
one-shot WLAN native-diag: state=4 act=1 total=0 native=0 bytes=0
one-shot WLAN join stopped: status=-5 first=-22 submitted=0x801 debt=0 cleanup=0 branch=4
```

`native_delivery_pass=false`: zero native frames, no ACTIVE state, no
post-ACTIVE Wi-Fi challenge. The command whitelist repair cleared ND1's earlier
refusal, but ND2 still supplied no firmware-side native-mode datum.

## Source diagnosis, distinct from observation

The native caller passed the whole lifetime (~11.184 seconds) to HIF entry,
whose existing operation limit is one second. Command preparation had already
debited one TC4 page and marked the sequence before entry refused with
`-EINVAL`, poisoning HIF before any PIO. Subsequent RX returned `-EIO`.
The MAC success-path debt remained zero; that does not refund the HIF ledger.
This deterministic source diagnosis was independently reviewed and reproduced
with actual host-test HIF entry/submission. It is not firmware rejection.

Proposal 0185 caps both native actions at the existing 100 ms operation budget
or remaining lifetime, whichever is shorter. Its host regression exercises the
actual extracted caller and actual HIF with finite mocked MMIO; no mock proves
hardware submission or firmware semantics. All diagnostic limits remain intact.

## Preservation and return

All 63 pre-recovery seal hashes independently matched (zero mismatches).
The helper group was quiescent/safe; device quiescence passed with empty faults.
Service regression passed. Exactly one reviewed recovery was requested, without
retry. Changed-boot Gemian `8dc27f98-f95e-4f74-9c4d-d57fd96a613a`, kernel
`3.18.41+`, was independently verified through strict laptop SSH.

This summary uses checksum-verified sanitized custodian metadata and observation
extracts; raw captures, private RAM-root members, credentials and unit identifiers
remain private. Sanitized boot IDs and deployment checksums are retained.
[ND1's original return-unconfirmed record](ND1_RESULT.md) remains immutable;
later Gemian boot `1cff2fb4` was separately confirmed before ND2. Neither negative
run establishes native firmware capability or maintained Wi-Fi support.
