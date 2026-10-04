# MT6797 shared STP task framing preparation

Historical compile checkpoint: this intermediate profile and series have been
retired after the [task-routing consolidation](../2026-10-04-mt6797-stp-task-routing/README.md#consolidation-after-validation).
Receipts and commands below refer to their original input commits. Current
compile reproduction uses `mt6797-a53-stp-task-routing-compile`.

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-04-mt6797-stp-task-framing` |
| Status | Driver dependency draft; host and Buildbox checks pass; runtime untested |
| Subsystem | Shared Bluetooth/WMT STP framing |
| Date | 2026-10-04 |
| Device action | None; owner unavailable; runtime testing deferred |

## Change and boundaries

Bluetooth task 0 and WMT task 4 share full-mode STP framing. The existing
codec accepts only WMT and limits commands to 1005 payload bytes. Patch
[0103](../../patches/proposals/0103-soc-mediatek-extract-task-aware-full-STP-framing.patch)
extracts the ordinary task codec and retains the WMT API, task filter and
command ceiling. Existing WMT callers use the extracted implementation.
The separate owner-held byte parser prepares complete-frame collection for
later task delivery; it has no production caller yet.

The selected Gemian full-mode parser rejects lengths above 2048 bytes despite
the 12-bit length field. Tasks 5 and 6 enter its separate firmware-message
path before ordinary header-checksum processing. The new codec accepts
ordinary tasks 0–4 and 7, refuses those special tasks, NAK and unsupported
headers, and publishes payload aliases only after exact length and CRC
validation. This is deliberately narrower than the vendor parser's recovery
behavior. The pinned source identity is in the
[receipt](results/validation.json); prior WMT framing provenance remains in the
[original audit](../2026-10-03-mt6797-wifi-audit/results/full-stp-codec.json).

The byte parser owns a bounded persistent buffer, never a kernel stack buffer.
It stops after one complete frame or a refusal; its owner must consume the
payload before collecting the next frame. Frame reinitialization must not
reset shared link sequence or ACK state. This patch introduces no task
registration, link state, IRQ handling, power operation or HCI device.
Shared sequence/ACK ownership, client lifetime, receive demultiplexing and
reset epochs are the next transport work. Bluetooth function enablement and
HCI integration depend on that transport; GPS has no driver claim here.

The isolated `mt6797-a53-stp-task-compile` profile extends the AFE compile
profile by this single patch, with unchanged configuration and board DT.
It is a compile checkpoint, not a boot candidate. The currently installed
version-read candidate remains unchanged. The unsigned internal format-patch
has a synthetic non-certifying author and is not submission-ready.
Its expected eventual destination is the common MediaTek connectivity
transport, with task clients in their normal subsystems. Delete this temporary
patch after a reviewed upstream transport supersedes it.

## Validation and reproduction

The [test](test-stp.c) compiles the actual kernel headers. It covers Bluetooth
HCI Reset and completion golden frames, all ordinary tasks and 64 sequence/ACK
combinations, 2048-byte payloads, the preserved WMT ceiling, ACK frames,
truncation, corruption, invalid arguments and terminal byte parsing. CRC
vectors were independently evaluated using the pinned Linux CRC16 table;
they are protocol fixtures, not observed Bluetooth transactions.

The four existing WMT codec/state/stream/TX fixtures also pass when compiled
in a temporary directory containing their unchanged sources and supporting
headers, with the three new kernel headers overlaid. Historical audit files
and receipts are unchanged. Strict C warnings, ASan and UBSan pass. Strict
checkpatch passes with `MISSING_SIGN_OFF` excluded for this internal draft,
`TYPO_SPELLING` for the inherited `acknowledgement` API spelling, and
`FILE_PATH_CHANGES` because the temporary headers have no upstream maintainer
entry yet. These exclusions are not upstream acceptance.

```sh
cc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined \
  -I/path/to/prepared/linux/drivers/soc/mediatek \
  experiments/2026-10-04-mt6797-stp-task-framing/test-stp.c \
  -o /tmp/gemini-stp-task-test
/tmp/gemini-stp-task-test
rm /tmp/gemini-stp-task-test
KERNEL_PROFILE=mt6797-a53-stp-task-compile ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mt6797-a53-stp-task-compile ./scripts/buildbox fetch-package
```

The full Buildbox build, remote package validator and fetched inventory checks
pass for input commit `0fa95ab0`. All three prepared header hashes match the
host-tested child. The shared codec is compiled through existing WMT callers;
the generic byte parser still has no kernel caller and remains host-tested
only. Configuration is byte-identical to the parent AFE compile profile.
The Linux artifact-provenance fixture passes six positive cases and rejects
28 mutations. Repository checks pass, including all 273 profile series.
No new compiler warning appears; historical patch 0261 whitespace and the
unused CPU rollback callback warning are inherited from the parent build.
No binding or DT content changed, so no additional schema check was run.

No device access, radio operation, boot candidate construction or installation
has occurred. The receipt binds the package to its original input commit;
this later documentation update does not change kernel inputs.
