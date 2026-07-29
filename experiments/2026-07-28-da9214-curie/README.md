# Experiment: Curie — exact Gemini board-control tuple

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-28-da9214-curie` |
| Status | `attempt 1 failed before serviceability; automatic watchdog-class return; endpoint not invoked` |
| Subsystem | Legacy DA9213/DA9214/DA9215 register contract over MT6797 I2C6 |
| Device variant | Named Gemini PDA unit |
| Date(s) | 2026-07-28 |
| Investigator(s) | Device owner and Codex |
| Tracking issue | Not yet assigned |

## Question or hypothesis

Can the already proven native packed/FIFO observation path complete two stable
passes of the fixed legacy-family tuple when the named board's complete
`BUCK_CONF` byte is required to equal the previously observed `0x1f`?

Curie is the semantic successor to Fermi. It retains Fermi's exact two-pass
order, individual receive prefills, transport gates, early-stop behavior,
counters, and full-byte stability checks:

1. `0x69:05`, `0x69:06`, `0x69:47`;
2. `0x68:d3`, `0x68:5e`, `0x68:d9`, `0x68:da`;
3. the same seven observations again.

The direct secondary-address tuple must be `d9,d0,c0` on each pass. Primary
offset `d3` must equal `1f` on each pass. First-pass `d3`, `5e`, `d9`, and
`da` establish a baseline and the second-pass bytes must match exactly.

`d3=1f` is an exact control-state gate for this named board. It is not a
unique semiconductor identity and does not uniquely distinguish DA9213 from
DA9214 or prove a particular physical phase topology.

## Prior evidence

Fermi attempt 1 produced four trustworthy native FIFO observations. The
secondary-address signature returned `d9,d0,c0`; primary `d3` returned `1f`.
All four transfers retained packed `0101/0000` lengths, `003a` control,
completion-only IRQ, one FIFO byte followed by an empty FIFO, all-zero APDMA
snapshots, unchanged initialization `1,1`, and value bytes distinct from their
individual prefills.

Fermi stopped exactly at its predeclared masked D3 comparator. The stop was
semantic, not a transport failure: `1f & 07` equals `07`, not `05`.

The older and newer Renesas register descriptions agree that D3 bits 4 and 3
control phase shedding, bit 2 selects Buck B's phase count, and bits 1:0 are
Buck A's selector. They also state that Buck A selector encodings above `01`
apply to DA9213 and are capped at the maximum supported phase count on other
variants. Thus the old low-bit `05` predicate was over-specific. Raw `1f` is
compatible with the installed board's DA9214 control state but is not a
unique identity or topology fingerprint.

Two independently retained Gemian boot logs contain the comparison tuple
`d3=1f,5e=00,d9=46,da=46`. Their private-evidence hashes and sanitized
provenance are recorded by the Cassini reconciliation experiment. Curie does
not require the latter three values; it records them naturally and requires
only pass-to-pass equality. Comparing a completed Curie tuple with Gemian is
analysis after capture, not an additional in-kernel acceptance gate.

## Provenance and environment

- Kernel and upstream input: Linux `7.1.3`, pinned by
  `kernel/manifest.json`.
- Exact predecessor series:
  `patches/series-fermi-i2c6-topology-fingerprint`.
- Curie series: `patches/series-curie-i2c6-board-tuple`; it must be exact
  Fermi plus
  `patches/v7.1.3/0121-i2c-mediatek-require-exact-Curie-board-control.patch`.
- Named profile:
  `observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-observer-initcall-blacklist-dvfsp-handoff-owner-i2c6-consumer-ap-dma-preserve-curie`.
- Curie policy: `configs/gemini-i2c6-curie.fragment`.
- Completed build environment: two independent recovery-VM roots
  `/home/julien.guest/src/linux-7.1.3-curie-{a,b}-20260728`,
  `/home/julien.guest/build/linux-7.1.3-curie-{a,b}-20260728`, and
  `/home/julien.guest/artifacts/curie-kernel-{a,b}-20260728`, through
  `./scripts/dev-vm build-kernel`.
- Completed assembly: both packages crossed with independently retained
  Cassini/Hubble A and B foundations in
  `boot-candidates-curie-matrix-{aa,ab,ba,bb}-20260728`. All four candidates
  are byte- and mode-identical.
- Installed boot path: owner-selected logical `boot2`, after live-GPT
  resolution, exact Fermi predecessor validation, a private full backup,
  write and flush, and exact full-partition readback.

Build, assembly, and installation gates are complete. Attempt 1 failed before
boot serviceability; the one-shot endpoint was not invoked and the tuple
remains untested.

## Safety assessment

The configuration compiles the Orion and Quasar diagnostics out and selects
only `CONFIG_I2C_MT65XX_CURIE_DIAGNOSTIC=y`. Fermi's renamed symbol is absent
from the Curie kernel.

Curie's only runtime surface is fixed `curie-run-native`, mode `0600`, under
the canonical I2C6 adapter's debugfs directory. It accepts exactly `run\n`
once. The one-shot is consumed before any transfer or run gate. Root-adapter
locking, a childless adapter, ready DVFSP handoff, exact canonical OF-node
identity, retries `1 -> 0 -> 1`, zero pre-run counters, and exact controller
initialization are inherited unchanged.

Each observation sends a fixed one-byte register pointer, then reads one byte.
It is not literally a read-only bus transaction, but sends no register data
byte. There is no:

- `PAGE_CON` access or register-data write;
- arbitrary address, register, length, engine, retry, or reset input;
- explicit controller or APDMA reset;
- i2c-dev endpoint or regulator provider;
- suspend, cpufreq, or CPU-idle operation; or
- Cortex-A72 power request.

Complete success requires 14 transport completions and validations, absolute
counters `14,0,14,14`, controller initialization unchanged at `1,1`, the
signature twice, exact D3 control state twice, four stable configuration
pairs, and every returned byte different from that sample's receive prefill.
A prefill collision is a safe inconclusive stop.

Any boot identity, configuration, serviceability, transport, native policy,
counter, signature, board-control, or stability mismatch is a stop condition.
Preserve the first result and do not invoke the file twice or repeat an
identical image without a new decision-changing measurement.

## Associated code

- `scripts/candidate_curie.py` pins Curie's exact inputs and inherited Fermi
  foundation.
- `scripts/test-curie-contract.py` validates patch, configuration, series,
  manifest, exact D3 semantics, safety exclusions, and mutations.
- `scripts/validate-package-curie.py` validates the exact kernel package.
- `scripts/build-candidate-curie.sh` derives the storage-inert LK assembly
  workflow from source-pinned Fermi machinery.
- `scripts/verify-curie-reproducibility.py` validates the two-build/four-
  assembly matrix.
- `scripts/derive-installer.py` accepts only a hash-pinned complete
  reproducibility record and derives a `boot2`-only installer guarded to the
  exact Fermi full-partition predecessor.
- `scripts/validate-curie-result.py` strictly classifies complete and bounded
  fixed debugfs results.
- `scripts/run-curie-one-shot.py` applies the exact serviceability gates,
  performs at most one invocation, and preserves private raw evidence.
- `results/pre-boot-hypothesis.txt` records the planned decision table in
  machine-readable form.
- `results/build-reproducibility.txt` records the exact two-build, four-
  assembly equality proof.
- `results/install-boot2-20260728.txt` records the sanitized guarded install,
  predecessor backup, flush, full readback, and shutdown evidence.
- `results/runtime-boot-attempt-1-20260728.txt` records the sanitized failed
  boot boundary, post-return storage identity, reset-class fields, and
  attribution limits.

## Procedure

1. Run all Curie static and mutation tests. Require valid JSON, patch syntax,
   whitespace, exact Fermi-plus-0121 series identity, source hashes, and safety
   exclusions.
2. Build the named profile twice in independent VM output roots. Validate each
   package and require normalized equality.
3. Assemble both packages in two independent roots. Require the complete 2x2
   matrix to be byte- and mode-identical; record the raw, padded, manifest,
   DT, initramfs, and LK-analysis identities.
4. Pin the complete reproducibility record. A guarded installer may target
   only live-GPT-resolved, inactive, unmounted, writable logical `boot2`. It
   must require exact Fermi as predecessor, preserve a private full backup,
   write one exact 16 MiB padded image, flush, and require matching full
   readback. It must not reboot.
5. On one owner-selected `boot2` start, require exact Curie
   kernel/configuration, console, keyboard, USB shell, CPUs `0-7`, childless
   I2C6, ready handoff, zero counters, and an unused mode-`0600` endpoint.
6. After adjacent revalidation, write exactly `run\n` once. Preserve the
   complete result, I2C6 status, serviceability state, and private kernel log.
   Never retry on that boot.
7. Classify the result using the table below. Reboot only through the existing
   owner-requested native path after evidence capture.

## Pre-boot hypothesis, evidence, and decisions

| Exact result | Unique attributable evidence | Decision-changing next action |
| --- | --- | --- |
| All 14 transfers validate; both signatures are `d9,d0,c0`; both D3 bytes are exactly `1f`; `d3/5e/d9/da` are byte-stable; all native FIFO/APDMA/drain gates pass; counters are `14,0,14,14`; init remains `1,1` | This named Gemini exposes a repeatable, exact legacy-family control tuple through the already proven natural controller path | Compare the recorded four-byte primary tuple with independent Gemian evidence. If reconciled, close this observation gate and design a zero-probe-write legacy-family provider; do not power an A72 yet. |
| A transport-valid D3 byte differs from `1f`, including a value such as `1d` that would pass Fermi's old low-bit mask | The named-board byte is not the exact independently observed control state; Curie's full-byte gate distinguishes this from Fermi's over-broad low-bit acceptance | Stop without retry. Reconcile the complete D3 byte with independent Gemian state before changing any driver compatibility claim. |
| First-pass values validate but any second-pass `d3/5e/d9/da` differs | A supposedly non-mutating observation did not yield stable configuration state | Stop without reset or retry. Compare the first mismatch with Gemian behavior and controller snapshots; do not bind a provider. |
| Any transport, FIFO, IRQ, APDMA, drain, counter, retry, or init invariant fails | Curie stopped before a trustworthy complete register-contract observation | Preserve the first failure. Fix only the controller/observation layer and do not interpret later values as PMIC evidence. |
| Any kernel, configuration, handoff, CPU, console, keyboard, USB, adapter, or endpoint gate fails | The candidate did not reach an attributable observation boundary | Do not invoke the diagnostic. Preserve evidence and change only the failed layer. |

No outcome is a unique semiconductor identity, physical topology proof, write
authorization, regulator-provider result, voltage or enable change, suspend
result, or Cortex-A72 support.

## Observations

Both independent kernel lanes produced the same normalized 249-file package
inventory
`9e4a8c98c3b0297814ea776bae0320ea2e46ff598354d2068a138256ac92271a`
and normalized build identity
`cdc5b6e7d82172deb6343be785a13651728c3cd49fa297cacf18f2202348d6e5`.
Their package manifests differ only through independently generated
provenance, including distinct generation times. Both exact Curie package
validators passed with configuration
`7a65d2f433304ad0361acb7d89ee1ff7bea7bd3bfc8d1bf2edbc6dd3711f8657`
and kernel Image
`86f0ecf55716453a23eac0fc8256a3ca66b789e7bf94cd8a206dfa6d4e9a236b`.

The complete 2x2 LK matrix produced one 21-file byte- and mode-identical
candidate inventory
`6adb8f4a5461554883463d77e9b27479e2b003401f77539bfbb35fa9363a8d61`.
The raw candidate is 7,747,584 bytes with SHA-256
`36b954acbc54278d2d81945d1baa830d6140af9dbe5f04f76e2deab50dde9598`.
Its zero-tail-padded 16 MiB `boot2` image is
`824c3391f55cc932d146ef2e573642a51fb5c077932c7b6d17316fd34020d52d`.
The exact reproducibility record is
`ca3d70bf605e1397b49eaf7a7446b2573555dde067546b1adb5c9ef50ac7d748`.

On known-good Gemian `3.18.41+`, the guarded installer resolved exactly one
live-GPT `boot2` row at `/dev/mmcblk0p30`; active root was
`/dev/mmcblk0p29`. The target was inactive, unmounted, writable, holder-free,
16 MiB, and contained the exact readback-verified Fermi predecessor
`0234c36c401aba7901f76a5ab8cc034d3d6038e132c9d9ad505e983119c69534`.
Battery was present, healthy, and 100%. The installer preserved a private
mode-`0600` full Fermi backup, wrote and flushed Curie, and required matching
remote and local full-partition readbacks at
`824c3391f55cc932d146ef2e573642a51fb5c077932c7b6d17316fd34020d52d`.
It removed remote staging and performed no reboot. Gemian was then powered
off, confirmed by three consecutive unreachable SSH checks.

On attempt 1 the owner selected logical `boot2`, saw a gray screen without
console text, and then observed an automatic return to Gemian. No recoverable
console or USB service was established, and the Curie endpoint was never
invoked. There were therefore zero Curie transfers and no execution of its D3
comparator.

The pre-attempt and post-return Gemian boot-ID hashes differ. Read-only
post-return inspection found the complete 16 MiB logical `boot2` still matched
exact Curie at
`824c3391f55cc932d146ef2e573642a51fb5c077932c7b6d17316fd34020d52d`.
Gemian reported `boot_reason=4`,
`androidboot.bootreason=wdt_by_pass_pwk`, and `powerup_reason=reboot`; PMIC
watchdog flags were zero and the three retained reset latches were
`0x4248000`, `0x0`, and `0xbabebabe`.

The post-return pstore directory was empty. Its private capture manifest is
`e12a57fc5ecc182e4861983bfe72748b312ca9f4c2cfb02a588d33fd5073fa13`,
but the collector was started with `wait_for_cycle=no`, so this is an unpaired
snapshot of the already-running recovery boot rather than a capture spanning
the attempted cycle. `/proc/last_kmsg` contained only a generic 74-byte ram
console header with hardware status 5 and FIQ step 0. Neither source retained
a Curie identity or progress marker.

Fermi's prior `d3=1f` result remains predecessor evidence, not a Curie
observation.

## Analysis

Source, package, LK-container, storage-target, predecessor, and readback
attribution are complete. The only causal change from Fermi is patch 0121's
replacement of the masked D3 predicate with exact named-board byte `0x1f`;
the three additional primary values remain pass-to-pass observations rather
than hard-coded acceptance gates.

Exact post-attempt `boot2` identity, together with the pre-boot LK and
reproducibility gates, rules out packaging or partition-write corruption as
the explanation for attempt 1. Because `curie-run-native` was never invoked,
the exact D3 comparator and every diagnostic transfer are also ruled out as
executed causes.

The changed Gemian boot ID corroborates an intervening boot cycle. The
watchdog-class reason does not distinguish watchdog expiry from a direct
TOPRGU software reset, and zero PMIC watchdog flags do not localize the
failure. The unpaired empty pstore snapshot and generic `last_kmsg` header
establish no Curie kernel, initramfs, panic, hang, or last-progress boundary.
The exact cause of the early boot-gate failure is therefore unknown.

## Conclusion

Candidate Curie remains reproducibly built, fully container-validated, and
storage-integrity verified, but attempt 1 failed before an attributable
serviceability boundary and returned automatically with a nondiscriminating
watchdog-class reason. The board tuple was not run. No Curie transport,
provider, voltage, enable, phase-topology, or Cortex-A72 support claim is
established.

## Follow-up

Do not repeat exact Curie. A successor must add a decision-changing,
independent observation path and arm paired cycle collection before its boot,
so a disconnect, reconnect, changed boot ID, reset fields, pstore, and
post-cycle storage identity belong to the same attempt. Preserve Curie's tuple
as untested and do not select a regulator provider or request CPUs 8/9 until a
separately attributable result is captured and reconciled with independent
Gemian evidence.
