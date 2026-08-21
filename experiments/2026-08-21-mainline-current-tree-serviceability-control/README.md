# Current-tree serviceability control

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-21-mainline-current-tree-serviceability-control` |
| Status | complete; exact current-tree serviceability control passed |
| Subsystem | arm64 boot, USB/netcat serviceability, DA921x read-only path |
| Device variant | Gemini PDA x27, named project unit |
| Date(s) | 2026-08-21 |
| Investigator(s) | Julien Etienne, Codex |
| Tracking issue | Gate 7 / CPU8 prerequisite localization |

## Question or hypothesis

Does the current canonical Linux 7.1.3 tree remain serviceable when built from
the last runtime-proven `da921x-same-value-write` configuration lineage, with
the action path and every protected-readback/clock-entry path explicitly
disabled, and paired with the exact successful three-window DT resource
contract?

This is not a repeat of padded candidate `85dbd8d0...`: the current tree adds
later canonical patches and the control has a unique release while compiling
out the old same-value trigger. It is also not a clock-entry retry: the clock
backend and its shared retained writer are absent from the resolved
configuration.

## Provenance and environment

- Kernel release: `7.1.3-gemini-service-ctl`
- Repository build commit: `27622dfea13e042bd82f036c50664d3b978aee11`
- Kernel source: manifest-pinned Linux 7.1.3 plus canonical `patches/series`
  through patch `0326`
- Build profile: `da921x-current-service-control`
- Build backend: Buildbox only, from an exact clean pushed commit
- Configuration foundation: exact manifest fragment sequence of
  `da921x-same-value-write` plus the final control fragment
- DT contract: retain named `cspm`, `scp-cfg`, and `devapc-ao` windows from
  successful candidate `85dbd8d0...`
- Boot path: guarded live-GPT logical `boot2` only

Buildbox produced Image.gz
`9aa5c9ae497314b7ab089ccf6aa7d2cf1bb2ae9239145456603f08439829a9d6`.
The exact derived DTB is
`b638674b9be209219d51b7dd02538f7a0bc8b402bab7336188cb95011cd912dd`.
The admitted raw Android-v0 candidate is
`691ff883f05158c9a62d6629befef93f54ba14e51ff4ed5d8ea97678f2fa5094`;
its exact 16 MiB boot2 image is
`7084f2ee87af103dfcf1dfad9956f54c2a9df8d37b5f6d0388ba45464d8d52a3`.

## Safety assessment

The profile explicitly compiles out the same-value action, protected-clock
backend, BigiDVFS backend, protected-readback observer, shared protected
retained writer, and both of its experiment modes. It retains the previously
successful read-only provider/preflight, I2C6 observation, USB/netcat,
keyboard, CPU0--7, and CPU8/9 veto paths. Runtime tooling must send no action
token. There is no protected call, regulator-data write, CPU request, retry,
owner transition, reset, or automatic power action in the tested path.

Any candidate installation must use the standing guarded `boot2` workflow:
resolve the live GPT, require inactive/unmounted exact target and stable power,
record the predecessor without a new backup, fit and pad exactly, write,
sync/flush, match a full readback, and shut down cleanly without rebooting.

## Associated code

- `configs/gemini-current-service-control.fragment`: final explicit closures
  and unique release
- `kernel/manifest.json`: named Buildbox profile
- `scripts/validate.py`: exact profile, fragment, and canonical-series audit
- `scripts/build-serviceability-dtb.sh`: pinned current-package DT derivative
- `scripts/build-candidate.sh`: pinned candidate construction and replay
- `scripts/test-candidate.py`: independent package, DT, container, and mutation
  validator
- `scripts/install-boot2.sh`: guarded live-GPT boot2 installation and shutdown
- `scripts/collect-runtime.sh`: pre-armed exact USB observer, read-only probe,
  pass-gated native reboot, and changed-ID Gemian return
- `scripts/validate-runtime.py`: exact serviceability classifier
- `scripts/test-runtime-tools.py`: offline safety and attribution mutations
- `contract.json`: frozen question, safety gates, and decision table

The Buildbox package and candidate passed offline validation. Guarded boot2
installation and its full readback passed, and the device was shut down. The
exact USB runtime attempt remains pending; its collector must be armed before
the one physical selection.

## Procedure

1. Validate the exact manifest/profile definition and all manifest-selected
   series invariants.
2. Commit and sign the definition, push it to the exact project origin, and
   leave the worktree clean.
3. Build that exact commit only with
   `KERNEL_PROFILE=da921x-current-service-control ./scripts/build-kernel --backend buildbox`.
4. Fetch only the validated package, pin every package identity, and construct
   the exact three-window DT derivative and Android-v0 candidate twice.
5. Independently reject identity, DT-resource, closure, CPU, and container
   mutations before admitting one boot candidate.
6. Install once to guarded inactive logical `boot2`, verify the full readback,
   and shut down.
7. Arm the exact collector before one physical selection. If exact mainline
   USB/netcat appears, verify release, model, CPU masks, keyboard, read-only
   provider state, zero action path, and one native return to changed-ID
   Gemian. If no exact interface appears before automatic return, stop without
   repetition and localize within the current tree/config boundary.

## Observations

The clock-node-disabled predecessor returned automatically without exact USB.
Changed-ID Gemian recovered empty pstore, four exact empty retained slots, the
known generic `last_kmsg`, and unchanged boot2. That result is `neither` and is
not repeated here.

The exact clean pushed definition commit built successfully on x86_64
Buildbox. The package resolved `CONFIG_NR_CPUS=512`, contains ten DT CPU nodes,
and forces `maxcpus=8`; those are separate limits. Two DT constructions, two
raw assemblies, and two padding constructions were byte-identical. Independent
validation passed all 32 LK gates and rejected 15 deliberate DT mutations.
The clock-entry/shared writer, protected-readback paths, BigiDVFS backend, and
same-value action are not enabled. No device access occurred during this
validation.

Guarded deployment resolved logical boot2 as inactive `/dev/mmcblk0p30` while
Gemian used `/dev/mmcblk0p29`. It replaced predecessor
`fc2a9a1a...30bf`, synchronized and flushed the write, matched the full 16 MiB
readback to `7084f2ee...d52a3`, and confirmed clean shutdown. No fresh backup,
reboot request, or write to another partition occurred.

The observer was armed before the single physical selection and detected the
exact USB interface. Its first read-only probe captured the exact release and
all required serviceability values, but the DT model property lacked a newline
and merged with the following field. The validator returned
`rejected-attribution=model-mismatch` and correctly sent no reboot. An
offline-tested newline correction then reran the same read-only probe on the
same mainline boot ID; this was not a second boot selection. It classified
`serviceable-control-pass`: CPUs 0--7 were online, CPUs 8--9 offline, USB,
keyboard, and one DA921x client were present, the same-value attribute and all
three experimental backend-device classes were absent, no block filesystem was
mounted, and every action request remained `none`.

Only after that exact pass, the collector sent one native reboot. Gemian
returned with a changed boot ID and exact boot2 remained
`7084f2ee...d52a3`.

## Analysis

The predecessor changed DT node population but retained the clock-entry Image
and shared checkpoint, so it could not distinguish the current
Image/configuration path from the experimental writer. This control removed
that writer and restored the complete serviceability DT contract with a new
current-tree Image. Its pass proves the canonical current tree, Android-v0
container, serviceability DT, read-only DA921x provider, USB, and keyboard are
viable together. It localizes the stopped clock-entry lineage to its
experimental writer/configuration boundary rather than to a generic current-
tree or boot-container regression. It does not prove why returned retained-RAM
slots were empty.

## Conclusion

Exact candidate `7084f2ee...d52a3` passed its one physical selection and
read-only serviceability oracle. The current-tree CPU0--7 foundation is
restored. CPU8/9 remain deliberately closed, and no clock-entry checkpoint,
protected transport, regulator-data write, or CPU admission claim is made.

## Follow-up

Isolate the manual checkpoint mechanism on this exact serviceable base without
enabling the clock node or either protected transport. Only after that
independent control passes may clock-backend population/probe entry resume.
CPU8 and CPU9 remain closed throughout.
