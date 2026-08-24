# Experiment: A72 physical-source pre-capture ledger

## Status

Runtime attempt 1 rejects this successor before its first `probe-enter`
checkpoint. The host saw a GNU/Linux USB device but no Gemini network/netcat
interface, and the owner then observed a delayed automatic return to Gemian.
Changed-ID recovery found the exact candidate still on boot2, pstore empty,
and both owned first-dmesg records exact empty. The result does not establish
whether the observer probe never ran or its first checkpoint refused. Because
allocations and all three source-device acquisitions follow a successful first
checkpoint, they were not reached by the candidate's successful-path ledger
order.

This non-identical successor moves the two qualified first-dmesg records
earlier and intentionally makes no physical-source capture:

1. `probe-enter` is the first physical-source observer probe operation;
2. `sources-held` follows successful acquisition of the bound platform-state,
   protected-clock, and BigiDVFS source devices.

After record 2, the probe releases all three references and returns success.
It does not register the direct source or call platform, DA921x, protected
clock, BigiDVFS, publication, owner mutation, or CPU-request paths.

## Decision table

| Retained result | Interpretation | Next action |
| --- | --- | --- |
| neither | Observer probe did not enter, or the first-dmesg checkpoint refused | Move before observer probe/init without repeating this artifact |
| `probe-enter` only | Probe entered but all three bound source devices were not acquired on its first attempt | Split the three acquisition boundaries |
| `probe-enter` + `sources-held` | All three source devices were bound and retained; failure in the rejected candidate lies inside its capture path | Isolate platform, DA921x, and clock returns before reintroducing BigiDVFS |
| malformed or foreign record | Attribution failed | Reject without path inference |

## Safety and build contract

- At most two short writes use only first-dmesg records 1 and 2 through the
  already-qualified all-ones/empty-header, payload-before-metadata,
  signature-last, barrier, and full-readback writer.
- There is no overwrite, clear, retry, partition write, protected/secure call,
  MMIO snapshot, I2C transaction, owner mutation, CPU request, reset, reboot,
  or power operation in the new probe path.
- One canonical patch follows `0356` and is generated on Buildbox from the
  exact integrity-verified managed source. The patch is experiment-only and
  retains a synthetic, non-certifying author with no DCO sign-off.
- Buildbox compile, package checksums, linked/excluded symbol review, candidate
  assembly, and independent Android-v0 validation must pass before deployment.

## Next action

Exact pushed commit `112bbdc8c5fd09da1a2aad5ee234dc8bf4fba7c4`
generated the one-patch delta on Buildbox from the integrity-verified managed
source through `0356`. Source validation, the exact three-file boundary,
byte-identical replay, and strict checkpatch with zero errors, warnings, or
checks pass. The fetched patch is byte-identical to canonical `0357`; see the
[generation receipt](results/buildbox-generation-112bbdc8.txt).

Compile the isolated profile on Buildbox. No native VM kernel build is
authorized, and the experiment remains `boot_candidate=false` until package,
binary, DT, and independent container gates pass.

The first build at exact commit
`e686b47f16c3db284980cb8db850bfa8df807256` stopped during `defconfig`
before compilation: Kconfig rejects reciprocal negative dependencies between
the old physical-source mode and the new pre-capture mode. No package or
candidate was produced. The [stopped-attempt receipt](results/build-attempt-1-recursive-kconfig-dependency.txt)
selects a one-line follow-up: remove only the old mode's reverse dependency.
The new mode still requires the old mode off, so exclusivity remains one-way
without a cycle. Runtime source and the two checkpoint boundaries are
unchanged. Generate and admit that exact Kconfig-only patch before retrying the
Buildbox profile.

Exact commit `3488562f545579e6c82e4e6b57d372563b92498e` generated the
Kconfig-only follow-up on Buildbox from the managed source through `0357`.
Parent integrity, one-file/one-deletion validation, byte-identical replay, and
strict checkpatch with zero errors, warnings, or checks pass. The fetched bytes
are canonical patch `0358`; see the
[fix-generation receipt](results/buildbox-kconfig-fix-generation-3488562f.txt).

