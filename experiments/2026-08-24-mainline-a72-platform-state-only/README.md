# Experiment: A72 platform-state source only

## Status

Exact DT-only candidate reconstructed twice, independently validated, and
accepted as the next boot candidate. The first deployment preflight safely
stopped before the partition writer because the preceding successful control
left its two exact retained records. After byte-attributing that pair, the
guarded `boot2` write, full readback, and clean shutdown all passed. Runtime
attempt 1 then returned automatically to a changed-ID Gemian boot without ever
exposing the mainline USB interface or netcat endpoint. A post-result semantic
DT audit found that this was not a one-variable derivative of the proven
Stage-27 control: among many unrelated differences, it disabled the USB
controller and T-PHY. The platform-state provider is therefore not implicated
by this attempt; the runtime result is inconclusive.

## Hypothesis

The exact `7.1.3-gemini-a72-early` kernel remains serviceable when the first
read-only physical-source provider, `mediatek,mt6797-a72-platform-state`, is the
only source enabled in the exact current physical-source DT. The clock backend,
BigiDVFS backend, and physical-source observer are explicitly disabled.

The Stage-27 control proved this exact kernel through `/init` and USB/netcat.
The failed physical-source DT enabled three providers at once. This derivative
isolates the first provider's probe and resource acquisition without invoking
its snapshot callback and without a register-data write, protected call,
observer registration, publication, owner mutation, or CPU request.

## Exact inputs and delta

- Kernel package commit:
  `26274db63316bbb24eeb9bfa8de21759da666b9e`.
- Kernel release: `7.1.3-gemini-a72-early`.
- `Image.gz` SHA-256:
  `00992be8c2ccb222c42eecfd92c43b81305f12d756cc2e2a7fc533299e2ce293`.
- Source physical DTB SHA-256:
  `fe67420ca4e2955a73a4a3f2e442af3534b621820cf77ae035be9bf98756425d`.
- Derived platform-only DTB SHA-256:
  `8e806c5305b6a2808fab59d3a25739d39cd3196a3498a1af21136dd7221923e1`.
- Serviceability initramfs SHA-256:
  `e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f`.
- Raw Android-v0 candidate SHA-256:
  `f3210fb38f9d3d5a61e23d60dc7f9d65b05b0a08cd5ef15033786a4f1bc50aff`,
  6,909,952 bytes.
- Exact 16 MiB boot2 payload SHA-256:
  `012f7eac6884e65baab075ef286929f610a63f2ea065eba45865bd046492a23f`.

The DT change is exactly three `status` values relative to the source physical
DTB: clock backend, BigiDVFS backend, and observer become `disabled`;
`a72-platform-state@10222000` remains `okay`. No kernel build is required or
authorized, and no native VM build is used.

Offline validation passed all 32 LK/container gates and rejected all six
independent mutations. Two DT derivations and two candidate constructions were
byte-identical. The exact 16 MiB payload is therefore eligible for the standing
guarded `boot2` deployment workflow.

The installed 16 MiB `boot2` payload read back as
`012f7eac6884e65baab075ef286929f610a63f2ea065eba45865bd046492a23f`.
The predecessor was the proven Stage-27 control, no fresh partition backup was
created, and the device was confirmed unreachable after the requested clean
shutdown.

## Runtime decision map

| Result | Interpretation | Next action |
| --- | --- | --- |
| USB/netcat plus platform-state bound | First read-only source probe is serviceable | Enable the clock backend alone next |
| USB/netcat but source unbound | Kernel remains serviceable; platform resource acquisition failed | Capture the bounded probe status and repair that source contract |
| Changed-ID Gemian before exact mainline identity | Only attributable if the serviceability DT is otherwise identical | Audit the exact DT delta before assigning a provider result |

CPU8 and CPU9 remain closed by `maxcpus=8`. One physical selection is allowed;
do not repeat the exact payload without a new observation path.

This experiment is attributed by exact live USB/netcat identity, not by the
early-initcall records: its kernel writes the same record pair as the successful
Stage-27 control. The installer therefore accepts only either two byte-exact
empty 4 KiB records or the byte-exact known Stage-27 `pure-init`/`core-init`
pair. Any other retained content still aborts before partition inspection or
writing. No retained-memory write or clear is performed.

## Runtime result

The observer was armed at `2026-08-24T22:56:33Z`, before the owner selected
`boot2`. It recorded no mainline USB topology change and no netcat capture, then
classified `no-mainline-network-before-changed-Gemian-return`. Direct SSH
confirmed Gemian `3.18.41+`, root `/dev/mmcblk0p29`, and a changed boot ID
`3dd69469-8429-4c1a-aa9b-cdd4a942c47a`. The owner's automatic-reboot report is
corroborating only.

The candidate DT had `/usb@11271000`, `/t-phy@11290000`, and its primary USB
PHY disabled while the proven control had all three `okay`. It also disabled
the previously live I2C5, GPIO expander, and keyboard nodes, removed the chosen
framebuffer and SCP node, and added other current-tree contracts. Therefore no
USB was expected from this DT even if `/init` ran. This does not prove a
platform-state probe failure or a CPU request: `maxcpus=8` remained in force
and the observer, clock, and BigiDVFS nodes were disabled.

This payload is retired and must not be repeated. The next discriminator must
start with the byte-exact proven Stage-27 DT and add only the minimum
platform-state node plus its SPM-syscon and watchdog-reset provider contracts.

## Associated code

- `scripts/build-platform-only-dtb.sh`: two-derivation exact DT transformer.
- `scripts/build-candidate.sh`: source-pinned Android-v0 builder.
- `scripts/validate-candidate.sh`: independent package, DT, layout, and
  mutation validator.
- `scripts/install-boot2.sh`: source-pinned guarded `boot2` installer with the
  exact retained-pair attribution gate; it records the predecessor identity,
  verifies full-partition readback, and shuts down after success.
- `scripts/remote-live-probe.sh`: bounded read-only netcat probe of exact live
  identity and provider isolation.
- `scripts/validate-runtime.py`: accepts serviceable bound and unbound provider
  outcomes while rejecting backend or observer exposure.
- `scripts/test-runtime.py`: positive-branch and mutation coverage for the
  runtime classifier.
- `scripts/collect-runtime.sh`: pre-armed USB/netcat collector; a successful
  mainline boot remains running.
- `results/post-runtime-dt-attribution-audit-20260824.txt`: exact reason the
  attempted runtime cannot be attributed to the platform-state provider.

Private artifacts remain below `artifacts/`.
