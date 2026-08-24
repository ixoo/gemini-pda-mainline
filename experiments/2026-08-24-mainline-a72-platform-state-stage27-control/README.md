# Experiment: A72 platform-state probe on the Stage-27 control DT

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-24-mainline-a72-platform-state-stage27-control` |
| Status | `running` — guarded deployment complete; one runtime pending |
| Subsystem | MT6797 Cortex-A72 platform-state source |
| Device variant | Gemini PDA, named project device |
| Date | 2026-08-24 |
| Boot path | retained LK, owner-selected non-primary `boot2` |

## Question or hypothesis

Does the exact `7.1.3-gemini-a72-early` kernel retain the proven Stage-27
serviceability baseline when only the read-only A72 platform-state driver's
probe and resource acquisition are added?

This is the corrected successor to the retired
[physical-source-DT attempt](../2026-08-24-mainline-a72-platform-state-only/README.md).
That attempt was inconclusive because its DT also disabled USB, T-PHY, I2C5,
keyboard, and other working Stage-27 state. This experiment starts from the
byte-exact proven Stage-27 DT instead.

The platform-state probe performs one managed allocation, resolves the existing
SPM syscon, acquires the PWRAP reset handle without asserting or deasserting it,
and maps the named MCUCFG and CCI resources. It performs no register read,
register-data write, reset action, protected call, snapshot, publication,
provider transaction, clock action, owner mutation, or CPU request.

## Provenance and exact delta

- Buildbox package commit:
  `26274db63316bbb24eeb9bfa8de21759da666b9e`.
- Kernel release: `7.1.3-gemini-a72-early`.
- `Image.gz` SHA-256:
  `00992be8c2ccb222c42eecfd92c43b81305f12d756cc2e2a7fc533299e2ce293`.
- Exact proven Stage-27 source DTB SHA-256:
  `7ee8421ea03b604e30e1760f6fb5bc98d4d2566694a9da189326ce2c10e0c806`.
- Derived DTB SHA-256:
  `57e11e4392edfdb9fa695ac3f87b82aad4043bc2a61b78646bf97344bae101fd`.
- Exact serviceability initramfs SHA-256:
  `e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f`.
- Raw Android-v0 candidate SHA-256:
  `70ca589dbfc7649c38648a008e5197702295f396610ee2336fef5325f31b9546`,
  6,909,952 bytes.
- Exact 16 MiB `boot2` payload SHA-256:
  `662e86846e783cf29b13c388f9e88217fe7bd32933eef4f32df86e44def0b16b`.

The DT transformation has exactly three contract additions:

1. add `syscon` to the existing SPM power-controller compatible list;
2. expose the existing watchdog as the one-cell PWRAP reset provider with the
   next previously unused phandle; and
3. add the enabled platform-state node with its SPM, reset, MCUCFG, and CCI
   references.

Removing that node and reversing the two provider properties recovers a
byte-identical sorted semantic DTS to the exact Stage-27 source. The exact
Stage-27 USB controller, T-PHY and primary PHY, I2C5, AW9523, keyboard,
framebuffer, and disabled SCP state are independently gated.

## Safety assessment

CPU8 and CPU9 remain closed by exact `maxcpus=8`. The platform snapshot export
has no caller. The clock and BigiDVFS backends and physical-source observer are
absent from this Stage-27 DT. The runtime probe is read-only and requests no
reboot.

The already authorized installer resolves logical `boot2` from the live GPT,
rejects an active, mounted, ambiguous, wrong-sized, or unwritable target,
checks power and both exact TEE identities, records the predecessor checksum,
creates no redundant backup, writes only the exact 16 MiB candidate, flushes,
requires a matching full-partition readback, and shuts the device down after
success. Primary `boot`, `boot3`, preloader, NVRAM, GPT, and whole-device
writes remain excluded.

## Associated code and procedure

- `scripts/build-provider-dtb.sh` derives the DT twice and proves the reversible
  semantic delta.
- `scripts/build-candidate.sh` performs two independent Android-v0 assemblies
  and two independent padding constructions.
- `scripts/validate-candidate.sh` independently validates package, DT, layout,
  all 32 LK gates, and six negative mutations.
- `scripts/install-boot2.sh` is the source-pinned guarded live-GPT installer.
- `scripts/collect-runtime.sh` pre-arms the USB/netcat observer and leaves a
  successful mainline boot running.
- `scripts/remote-live-probe.sh`, `scripts/validate-runtime.py`, and
  `scripts/test-runtime.py` collect and classify exact live identity, provider
  bind state, serviceability DT state, CPU state, and prohibited effects.

Private candidates and device captures remain below ignored `artifacts/`.
The offline result is recorded in
[`results/offline-candidate-validation-20260824.txt`](results/offline-candidate-validation-20260824.txt).

## Pre-boot decision map

| Unique result | Interpretation | Next action |
| --- | --- | --- |
| Exact USB/netcat identity, Stage-27 state exact, provider bound | Resource-only probe is serviceable | Enable the clock backend alone next |
| Exact USB/netcat identity, Stage-27 state exact, provider unbound | Kernel remains serviceable; one provider resource contract failed | Capture bounded probe status and repair only that contract |
| Changed-ID Gemian before exact mainline identity | With the confounding DT deltas removed, the minimum provider probe/resource boundary is implicated, but no CPU or snapshot action occurred | Add an earlier durable probe-entry/completion discriminator; do not repeat this payload unchanged |
| Neither exact live mainline nor changed-ID Gemian | Observation incomplete | Preserve state and diagnose transport/boot selection without assigning a kernel result |

One owner-selected `boot2` attempt is allowed after the exact candidate is
committed, pushed, deployed, fully read back, and the device is shut down. A
successful mainline result remains running; an identical retry is prohibited
unless it adds a decision-changing independent observation path.

## Observations and conclusion

Offline construction and independent validation pass. The DT derives twice
byte-identically, its reverse proof recovers the exact Stage-27 semantic tree,
the raw and padded candidates reproduce byte-identically, all 32 LK gates pass,
and all six container mutations are rejected. The runtime classifier accepts
the bound and unbound serviceable branches and rejects the inherited seven
provider mutations plus four Stage-27-state mutations.

The exact 16 MiB payload was committed and pushed in signed definition commit
`23f1843a`, then deployed from known-good Gemian. Live GPT resolved inactive
logical `boot2` as `/dev/mmcblk0p30` while root was `/dev/mmcblk0p29`. The
predecessor was the retired confounded payload `012f7eac...a23f`; both TEE slots
matched the expected identity, power was online at 100% and good, both retained
records were exact empty, and no retained-memory write or fresh partition
backup occurred. Write, sync, flush, and full 16 MiB readback produced exact
`662e8684...0b16b`. The device was then cleanly shut down and independently
confirmed unreachable. Sanitized deployment evidence is in
[`results/deployment-20260824.txt`](results/deployment-20260824.txt).

No runtime conclusion is claimed yet. The device is powered off and ready for
one physical `boot2` selection after the USB/netcat collector is pre-armed.
