# Authenticated baseline candidate reconstruction

Recorded UTC: `2026-09-07T22:36:49Z`.

## Exact-candidate refusal

The retained kernel package, foundation candidate and validated userspace
package were recovered and audited at their pinned identities.  A clean
checkout of userspace revision
`e9c028005b88ef8536ecb58c095e8d172253fa12` then ran the existing private
candidate builder with the current mode-0700 A53 credential bundle.  The build
and independent candidate validator passed, but the result did **not** match
the previously observed candidate:

| Artifact | Previously observed | Reconstructed |
| --- | --- | --- |
| Raw Android-v0 image | `a25fe4cb907f4f3da2bf9f36fcf38b3fff7d8ba84adc37562fdcff2f1a422daf` | `3290b867bc6cb2ecee42e6ca1436e1ae29613c074e7e45b3836ecb2905f3e07c` |
| Padded boot2 image | `a423ad63fbb97d0f3fc4726d3957e05d3951480996b754d839a89d80a1232821` | `29f59c7f21a25b47d63d653857db9d7d0760d9a00f7193e098219699235f16f1` |
| Initramfs | `a678c4051204754dbb8043b25d3f61e0e6b4936fc4c92bea012140b9b6687d7a` | `b258a9a5dc894ecbd330005ecab841225b320a3c2b82abe725f3833c874d74cd` |
| Private candidate manifest | `54b07f0c70e77fd1e34fde4fc1c929980f0d8c3410f0a97ce3f15ffec1a66179` | `62440fdee9267e26d6f90148609a7c2551fdb9d6a9f603da03f891638c65180d` |

The raw and initramfs sizes exactly match the historical record.  The retained
Image, board DTB, resolved configuration, foundation, userspace manifest and
47-member archive contract all validate.  The historical secret-bearing
candidate and its original private credential bundle are no longer retained,
so their exact bytes cannot be reconstructed.  The evidence supports the
credential bundle as the remaining variable, but cannot prove a byte-level
delta against an unavailable archive.  Therefore the reconstructed artifact is
never represented as the old candidate and none of the old candidate's runtime
evidence is transferred to it.

The failed exact reconstruction made no device connection or device change.
Its disposable checkout is removed after preservation of the independently
validated private candidate below the ignored artifact tree.

## Candidate R selection boundary

The reconstructed artifact is named **Candidate R** for this session.  It is a
new first-boot candidate, not an exact replay.  Its intended kernel, DT,
configuration, userspace and storage behavior are unchanged; its independent
current authentication bundle provides the durable observation path needed to
collect new attributable evidence.  Candidate R is secret-bearing, remains
private, and has no hardware-support result.

The pre-boot hypothesis is that Candidate R boots the unchanged A53-only
baseline, leaves CPUs 8-9 offline, exposes the pinned USB address and key-only
Dropbear service, keeps automatic keyboard capture disabled, and preserves the
bounded RAM logger and recovery paths.  The unique evidence is a matching
full-partition boot2 readback followed by a fresh boot ID, exact kernel identity,
authenticated host-key-pinned connection, CPU/USB/console/input metadata and
bounded logger export from Candidate R itself.

Outcome branches are finite:

- A complete new baseline pass permits review of the separately bounded
  disconnect proof; it does not inherit or spend the keyboard capture claim.
- An attributable boot with any identity, CPU, USB, console, reader or logger
  mismatch rejects Candidate R and proceeds to evidence preservation and the
  reviewed known-good recovery path.
- Missing attribution or incomplete evidence is inconclusive, consumes the
  boot observation, and permits no retry or dependent keyboard action.

Installation may use the existing dynamic guarded installer only after an
independent review accepts this new identity.  It must resolve logical boot2
from the live GPT, require inactive/unmounted writable target and stable power,
record the predecessor checksum, write only if different, verify the complete
16 MiB readback, and shut down without reboot.  The owner alone then makes one
physical boot2 selection.  No Dropbear disconnect or keyboard capture is
performed during installation or before the fresh baseline is accepted.