The retry at exact commit
`bc1d7fecb5f8c485e4d39b89bbdec9e1bcf81fff` passed configuration and entered
compilation, then stopped because the two guarded exits added by `0357` target
`put_bigidvfs` while the existing release statement has no label. No package
or candidate was produced. The
[second stopped-attempt receipt](results/build-attempt-2-missing-cleanup-label.txt)
selects one guarded label immediately before the unchanged BigiDVFS, clock,
platform, and snapshot release chain. Generate and admit that exact
control-flow-only follow-up before another Buildbox compile.

Exact pushed commit `183269b26bb809f44fd212adac92c21fe83f43b7`
generated the control-flow-only follow-up on Buildbox from the managed source
through `0358`. Parent integrity, the exact one-file/three-line boundary,
byte-identical replay, and strict checkpatch with zero errors, warnings, or
checks pass. The fetched bytes are canonical patch `0359`; see the
[control-flow fix receipt](results/buildbox-control-flow-fix-generation-183269b2.txt).
The next action is to retry the unchanged isolated profile through `0359`.

The retry from signed exact commit
`94b3e6a12d0701ddedaa442a794b08b3563130f5` compiled and passed the
Buildbox package validator. The fetched package has release
`7.1.3-gemini-a72-precapture`; see the
[kernel build receipt](results/buildbox-kernel-94b3e6a1-pass.txt).
Offline preassembly with the unchanged serviceability ramdisk passes all 32 LK
gates and fixes the raw and padded candidate identities. The next action is to
run the pinned builder and a separately pinned independent validator before
any device access.

Assembly attempt 1 from definition `e0ec34f0` stopped before serialization
because one inherited builder assertion still named the predecessor's local
version. No candidate or device action occurred. The
[stopped assembly receipt](results/candidate-assembly-attempt-1-localversion-gate.txt)
selects the same exact local-version correction in both the builder and the
independent validator before retrying.

Assembly attempt 2 from corrected definition `3e1300fa` produced the exact raw
and padded identities fixed above. The separate validator passed the complete
package inventory, source pins, configuration and linked/excluded symbols,
unique/absent record inventory, unchanged physical-source DT wiring,
independent padding, and all 32 LK gates. The
[candidate validation receipt](results/candidate-validation-6397a032-pass.txt)
promotes this artifact to `boot_candidate=true`.

Before the one physical selection, the exact kernel/DT/config hypothesis,
unique records, and decision branches are fixed in the
[predeployment statement](results/predeployment-hypothesis-20260824.txt).
The next action is a guarded live-GPT `boot2` deployment with full-partition
readback followed by clean shutdown, never an automatic reboot.

Deployment attempt 1 resolved inactive `boot2` from the live GPT, confirmed
both owned records exact empty, wrote the exact padded candidate, synchronized
and flushed it, matched the full-partition readback, and cleanly shut the
Gemini down without reboot. See the
[sanitized deployment receipt](results/deployment-1-write-readback-shutdown-20260824.txt).

Runtime attempt 1 exposed a physical GNU/Linux USB device but no usable
Gemini USB network interface or netcat endpoint, then returned automatically
to Gemian after the bounded observation. Changed-ID recovery matched the exact
boot2 candidate and found both records exact empty with zero-length payloads;
pstore was mounted and empty. The
[runtime receipt](results/runtime-attempt-1-before-probe-enter-20260824.txt)
therefore rejects this artifact without claiming observer probe entry or any
source acquisition. An identical retry is disallowed.

The selected next diagnostic puts record 1 in the observer driver-init path
before `platform_driver_register()` and record 2 at the first probe operation,
then exits without allocations or source acquisition. This distinguishes
pre-init failure from registration/probe failure while keeping capture,
provider transactions, publication, owner mutation, and CPU requests closed.
