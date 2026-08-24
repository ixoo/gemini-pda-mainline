# Experiment: A72 platform-state source only

## Status

Exact DT-only candidate reconstructed twice, independently validated, and
accepted as the next boot candidate. Device deployment is pending.

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

## Runtime decision map

| Result | Interpretation | Next action |
| --- | --- | --- |
| USB/netcat plus platform-state bound | First read-only source probe is serviceable | Enable the clock backend alone next |
| USB/netcat but source unbound | Kernel remains serviceable; platform resource acquisition failed | Capture the bounded probe status and repair that source contract |
| Changed-ID Gemian before exact mainline identity | Platform-state enablement is implicated at the live boundary | Audit its exclusive reset/resource acquisition before another boot |

CPU8 and CPU9 remain closed by `maxcpus=8`. One physical selection is allowed;
do not repeat the exact payload without a new observation path.

## Associated code

- `scripts/build-platform-only-dtb.sh`: two-derivation exact DT transformer.
- `scripts/build-candidate.sh`: source-pinned Android-v0 builder.
- `scripts/validate-candidate.sh`: independent package, DT, layout, and
  mutation validator.
- `scripts/install-boot2.sh`: source-pinned guarded `boot2` installer; it
  records the predecessor identity, verifies full-partition readback, and
  shuts down after success.
- `scripts/remote-live-probe.sh`: bounded read-only netcat probe of exact live
  identity and provider isolation.
- `scripts/validate-runtime.py`: accepts serviceable bound and unbound provider
  outcomes while rejecting backend or observer exposure.
- `scripts/test-runtime.py`: positive-branch and mutation coverage for the
  runtime classifier.
- `scripts/collect-runtime.sh`: pre-armed USB/netcat collector; a successful
  mainline boot remains running.

Private artifacts remain below `artifacts/`.
