# DA921x original untagged uevent dispatch

| Field | Value |
| --- | --- |
| ID | `2026-08-01-da921x-uevent-untagged-dispatch` |
| Status | `input validated; awaiting exact buildbox` |
| Subsystem | I2C, OF, kobject uevent, netlink |
| Device variant | Named Gemini PDA development unit |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 transport boundary |

## Question or hypothesis

Can the exact runtime-proven stage-22 event traverse the original untagged
delivery function once, producing exactly one function entry and return, one
allocation, one broadcast, one exact userspace receipt, and no duplicate while
preserving the one-socket/one-listener, unbound-client, zero-I2C, and
serviceability baseline?

Stage 22 proved the complete event and netlink result through a deliberately
isolated one-listener delivery loop. Stage 23 retains that exact target but
calls `uevent_net_broadcast_untagged()` with the bounded observation structure
already introduced for the stage-20 no-listener branch. The helper independently
validates the same exact 293-byte datagram without printing its payload.

## Decision

- Stage 23 with one attempt, one function entry and return, one baseline
  socket, one observed socket and listener, one allocation, one broadcast,
  normalized return zero, one exact receipt, and no duplicate passes.
- A missing target or second trigger fails before replay.
- Any counter, topology, event, receipt, source, credential, client, I2C, CPU,
  or serviceability mismatch rejects attribution.
- Visual white/grey-screen and reboot behavior alone remains inconclusive.

## Safety and build policy

The experiment emits one intentional uevent multicast only after reconstructing
the proven stage-22 predecessor with checksum-pinned helpers. The matching
DA921x driver remains module-only and absent from the initramfs; the real client
remains unbound. The patch adds no driver, provider, I2C transfer, register
access, printk, or device-storage path.

Build only through `./scripts/build-kernel --backend buildbox` from an exact
clean pushed commit. Do not run a native VM kernel build unless the owner
explicitly requests one. The experiment-only patch has no DCO sign-off and is
not submission-ready.

## Associated code

- `listener/untagged-dispatch-listener.c` binds the sole group-1 listener,
  triggers the exact stage-23 replay, and validates one exact receipt plus no
  duplicate without printing the event.
- `scripts/build-listener.sh` pins and statically cross-builds that helper only
  in the managed VM.
- Patch `0144` adds the one-shot kernel-side function-boundary observation.

## Frozen pre-build hypothesis

The exact input-to-action map is recorded in
`results/pre-build-hypothesis.txt`. Buildbox must produce the named release
with the complete predecessor chain and only the new stage-23 gate added. No
package or candidate may be selected by timestamp.

All 133 patches apply to the pinned Linux 7.1.3 source. The named profile
resolves the complete stage-22 predecessor plus only the untagged-dispatch gate
and release `7.1.3-gemini-da921x-untag`. All 50 manifest profiles pass the
canonical-order invariant and all eight focused mutations are rejected. Strict
checkpatch has zero warnings and checks; its sole error is the intentionally
absent experiment-only DCO. Two static ARM64 helper builds were byte-identical.
Host and VM free-space checks passed with 90 GiB and 83 GiB available. Exact
identities are in `results/input-validation.txt`. No native VM kernel build or
device access was used.

## Follow-up

Commit and push the exact clean inputs, then submit only that commit to the
explicit buildbox backend.
