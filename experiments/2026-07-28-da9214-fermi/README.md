# Experiment: Fermi — legacy DA9214 topology fingerprint

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-28-da9214-fermi` |
| Status | `hardware-tested once; exact bounded stop after trustworthy D3 read rejected the predeclared mask` |
| Subsystem | Legacy DA9213/DA9214/DA9215 direct-address register contract over MT6797 I2C6 |
| Device variant | Named Gemini PDA unit |
| Date(s) | 2026-07-28 |
| Investigator(s) | Device owner and Codex |
| Tracking issue | Not yet assigned |

## Question or hypothesis

Can the exact ordinary I2C6 native packed/FIFO path proven by Candidate Quasar
obtain a stable, read-only legacy-family topology fingerprint without changing
the target's page, configuration, voltage, enable state, or power state?

Fermi performs two ordered passes of seven fixed one-byte-pointer plus
one-byte-read transfers:

1. `0x69:05`, `0x69:06`, `0x69:47`;
2. `0x68:d3`, `0x68:5e`, `0x68:d9`, `0x68:da`;
3. the same seven transfers again.

The direct secondary-address tuple must be `d9,d0,c0` on both passes. The
legacy `BUCK_CONF` byte at primary offset `d3` must satisfy
`value & 0x07 == 0x05`, the documented two-phase Buck A plus two-phase Buck B
configuration. The first-pass `d3`, `5e`, `d9`, and `da` values establish a
baseline; the second-pass values must match it exactly.

This is a topology/configuration fingerprint, not a unique semiconductor ID.
The legacy DA9213/14/15 register map does not document the later A-family
`DEVICE_ID`/`VARIANT_ID` page. The prior `0x201 == 0` observation therefore
does not exclude this legacy family.

## Prior evidence

Exact Candidate Quasar attempt 1 completed six native, unforced FIFO transfers
at `0x69`, returning `d9,d0,c0` twice. Every transfer used packed
`TRANSFER_LEN=0x0101`, `TRANSFER_LEN_AUX=0`, `CONTROL=0x003a`, completion-only
IRQ, one received FIFO byte followed by a drained FIFO, and no I2C6 APDMA
start. Controller initialization remained exactly `1,1`; the second pass
therefore supplies an independent clean-reuse observation without an explicit
or recovery reset.

The legacy datasheet describes:

- direct primary access at default seven-bit address `0x68`;
- direct secondary access at adjacent address `0x69`;
- `0xd3` as `BUCK_CONF`, whose low phase-selection fields distinguish the
  two-plus-two configuration;
- `0x5e` as `BUCKB_CONT`; and
- `0xd9`/`0xda` as the Buck B A/B voltage-setting bytes.

The already captured Gemian vendor path repeatedly identifies the installed
component as DA9214 and observes the `d9,d0,c0` interface/configuration tuple.
Those are independent software-path and family-signature evidence, not a
documented unique chip-ID read.

## Provenance and environment

- Kernel release and upstream input: Linux `7.1.3`, pinned by
  `kernel/manifest.json`.
- Exact predecessor series:
  `patches/series-quasar-i2c6-native-fifo`.
- Fermi series:
  `patches/series-fermi-i2c6-topology-fingerprint`; it must be exact Quasar
  plus
  `patches/v7.1.3/0120-i2c-mediatek-add-fixed-Fermi-topology-fingerprint.patch`.
- Named profile:
  `observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-observer-initcall-blacklist-dvfsp-handoff-owner-i2c6-consumer-ap-dma-preserve-fermi`.
- Fermi policy: `configs/gemini-i2c6-fermi.fragment`.
- Intended build environment: two independent recovery-VM source/build roots
  through `./scripts/dev-vm build-kernel`.
- Intended assembly: cross both packages with two independent assembly roots
  and require all four candidates to be byte-identical.
- Intended boot path: owner-selected logical `boot2`, only after validation,
  guarded installation, and a matching full-partition readback.

Build, assembly, installation, and hardware observations remain separate
evidence gates.

## Safety assessment

The profile must compile both earlier diagnostic surfaces out:

- `CONFIG_I2C_MT65XX_ORION_DIAGNOSTIC=n`;
- `CONFIG_I2C_MT65XX_QUASAR_DIAGNOSTIC=n`; and
- `CONFIG_I2C_MT65XX_FERMI_DIAGNOSTIC=y`.

The only new runtime file is fixed `fermi-run-native`, mode `0600`, under the
canonical I2C6 adapter's debugfs directory. It accepts exactly one `run\n`;
the one-shot is consumed before any transfer or run gate. The root adapter lock,
childless-adapter requirement, ready DVFSP handoff, exact canonical OF-node
identity, retries `1 -> 0 -> 1`, zero pre-run counters, and exact controller
initialization gates are inherited from Quasar.

Each bus observation sends a single fixed pointer byte and then reads a single
byte. It is therefore not literally a read-only bus transaction, but it sends
no register data byte. There is:

- no `PAGE_CON` access;
- no data, page, address, length, engine, retry, or reset input;
- no i2c-dev endpoint;
- no DA9211/DA9214 regulator provider;
- no register data write;
- no suspend, cpufreq, or CPU-idle operation; and
- no Cortex-A72 request or power action.

Fermi never calls `mtk_i2c_init_hw()`. It must naturally retain Quasar's FIFO
policy and exact per-sample snapshots: packed `0101/0000`, transaction count
two, control `003a`, completion-only IRQ, FIFO count one then zero, and all
I2C6 APDMA fields zero. Complete success requires absolute counters
`14,0,14,14`, initialization unchanged at `1,1`, the exact signature twice,
the topology mask once per pass, four stable configuration bytes, and every
returned byte different from that individual sample's receive prefill. A
prefill collision is a safe inconclusive failure, even if the byte would
otherwise satisfy a signature, topology, or stability check.

Any boot identity, serviceability, transport, native-policy, counter,
signature, topology, or stability mismatch is a stop condition. Preserve the
first result and do not invoke the file twice or repeat an identical image.

## Associated code

- `scripts/candidate_fermi.py` pins the Fermi inputs and exact Quasar
  serviceability/assembly foundation.
- `scripts/test-fermi-contract.py` validates the patch, configuration, series,
  manifest, transfer order, safety exclusions, and representative mutations.
- `scripts/validate-package-fermi.py` validates the exact kernel package.
- `scripts/build-candidate-fermi.sh` derives the storage-inert LK assembly
  workflow from exact source-pinned Quasar machinery.
- `scripts/verify-fermi-reproducibility.py` validates the independent
  two-build/four-assembly matrix.
- `scripts/derive-installer.py` accepts only the exact hash-pinned complete
  reproducibility record and derives a `boot2`-only installer guarded to
  Quasar's full-partition predecessor identity.
- `scripts/validate-fermi-result.py` strictly classifies the fixed debugfs
  result.
- `scripts/run-fermi-one-shot.py` applies the inherited exact serviceability
  gates, performs at most one invocation, and preserves private raw evidence.
- `results/pre-boot-hypothesis.txt` records the planned decision table in a
  machine-readable form.
- `results/build-reproducibility.txt` records the byte-identical two-build,
  four-assembly matrix.
- `results/install-boot2-20260728.txt` records the sanitized guarded install,
  full backup, flush, and readback evidence.

## Procedure

1. Run Fermi's static and mutation tests. Require valid JSON, patch syntax,
   whitespace, exact Quasar-plus-0120 series identity, and all safety
   exclusions.
2. Build the named profile twice in independent VM output roots. Validate both
   packages and require exact normalized equality.
3. Assemble the two packages in two independent roots. Require the complete
   two-by-two matrix to be byte- and mode-identical and record the raw, padded,
   manifest, DT, initramfs, and LK-analysis identities.
4. A guarded installer may target only live-GPT-resolved, inactive, unmounted,
   writable logical `boot2`. It must require exact Quasar as the predecessor,
   preserve a private full backup, write one exact 16 MiB padded image, flush,
   and require matching remote and local full readbacks. It must not reboot.
5. On one owner-selected `boot2` start, require exact Fermi kernel/configuration,
   console, keyboard, USB shell, CPUs `0-7`, childless I2C6, ready handoff, zero
   transfer counters, and an unused mode-`0600` endpoint.
6. After an adjacent revalidation, write exactly `run\n` once. Preserve the
   complete result, I2C6 status, serviceability state, and private raw kernel
   log. Never retry on that boot.
7. Classify the result with the table below. Reboot only through the existing
   owner-requested native path after evidence capture.

## Pre-boot hypothesis, evidence, and decisions

| Exact result | Unique attributable evidence | Decision-changing next action |
| --- | --- | --- |
| All 14 transfers validate; both signatures are `d9,d0,c0`; both `d3` values satisfy `& 07 == 05`; `d3/5e/d9/da` are byte-stable; every sample retains Quasar's FIFO/native/APDMA/drain contract; counters are `14,0,14,14`; init remains `1,1` | The installed device exposes a stable legacy-family two-plus-two topology/configuration contract through the already proven natural controller path | Close the fingerprint gate as a composite DA9214-compatible board contract. Design a genuine legacy DA9213/14/15 driver variant with zero probe-time writes; do not power an A72 yet. |
| Signature passes but `d3 & 07 != 05` on either pass | The electrical target is in the expected legacy/interface family but does not expose the documented two-plus-two configuration | Stop. Reconcile the exact phase encoding against vendor source/binary evidence before selecting a compatible or provider. |
| First-pass topology/configuration values are valid but any second-pass `d3/5e/d9/da` byte differs | A supposedly non-mutating observation did not produce stable configuration state | Stop without reset or retry. Compare the first mismatch with Gemian behavior and controller snapshots; do not bind a provider. |
| Any transport, FIFO, IRQ, APDMA, drain, counter, retry, or init invariant fails | Fermi failed before a trustworthy register-contract observation completed | Preserve the first failure. Fix only the controller/observation layer and do not interpret values as PMIC evidence. |
| Kernel, configuration, handoff, topology, CPU, console, keyboard, or USB gate fails | The candidate did not reach an attributable observation boundary | Do not invoke the diagnostic. Preserve evidence and change only the failed layer. |

No outcome is a unique semiconductor ID, write authorization, regulator
provider result, voltage/enable change, suspend result, or Cortex-A72 support.

## Observations

Two independent kernel builds produced the same normalized 248-file package
inventory. Crossing both builds with two independently preserved
Cassini/Hubble foundations produced four byte- and mode-identical 21-file
candidates. The raw LK image is 7,747,584 bytes with SHA-256
`33210b4144ad8b485e8da8284feb7af772f2cc99a762a9a120736b1bdc654635`;
its exact 16 MiB boot2 form is
`0234c36c401aba7901f76a5ab8cc034d3d6038e132c9d9ad505e983119c69534`.
The complete reproducibility record is
`bddb4e126d87289b253872063713d12e61a36b088e551e61afc63534634a5fd6`.

On known-good Gemian `3.18.41+`, the guarded installer resolved exactly one
live-GPT `boot2` row at `/dev/mmcblk0p30`; active root was
`/dev/mmcblk0p29`. The inactive 16 MiB target was writable, unmounted, unused
as swap, holder-free, and contained exact readback-verified Quasar
`73fceae91606ebf831e503585406df1e2be997edc9fddff1bcae9ec718c91d78`.
Battery was present, 100%, and healthy. The installer preserved a private full
Quasar backup, wrote and flushed Fermi, and required matching remote and local
full-partition hashes plus byte equality. The private evidence manifest is
`e67de92aa213c44432d2e7219255a6f9eec05f0d99bae25140666648a4f26a38`.
The device was then powered off and remained unreachable for three consecutive
checks.

The owner then selected `boot2`.  The exact Fermi kernel and configuration,
CPUs `0-7`, one keyboard input device, ready DVFSP handoff, childless I2C6,
zero initial I2C6 counters, configured USB gadget, and unused mode-`0600`
one-shot endpoint all passed the runner's gates.  The adjacent revalidation
passed and the endpoint was invoked exactly once.

Four transfers completed through the native FIFO path.  The secondary-address
signature returned `d9,d0,c0` on the first pass.  Primary-address register
`d3` then returned `1f`, different from its `96` receive prefill, with the
same packed `0101/0000` lengths, `003a` control, completion-only IRQ, FIFO
count one followed by zero, and all-zero APDMA snapshots as the successful
signature samples.  Initialization remained `1,1`; absolute transfer,
DMA-start, nonzero-start, and IRQ counters became `4,0,4,4`.  The diagnostic
stopped as designed with `-EUCLEAN` because `1f & 07 == 07`, not the
predeclared `05`.  Boot identity, CPUs `0-7`, handoff readiness, USB carrier,
USB operational state, and configured UDC remained unchanged afterward, and
the raw kernel log contained no fatal or I2C-timeout signature.

Two independently retained Gemian boots already contain the same primary
control tuple `5e=00,d3=1f,d9=46,da=46`, as recorded with private-evidence
hashes in the Cassini reconciliation record.  Candidate Fermi did not reach
`5e`, `d9`, `da`, or the second pass, so those Gemian values are comparison
evidence rather than Fermi observations.

The private mode-`0600` raw transcript is
`7db8d5c04115e8c64882fa9ef1c955a55289c18b33f8cf06d5b3a129320fa383`;
the final raw debugfs state is
`698f7284dca254e9a9be6ed29262acc01e77508e2aba335b3ccef5d470cfcafe`;
the raw kernel log is
`cff5a554553ff2945c3ccc27ca9e0af4bdc686df4eef8dfcc2233550cff458bc`.
The sanitized result is preserved in
`results/runtime-candidate-fermi-attempt-1-20260728.txt`.

## Analysis

Build, LK-container, boot2 deployment, exact runtime identity, serviceability,
and the first four fixed observations are complete and mutually consistent.
The result is not an I2C transport failure: every controller, FIFO, IRQ, DMA,
counter, initialization, sentinel, and post-serviceability invariant passed.

Both Renesas register descriptions give `BUCK_CONF` the same layout:
bits 4 and 3 enable current-dependent phase shedding for Buck B and Buck A,
bit 2 selects one or two Buck B phases, and bits 1:0 select the Buck A phase
count.  Thus raw `1f` means both phase-shedding bits are set, Buck B's
two-phase selector is set, and Buck A's raw selector is `11`.  The same
descriptions explicitly state that Buck A selector values above `01` apply
only to DA9213; other variants limit the number of active phases to two.
Consequently the literal `05` mask was too strict: `1f` is compatible with an
effectively two-plus-two DA9214, while neither `1f` nor `05` uniquely
identifies a family member.

The recovered Gemian probe reads `d0` through `da`, but its ordinary
initialization path does not write `d3`; the active binary likewise detects
only the high nibble of secondary register `05`.  The repeated Gemian `1f`
and Fermi `1f` therefore form a cross-kernel control-state observation, not a
silicon ID or proof of whether OTP or an earlier firmware stage established
the byte.

The generated sanitized helper summary includes success-criterion phrases
ending in `-twice`; they must not be read as observations for this bounded
failure.  Fermi observed the signature and `d3` only on pass zero.  The
tracked result file records that distinction explicitly.

## Conclusion

Candidate Fermi passed its exact boot and native-transport boundaries and
produced a decisive bounded result.  It disproved only the predeclared raw
`d3 & 07 == 05` assumption.  It did not disprove the DA9214-compatible board
contract, authorize a regulator provider, or authorize Cortex-A72 power.
Exact Fermi must not be invoked or booted for this experiment again.

## Follow-up

The smallest decision-changing successor must preserve every Fermi transfer,
sentinel, FIFO, IRQ, APDMA, counter, initialization, serviceability, and
one-shot gate.  Its only semantic change should require exact first-pass
`d3 == 1f`, then continue through `5e`, `d9`, and `da`, and require full-byte
equality for all four primary registers on pass two.  The expected
cross-kernel comparison is Gemian `1f,00,46,46`, but the successor must record
the complete natural result before making that comparison.  This remains a
read-only board-contract experiment with no provider, register-data write, or
Cortex-A72 request.
