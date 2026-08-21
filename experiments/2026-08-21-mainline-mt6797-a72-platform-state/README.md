# Experiment: mainline MT6797 A72 platform-state source

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-21-mainline-mt6797-a72-platform-state` |
| Status | deterministic Buildbox generation input; patches pending |
| Subsystem | MT6797 A72 CCI/SPM/TOPRGU/DCM observation |
| Device variant | Gemini PDA contract; hardware-free implementation phase |
| Date | 2026-08-21 America/New_York |
| Tracking issue | Roadmap Gate 7, direct A34 recovery state |

## Question

Can mainline expose one default-off, typed, read-only snapshot of the exact
platform fields selected by the ownership audit, without adding a CCI/SPM/DCM/
TOPRGU write, polling, A34 caller, lifecycle publication, or CPU operation?

## Provenance and safety

- Repository parent: signed and pushed audit commit
  `cdf5dbe9e1f9331eb261b705f22a52b871a0bc94`.
- Kernel parent: pinned Linux 7.1.3 source state
  `905fb7f5ead29cbe65eaf7f66e41433aea417c2ee15d751ebda6ddf79f19ad8e`
  through canonical patch `0307`.
- Decision authority: the
  [CCI/platform-state ownership audit](../2026-08-21-mainline-a72-cci-platform-state-owner-audit/README.md).
- Generation and later compilation use Buildbox only. No kernel source tree is
  copied to or from Buildbox.

The implementation is default-off. Patch generation performs no build or
device action. The source contains no register/reset write, polling loop, PSCI
call, CPU request, A34 caller, lifecycle publication, boot candidate, or boot2
write.

The passing repository-side syntax and scope receipt is
[`results/design-validation-20260821.txt`](results/design-validation-20260821.txt).

## Generation attempts

The first Buildbox generation attempt used repository commit `cfb17745c9a1d4dd7b8e8ce13b08642ec0bd78e3`.
All parent source-state and file-hash gates passed. Generation then stopped
before patch export because Python `dedent()` removed the leading tab from the
exact DTS node edit anchor. The strict one-match guard correctly rejected the
zero-match edit; no patch package, build, or device action resulted. The
sanitized receipt is
[`results/buildbox-generation-attempt-cfb17745.txt`](results/buildbox-generation-attempt-cfb17745.txt).

The edit now expresses both DTS node bodies as explicit tab-preserving string
literals while retaining the exact one-match guard.

The second Buildbox attempt used repository commit
`5866aeff5039c253780771039fb88405b0d50b59`. It generated and replayed the
two initially planned patches, and the semantic source and patch validators
passed. Strict checkpatch then rejected the combined platform patch because
the DT binding was not isolated and because of nine style checks. No package
was exported and no build or device action occurred. The sanitized receipt is
[`results/buildbox-generation-attempt-5866aeff.txt`](results/buildbox-generation-attempt-5866aeff.txt).

The series is therefore split into four logical patches—watchdog accessor,
binding, source driver, and DT description—and every reported style check is
fixed in the source rather than ignored.

## Selected change

Patch `0308` adds the standard reset-controller `.status` callback to
`mtk_wdt`. It reads `WDT_SWSYSRST` under the same spinlock used by assert and
deassert and returns the selected logical bit. It performs no reset action.

Patch `0309` adds the binding, patch `0310` adds the default-off
MT6797-specific source, and patch `0311` adds its still-disabled DT node. The
source provides:

- named `mcucfg` and `cci` DT resources;
- the existing SPM syscon and TOPRGU PWRAP reset owner;
- two immediate bounded samples with no loop or retry;
- rejection of CCI change-pending (`-EBUSY`) and A72-field movement
  (`-EAGAIN`);
- a destination that remains all-zero on error; and
- one valid typed record on success.

General SPM `PWR_STATUS` words are captured as raw context but excluded from
the movement predicate. The predicate covers both CPU-status words, MP2
cluster and CPU8/CPU9 controls, external Buck-B isolation, PWRAP reset, the
defined low seven MP2 DCM bits, and the CCI MP2 request bits. CCI status bit 0
must be clear around both port reads. Upper opaque bits remain raw evidence.

The DT node stays disabled. The old disabled probe-time A72 observer node is
replaced to avoid a duplicate unit address, and the obsolete Gemini deletion
is removed; that does not enable either driver.

## Reproducibility

Repository validation:

```sh
python3 experiments/2026-08-21-mainline-mt6797-a72-platform-state/scripts/validate.py
```

After committing and pushing a clean input:

```sh
./scripts/buildbox generate-mt6797-a72-platform-state-patches
./scripts/buildbox fetch-mt6797-a72-platform-state-patches
```

The generator verifies exact parent source hashes, uses a temporary reduced
Git tree, produces four normal `git format-patch` files under a clearly
synthetic non-certifying experiment identity, replays them byte-for-byte, and
runs strict checkpatch. It exports only a checksum-covered patch review.

## Current conclusion

The deterministic source and generation boundary are ready for Buildbox
review. No compile, runtime, hardware, or device claim is made yet. A34 and
CPU8/CPU9 remain closed.
