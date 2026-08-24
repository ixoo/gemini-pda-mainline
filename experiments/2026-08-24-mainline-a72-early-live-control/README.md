# Experiment: A72 early-initcall live DT control

## Status

Exact candidate constructed twice and independently validated. All 32 LK gates
and six negative structural mutations passed. Guarded deployment and one live
USB/netcat observation are pending.

## Hypothesis

The exact `7.1.3-gemini-a72-early` kernel reaches `/init` and the established
USB/netcat service when its appended DTB is replaced with the exact Stage-27
DTB already proven serviceable on this Gemini. The kernel, configuration,
initramfs, load addresses, command line, early-initcall ledger, and CPU policy
remain unchanged; only the appended DTB changes.

A live capture of the exact kernel proves execution through `/init` before any
automatic reboot or later Gemian initialization can erase retained state. It
also looks only for the three fixed `GAEI-20260824-A` records in pstore and
dmesg; it never captures unrestricted dmesg or command-line data. If the exact
mainline identity is not observed before a changed-ID Gemian return, the
attempt is nonserviceable at this observation boundary.

## Exact inputs

- Buildbox repository commit:
  `26274db63316bbb24eeb9bfa8de21759da666b9e`.
- Kernel release: `7.1.3-gemini-a72-early`.
- `Image.gz` SHA-256:
  `00992be8c2ccb222c42eecfd92c43b81305f12d756cc2e2a7fc533299e2ce293`.
- Runtime-proven Stage-27 DTB SHA-256:
  `7ee8421ea03b604e30e1760f6fb5bc98d4d2566694a9da189326ce2c10e0c806`.
- Serviceability initramfs SHA-256:
  `e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f`.
- Raw Android-v0 candidate SHA-256:
  `32ff42b3e8ba07e5b0267b521118f906aa27bd737613ae76a119961d3acc9e0d`,
  6,909,952 bytes.
- Exact 16 MiB boot2 payload SHA-256:
  `070e0ff4b019dd35e91ba91413b9ae958cf5e71e3573ed81bc9dd7d1cf3cc4ef`.

No kernel compilation is required: this is an exact recontainer of a fetched,
validated Buildbox package. No native VM build is authorized or used.

## Safety and decision map

The kernel retains the prior fail-closed maximum of two short retained-RAM
write attempts. It performs no observer registration, allocation, source
lookup, platform/provider snapshot, clock or BigiDVFS call, provider
transaction, publication, owner mutation, or CPU request. CPU8 and CPU9 remain
closed by `maxcpus=8`.

The only storage mutation is the standing-authorized, live-GPT-resolved
inactive logical `boot2` write. The installer records but does not freshly back
up the predecessor, requires exact target and power gates, performs a complete
padded write and full readback, and shuts Gemian down after success. It never
reboots automatically.

| Live result | Interpretation | Next action |
| --- | --- | --- |
| Exact release and USB/netcat service | Current kernel reached `/init` with Stage-27 DTB | Audit current-vs-Stage-27 LK-sensitive DT delta and select one minimal repair |
| Same plus pure/core records | Early ledger also committed both checkpoints | Preserve the live record as ordering evidence |
| Same plus pure/refusal | Pure init ran; primary record path refused | Localize the primary refusal without another serviceability control |
| Same with no exposed record | Serviceability proven; live pstore is not a positive ledger oracle | Continue from the DT control, not the missing record |
| Changed-ID Gemian before exact USB identity | No exact mainline serviceability observation | Use the observer journal; do not infer from screen color or reboot timing |

One physical selection is permitted. Do not repeat an identical payload
without a new independent observation path.

## Associated code

- `scripts/build-candidate.sh`: source-pinned two-construction Android-v0
  builder.
- `scripts/validate-candidate.sh`: independent serialization, package, config,
  marker, DTB, and mutation validator.
- `scripts/install-boot2.sh`: source-pinned guarded boot2 installer.
- `scripts/remote-live-probe.sh`: bounded read-only netcat probe; no reboot.
- `scripts/validate-runtime.py`: exact live identity and early-record
  classifier.
- `scripts/collect-runtime.sh`: pre-armed USB observer and netcat collector;
  it leaves a successful mainline boot running.

Private captures and the candidate remain below ignored `artifacts/` paths.
