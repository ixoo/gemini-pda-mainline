# Experiment: Gauss — exact D3 discriminator on the Fermi baseline

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-28-da9214-gauss` |
| Status | `complete; attempt 1 passed the exact gated one-shot` |
| Subsystem | Legacy DA9213/DA9214/DA9215 register contract over MT6797 I2C6 |
| Device variant | Named Gemini PDA unit |
| Date(s) | 2026-07-28 |
| Investigator(s) | Device owner and Codex |
| Tracking issue | Not yet assigned |

## Question or hypothesis

Does the named device return the exact, stable primary-register tuple
`d3=1f,5e=00,d9=46,da=46` twice after the already proven secondary-address
signature `d9,d0,c0`, when the experiment changes only Fermi's post-trigger D3
predicate and truthful fixed-length result strings?

Gauss's final source and binary baseline is exact Candidate Fermi, not Curie.
It preserves Fermi's kernel release, resolved configuration, DT tree,
initramfs, LK header name and command line, USB identity, ready marker,
debugfs filename, functions, transfer order, receive prefills, FIFO/native
policy, and every operation before the first result comparison. The runtime
result identifies itself as `candidate=Gauss`; artifact hashes provide the
pre-runtime attribution.

For canonical-series compliance, the patch history applies Curie and then
Gauss. The intermediate Curie source is never configured or built for this
profile: Gauss restores the exact Fermi Kconfig and runtime ABI before
configuration is merged while retaining Curie's already exact `0x1f`
expectation and full-byte comparator. The final source is byte-identical to
the independently audited direct Fermi-to-Gauss result.

The Curie white-screen/automatic-return observation did not reach a captured
endpoint or paired pstore record. It remains real but causally unassigned.
Gauss neither repeats Curie nor treats that observation as evidence about the
D3 predicate.

## Provenance and environment

- Upstream input: Linux `7.1.3`, pinned by `kernel/manifest.json`.
- Exact source baseline:
  `drivers/i2c/busses/i2c-mt65xx.c` blob
  `7c0ddb29556fdd0b75be2aee7a597e25c2512817` from Fermi.
- Gauss-applied source blob:
  `0a453662c9bdc01a267edc65bda3a8716b78be6a`.
- Series: `patches/series-gauss-i2c6-exact-d3`, SHA-256
  `a203482246d00637c397eace5fb8526867ecd1297bae752508f14aeae9d3d66d`.
- Canonical predecessor patch:
  `patches/v7.1.3/0121-i2c-mediatek-require-exact-Curie-board-control.patch`,
  SHA-256
  `f82ad98c9bb6fb1f99bca9c778d0b1853f9ec3bbed2ce59e9643680826a7750c`.
- New patch:
  `patches/v7.1.3/0122-i2c-mediatek-add-Gauss-exact-D3-discriminator.patch`,
  SHA-256
  `654bac9cf1a97ba49d953a785a57e5cebab683be7a0a5d297acb0209ddf55e5e`.
- Profile:
  `observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-observer-initcall-blacklist-dvfsp-handoff-owner-i2c6-consumer-ap-dma-preserve-gauss`.
- Fragment: `configs/gemini-i2c6-gauss.fragment`, SHA-256
  `1536480a5f1a5c802921939c5394da46455d79769e815ee53f39b10bd6512e7a`.
- Resolved configuration: byte-identical to Fermi, SHA-256
  `c5b56a23d3711895f826487edf4762bf035d442c0bf29810f9032288adeee407`.
- Kernel/LK identity retained exactly:
  `7.1.3-gemini-fermi`, LK name `gemini-fermi`, command line
  `bootopt=64S3,32N2,64N2`.
- Intended build environment: two independent AArch64 recovery-VM source and
  output roots through `./scripts/dev-vm build-kernel`.
- Intended boot path: owner-selected logical `boot2`, after complete
  reproducibility, guarded install, flush, and full-partition readback.

## Binary attribution contract

The pre-boot auditor requires all of the following:

- exact Fermi and Gauss `i2c-mt65xx.o` identities and equal 36,296-byte size;
- a whole-object transform with only:
  `.text+0x1534`
  `410800123f140071 -> 21cc42393f00026b`,
  `.rodata+0x6f` `05 -> 1f`, and the three fixed strings at exact
  `.rodata.str1.1` offsets;
- every other object byte, section, symbol, and relocation byte-identical;
- exact ELF section and program-header layouts;
- every allocated executable section byte-identical except the same comparator
  instruction pair;
- a whole-`vmlinux` transform limited to the five source deltas plus the
  explicitly located GNU build-ID digest;
- exactly seven changed executable byte positions in `Image`, all in the
  comparator pair at `0x6463dc`;
- the expected-array D3 byte and three fixed-length result strings as the only
  semantic non-executable changes;
- the 20-byte GNU build-ID digest at `Image` offset `0xa50848` as the only
  link-generated exception, with its GNU note header validated at `0xa50838`;
- `Image.gz` decompressing exactly to `Image`; and
- byte-identical `System.map`, resolved configuration, compiled Gemini DT, and
  complete packaged DT inventory.

Two builds made before the canonical-series repair satisfied that binary
contract, and their exact boot-bearing identities remain the required oracle
in `scripts/candidate_gauss.py`. Their packages are superseded because their
provenance records the obsolete direct-Fermi patch history. Fresh canonical
lanes A and C reproduced every pinned binary identity and have distinct
generation times. The complete verifier record is
`results/build-reproducibility.txt`, SHA-256
`05b0f7c3a02b1931c7c0fe7efa8e3ad97bafaa0cfa15b230544117e4bcc805e1`.

## Safety assessment

Gauss retains `CONFIG_I2C_MT65XX_FERMI_DIAGNOSTIC=y` and compiles the Orion and
Quasar diagnostic surfaces out. The only runtime file remains root-only
`fermi-run-native`, mode `0600`, and accepts exactly one `run\n`. The one-shot
is consumed before transfers.

Each observation writes only one fixed register-pointer byte and reads one
byte. There is no register data write, arbitrary address/register/data/length
input, reset, retry control, DA9214 regulator provider, i2c-dev endpoint,
suspend action, cpufreq action, CPU-idle action, or Cortex-A72 request.
CPUs 8 and 9 remain fail-closed and unrequested.

The installer is derived from exact Fermi machinery and may write only a
live-GPT-resolved, inactive, unmounted, writable 16 MiB logical `boot2`. It
requires the exact current Curie padded checksum
`824c3391f55cc932d146ef2e573642a51fb5c077932c7b6d17316fd34020d52d`
as a storage-safety predecessor. Curie is also an unconfigured intermediate
patch dependency, but it is not Gauss's final source, binary, DT, initramfs,
or software baseline. The installer preserves a private full Curie backup,
writes once, flushes, requires full readback equality, and performs no reboot
or slot selection.

Any build-attribution, boot identity, serviceability, transfer, FIFO, IRQ,
APDMA, counter, initialization, signature, exact-D3, stability, console,
keyboard, USB, or CPU gate failure is a stop condition. Preserve the first
result and do not repeat an identical artifact.

## Associated code

- `scripts/candidate_gauss.py`: pinned inputs, exact Fermi control identities,
  and safety constants.
- `scripts/test-gauss-contract.py`: patch/config/series/manifest contract and
  mutations.
- `scripts/audit-gauss-binary.py`: exact object, ELF, Image, build-ID, gzip,
  configuration, and DT comparison.
- `scripts/validate-package-gauss.py`: exact package and mandatory build-binary
  audit.
- `scripts/build-candidate-gauss.sh` and `scripts/derive-candidate.py`:
  storage-inert assembly derived from exact Fermi machinery while retaining
  Fermi's LK header identity.
- `scripts/verify-gauss-reproducibility.py`: two-build/four-assembly matrix plus
  independent binary audits.
- `scripts/derive-installer.py`: reproducibility-record-gated, boot2-only
  installer with the Curie storage predecessor.
- `scripts/validate-gauss-result.py`: strict exact-D3 result classifier.
- `scripts/run-gauss-one-shot.py`: Fermi-identity serviceability gate, one
  invocation, and private evidence preservation.
- `results/pre-boot-hypothesis.txt`: machine-readable decision table.
- `results/runtime-candidate-gauss-attempt-1-20260728.txt`: sanitized
  attempt-1 hardware result and private-evidence hashes.

## Procedure

1. Run all Gauss static, mutation, package, result, and tooling tests.
2. Build the pinned profile twice in independent VM source/output roots.
3. Audit both build lanes against the exact Fermi package, object, and
   `vmlinux`. Require both Gauss lanes to be byte-identical.
4. Cross both packages with two independent assembly roots. Require the entire
   two-by-two matrix to be byte- and mode-identical.
5. Generate the reproducibility record and derive the guarded installer.
6. On known-good Gemian, install only if live GPT resolves exact inactive
   `boot2`, the full current partition matches Curie, battery is present,
   healthy, and above 80%, and every other storage gate passes. Preserve the
   full private backup and matching readback; do not reboot automatically.
7. Pre-arm cycle-aware pstore collection before the owner selects `boot2`.
8. Require exact Fermi kernel/LK/USB identity, console, keyboard, CPUs `0-7`,
   CPUs `8-9` offline, ready handoff, childless I2C6, zero counters, and the
   unused root-only `fermi-run-native` endpoint.
9. After adjacent revalidation, write exactly `run\n` once. Preserve the result,
   status, post-state, and private raw kernel log even after a negative write.
10. Apply the predeclared decision table. Do not retry on that boot.

## Pre-boot hypothesis, evidence, and decisions

| Exact result | Unique attributable evidence | Decision-changing next action |
| --- | --- | --- |
| Exact Fermi boot/serviceability succeeds; all 14 transfers validate; signatures are `d9,d0,c0` twice; D3 is exactly `1f` twice; `d3/5e/d9/da` are byte-stable; native/FIFO/APDMA/drain/counter/init invariants all pass | The named board exposes the stable legacy-family control contract through Fermi's already proven natural controller path, and the only executable semantic delta needed to continue past D3 was the exact comparator | Close this identification gate as a DA9214-compatible board contract. Design a zero-probe-write legacy-family driver variant; still do not request Cortex-A72. |
| The exact Fermi boot/serviceability boundary fails before the endpoint is invoked | The changed post-trigger comparator was unreachable; the failure cannot be attributed to D3 semantics | Preserve pstore/console evidence. Stop deployment and investigate build, link, container, or nondeterministic platform state without changing the diagnostic. |
| Signature passes but either observed D3 is not exactly `1f` | The live target no longer matches the repeated Fermi/Gemian D3 control observation | Stop without retry or reset. Reconcile the changed control state before selecting any compatible or provider. |
| D3 is `1f`, but `5e`, `d9`, or `da` differs between passes | The fixed pointer-read observation did not produce a stable primary control tuple | Stop. Compare the first mismatch with private Gemian evidence; do not bind a provider. |
| Any transfer, FIFO, IRQ, APDMA, drain, counter, retry, sentinel, or init invariant fails | Gauss failed before a trustworthy register-contract observation completed | Preserve the first failure and repair only the observation/controller layer. Do not interpret returned bytes as PMIC evidence. |

No outcome is a unique semiconductor ID, a register-write authorization,
regulator-provider result, voltage/enable change, suspend result, or A72
support result.

## Observations

Before the canonical-series repair, two independent Gauss builds completed.
Their `i2c-mt65xx.o`, `vmlinux`, `Image`, `Image.gz`, `System.map`, resolved
configuration, and DT inventories passed the exact attribution contract
above and were byte-identical across lanes. The seven executable byte changes
were confined to the comparator instruction pair. There were 34 semantic
non-executable byte changes and 20 GNU build-ID digest byte changes, with no
other object, ELF, or Image difference.

Those older package trees are superseded: they record a direct Fermi-to-Gauss
series that omitted selected patch 0122 from the canonical superset. The
repaired canonical and Gauss series are byte-identical and apply 0121 then
0122. The final C and Kconfig blobs remain exactly the already audited Gauss
and Fermi blobs, respectively.

Fresh canonical build lanes A and B both matched every pinned source and
binary identity, but their packages coincidentally recorded the same
`generated_utc` second. The reproducibility verifier correctly rejected that
pair as not independently attributable. The records were not edited; lane B
was discarded and a fresh lane C was built in new source, output, and artifact
roots. A and C have generation times `2026-07-28T23:11:07Z` and
`2026-07-28T23:34:43Z`. Their normalized 250-file package inventories and
build provenance are identical.

The A/C package lanes crossed with two independently published Hubble
foundations to produce four mode- and byte-identical 21-file candidates.
The final raw LK image is 7,747,584 bytes with SHA-256
`359cce03ac059410ead4b7f5cf85a71ab3b383370dc0f64a334c8fdae329a703`;
its exact 16 MiB padded boot2 image has SHA-256
`8749c0394dc8d6989eea4fe945da4afb569a1b2cd7727c98b31c5eb5140624cb`.

The derived guarded installer, SHA-256
`98e8924c14a219c5437be56b3b8d9f1a68e1c88c08cccb9006abbec152286119`,
resolved live logical `boot2` to inactive, unmounted, writable
`/dev/mmcblk0p30`, preserved a private mode-0600 full Curie backup, performed
one bounded write, synced and flushed it, and required matching remote and
local full-partition readbacks. The exact install record is
`results/install-boot2-20260728.txt`. No reboot or slot selection was
performed. Cycle-aware pstore collection was armed before a known-good-OS
poweroff, and three independent SSH probes confirmed the device remained
unreachable.

The owner then selected `boot2`. Gauss remained available through its exact
retained Fermi USB identity instead of returning to Gemian; the cycle-aware
collector consequently reached its 600-second known-good-return deadline.
The frozen runner passed its package, kernel/config, topology, childless-I2C6,
CPU0--7, CPU8/9-offline, keyboard-device, tty1, handoff, zero-counter,
initialization, USB/UDC, endpoint-mode, and adjacent-revalidation gates. It
wrote the sole accepted `run\n` token once.

All 14 fixed transfers completed and validated through the unforced native
packed/FIFO path. Both secondary-address passes returned `d9,d0,c0`; both
primary-address passes returned `d3=1f,5e=00,d9=46,da=46`; and all four
full-byte stability comparisons passed. Every distinct receive prefill was
overwritten. Each sample retained packed `TRANSFER_LEN=0x0101`,
`TRANSFER_LEN_AUX=0`, `CONTROL=0x003a`, completion-only IRQ, FIFO count one
then zero after extraction, and all-zero APDMA state. Counters changed exactly
`0,0,0,0 -> 14,0,14,14`, initialization remained `1,1`, and no forced mode,
reset, in-run retry, fatal signature, I2C timeout, boot-ID change, CPU-state
change, handoff loss, or USB/UDC loss occurred.

The result classified `complete-success`; post-capture was unconditional and
the endpoint invocation count was exactly one. Raw address-bearing evidence
remains under a mode-0700 Git-ignored directory with mode-0600 files. An
independent replay verified the stored final result and sanitized summary
byte-for-byte, the single invocation marker and root-owned one-shot guard, and
the complete transfer/FIFO/IRQ/drain/counter contract. The tracked sanitized
record is
`results/runtime-candidate-gauss-attempt-1-20260728.txt`.

## Analysis

The canonical A/C builds and four-way assembly matrix prove the intended
narrow final delta is reproducible from the repaired patch history. The
timestamp collision was an attribution failure rather than a binary failure;
discarding the colliding lane instead of editing provenance preserved that
distinction. The installed image is now fully attributable to the canonical
series, exact Fermi baseline, fixed Cassini input, and both Hubble publication
lanes.

Gauss is a decision-changing test rather than a repetition of Curie: it uses
the exact booted Fermi software identity and changes only code that executes
after the one-shot trigger. A pre-trigger failure therefore points away from
the D3 comparison, while a complete result directly tests the exact value that
bounded Fermi.

Attempt 1 selected the predeclared success branch. Observation: the named board
exposes the exact stable fixed read-only legacy-family tuple at primary
address `0x68` and the documented secondary page-2 signature at `0x69` over
the already proven native controller path. Inference: the vendor binding,
documented address mapping, and complete repeated tuple establish a
high-confidence DA9214-compatible board contract for this bounded access.
This is not a unique semiconductor ID among related DA9213/DA9214/DA9215
parts, nor independent-boot repeatability.

The identification gate needed to design a genuine legacy-family driver is
closed. The result does not establish or authorize register data writes,
`PAGE_CON` changes, regulator registration or behavior, rail ownership,
voltage/enable changes, IRQs, error recovery, arbitrary lengths, suspend,
resume, stress, or Cortex-A72 power.

## Conclusion

`passed` for the exact fixed read-only legacy-family register contract on the
named unit. Build attribution, LK assembly, guarded storage installation,
serviceability, one-shot execution, both signatures, exact D3, stability, and
post-state gates all passed.

## Follow-up

Do not repeat Gauss unchanged. Design a zero-probe-write legacy-family driver
variant with an explicit compatible and the proven primary/secondary register
contract. Its first hardware candidate must remain read-only, leave the
regulator provider and A72 consumers disconnected, and prove ordinary probe,
bind, teardown, and serviceability without the diagnostic endpoint. Review
the provider, constraints, rollback, and resume contracts independently before
any voltage, enable, or Cortex-A72 action.
