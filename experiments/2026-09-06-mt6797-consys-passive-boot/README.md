# MT6797 passive CONSYS/WLAN boot slice

## Result

This experiment adds one built-in diagnostic patch for Linux 7.1.3. At late
init it discovers the existing `mediatek,consys-reserve-memory` node and
validates, without mapping or claiming it:

- one compatible node below `/reserved-memory`, with `no-map` and no `reg`;
- exactly 2 MiB `size` and 2 MiB `alignment` properties;
- exactly one 2-cell address/size `alloc-ranges` tuple equal to the frozen
  Gemini allocation range; and
- the initialized reservation's size, alignment, callback state and location.

Only after all checks pass does the private provider publish generation `1`.
The private WLAN client acquires one generation-bound handle and retains a
balanced provider reference. No client-facing symbol or userspace ABI is
added. The immutable effect counters are compile-time zero values with no
increment path.

The duplicate-compatible iterator uses an independent `of_node_get(node)`
reference because the OF iterator consumes its `from` reference. The caller's
node reference is therefore still released exactly once after validation.

The sole success record is:

```text
mt6797-consys-passive: state=BOUND generation=<nonzero> client=wlan-passive power=0 reset=0 remap=0 protection=0 firmware=0 radio=0 dma=0
```

It intentionally contains no physical address, pointer, device identifier,
firmware value, calibration value, radio action or support claim. Validation
failure logs remain `state=UNBOUND` and publish no handle.

## Files and exact inputs

The implementation is [0544-soc-mediatek-add-MT6797-passive-CONSYS-boot-binding.patch](../../patches/v7.1.3/0544-soc-mediatek-add-MT6797-passive-CONSYS-boot-binding.patch).
Its Kconfig and Makefile preimages are the post-0528 Linux 7.1.3 states
identified by patch indices `eecef65` and `29b4525`; the new C file has a zero
preimage. The profile fragment is
`configs/gemini-mt6797-consys-passive.fragment` and the selected series is
`patches/series-mt6797-consys-passive-boot`. The fragment selects the passive
observer and overrides the inherited local version with
`-gemini-consys-passive` so runtime identity is attributable.

The series is an ordered subsequence of the canonical series through the
parent TOPRGU restart patch, followed by this patch. The integrated profile
inherits the complete parent fragment list and appends only the passive
observer/local-version fragment.

## Validation

The focused host fixture is [test_passive_boot.py](test_passive_boot.py). It
models metadata refusal, publication ordering, generation/lifetime checks,
zero-effect counters, log privacy, OF reference ownership and profile
isolation. Its `check()` oracle remains active under `python3 -O`; it does not
emulate Linux, firmware, Wi-Fi, a device or hardware support.

Executed in this handoff:

```text
python3 experiments/2026-09-06-mt6797-consys-passive-boot/test_passive_boot.py    PASS cases=49
python3 -O experiments/2026-09-06-mt6797-consys-passive-boot/test_passive_boot.py PASS cases=49
git apply --stat patches/v7.1.3/0544-soc-mediatek-add-MT6797-passive-CONSYS-boot-binding.patch PASS
git diff --check PASS
managed Linux 7.1.3 strict Checkpatch: 0 errors; 4 warnings; 3 checks
```

The style diagnostics are the intentional synthetic patch's missing
MAINTAINERS update, one commit-message wrap warning, two split-format-string
warnings needed for a single bounded record, and three continuation/style
checks. Independent Sol review accepted them as non-blocking for this internal
experiment; they remain upstream cleanup alongside real authorship and
maintainer review.

After the compile escalation and repaired integration, Buildbox applied all
531 patches from exact clean pushed revision
`f9981eaf63381a558f77be251da4c2320cb4321b`, compiled and linked the passive
observer, and validated package inventory
`7c43a80cce28a15dc70306e3b8c225b537f1589eec4ac7411a46d422d705401c`.
The immutable facts are in [the Buildbox receipt](results/buildbox-f9981eaf.txt).
No VM build, device boot, candidate construction or hardware access occurred.
Compilation does not establish Wi-Fi or hardware support.

## Handoff limits

The patch deliberately stops at passive `BOUND`. It does not add power/reset
ownership, MMIO or reserved-memory mapping, resource requests, firmware
loading, AP-DMA, cfg80211/rfkill, radio activation, removal, suspend/resume,
recovery or a Device Tree change. The device readiness state remains
`preparing` pending an exact candidate, collector and independent packet
review; no physical action is admitted by this record.
