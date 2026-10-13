# Compile 38 — owned-BSS scheduling and shared-control gate (0184)

Source reviewed and compiled; no candidate-34 hardware result. Native ND3 is
a separate input/profile and is first in the device queue.

- Kernel input: `1edcbfb315f1464e3319aff0be1133b4e948f8e5`.
- Profile: `mt6797-a53-wifi-phase-b-compile`, 32 jobs on the managed backend,
  clean pushed checkout, experiment selector unset.
- Reviewed logical 0184 format-patch:
  `73ead80a98fd22a8b1d9ddb712682b6afdd77df51dd8acce8a74454f01deb742`.
- Package inventory:
  `074414c5744a6a45023c136ac3537321c5738b118d4a5a4935b4ad81d613d59e`.
- Image.gz: `28b1f4c88a931f015d14f350d2ab51ee631f58f76d33850ba24d33b0d726caa4`.
- Resolved config:
  `975f8703e4061d8676dff6fc7835312f949f9ce3317b3fd900a3219cce0c312d`,
  unchanged from the preceding Phase-B candidate.
- Selected series: 682 canonical-order patches, including 0182/0183/0184,
  excluding native 0181/0185. Package inventory/provenance validation and fetch
  passed; modules disabled, 123 DTBs, no device action.
- Built mac.c:
  `fc356246a0b96a80911ffd6d8b9c463b9140ca6c62e23538f2e1a2ee11ba1a7a`,
  byte-identical to exact replay of the reviewed patch on its C33 parent.

Actual handler and extracted worker-dequeue/close/rearm blocks pass ASan/UBSan
fixtures against this built source, including valid fake hw/wiphy objects in
the control handler fixture. Strict notification shape, repeats/phases,
quota-as-noncredit, before-dequeue retention, publication with mocked lock held,
close from woken state and healthy reset release are covered. Tests do not
prove kernel concurrency, full-worker RX servicing or firmware semantics.
Repository, staged whitespace/syntax/sensitive-data and manifest gates passed.
Actual format-patch checkpatch has no warnings and only the standing internal
archive missing-signoff exception; no DCO is fabricated. DT schemas and device
tests were not run for this source-only MAC change.

## Correctness/performance boundary

The shared queue retains management/EAPOL cap 3 / 3*2304 and data cap 8 / 8*1550.
The conservative stop threshold and low-water wake use shared control admission
headroom in every phase, including DATA. This can reduce data queue depth and
throughput; it is not throughput completion. Direct management callbacks do not
all serialize, so exceptional hard-cap refusals remain honest unsent drops,
not frames falsely described as retained or ACKed. Reserved deauth stays in the
same queue; no software-unsent TC4 refund or quota-as-credit is introduced.

Old diagnostic lifetime budgets, scan notification limits, general IRQ/DMA,
rekey/reuse, clean-profile sustained operation and diagnostic retirement remain
work toward the full maintained Wi-Fi goal. Compilation is not that goal.

## Proactive candidate/runtime preparation

`build-candidate-34.py` reuses the frozen C32 successor compositor with only
this exact kernel/package/Image.gz pin rebound. The custodian supplies private
C32 parent inputs and returns the real six-file candidate receipt. Configuration,
DT and the private 64-member RAM root are reused byte-identical; no native
release/arm flag enters this candidate. No receipt or deployment checksum is
invented here.

`prepare-runtime-35.py` already targets that exact build/package and fresh
`wifi-phase-b/session-35`/`capture-35` roots, preserving the reviewed two-lifetime
join script and finite helper/quiescence/recovery limits. It refuses until the
real candidate-34 receipt is published. Exact installer/capture/session/runtime
receipt pins follow that receipt, not speculative hashes. The installed
predecessor must be pinned from the completed ND3 device outcome and freshly
verified at later live-GPT deployment; ND3 has not been installed at this record.

`passive-host-35.py` and `laptop-session-35.py` prepare the actual fresh host
namespace and two-cycle helper identity, preserving private-source remapping
and requiring C32's supplicant/wpa_cli members when selecting the new receipt.
The main session refuses until the real runtime35 receipt copy is published;
these adapters are not yet device-ready. Host namespace tests make no candidate,
deployment or device claim. Capture/installer binding and full private dry run
remain receipt-dependent; no incomplete adapter is an instruction to install.

A later bounded test asks whether valid owned-BSS absence notifications can
hold/resume the second join's unsent ownership without the R34 local refusal.
Observe exact notifications, queue/TX completion and healthy-rearm chronology;
retain negative outcomes and do not infer sustained/rekey/replay support from
two lifetimes. This does not require an additional observer-only boot.
