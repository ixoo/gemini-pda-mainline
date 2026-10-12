# Runtime 32 preparation: the runtime 31 protocol on candidate 31 (proposal 0179)

Status: candidate 31 composed and validated by the custodian from the compile-36 package
`521e1ce3…` (built input 7fa36c01) with candidate 30's RAM root, board DT and kernel config
byte-identical (`449832a3…`, `25ab60f4…`, `975f8703…`; helper and supplicant preserved;
PSCI and clock contract passed); boot image `416f502c…` (12302336 bytes), full padded boot2
`54791b43…` (exact 16 MiB). [results/candidate-31.json](results/candidate-31.json) (SHA-256
`00662e5c…`) is the receipt's exact bytes and `runtime-32/results/candidate.json` its copy.
The current boot2 content is the installed candidate 30 (`e758bf36…`); the live Gemian boot,
independently reverified, is `505bcade-6441-4729-82ee-025c341648b9`. The identity bindings
below are complete; the custodian derives private installer 31 from the reviewed installer 30
by the identity substitutions in the last section, reverifies identity, power and the GPT
guard at installation, and the owner selects boot2 physically. No device step has run.

## What differs from runtime 31

Kernel, proposal 0179 only, after 0178 in canonical order (built driver files `mac.c`
`2d7e5a33…`, `data-rx.h` `6330bac2…`; reviewed, no comment split). 0179 is a metadata-only
observation: the receive decoder reports the GROUP_VLD mask it already computes, and the
data phase keeps per delivered class the count of frames with group 1 (the received PN
group) present or absent and a per-class bitmap of the mask values 0..15 seen, printed
once at the data phase end, with the first data RX record carrying the mask. No PN bytes,
payload or addresses are read or stored; nothing reaches the crypto path; no delivery,
drop, radio, transmit or timing behaviour changes.

Everything else is runtime 31's exactly: the same admitted radio effects, the same ping
and SSH budgets, the same data-phase budget and teardown margin, the same single native
recovery, the same credential and address handling, the same decoders' gates. The only
new evidence is the group-1 observation.

## Hypothesis and what the run can and cannot establish

Hypothesis (availability only): the delivered unicast and group data classes carry some
GROUP_VLD mask set; whether group 1 (the PN group) is among the bits set on those
delivered frames is presently unknown, and runtime 32 records it. The run establishes only
whether group 1 is available on the sampled delivered classes. It does not establish who
enforces replay, does not prove firmware enforcement or its absence, and makes no
operational, reliability or replay-protection claim; `wifi_operational` stays false. A
present group-1 PN would still prove neither the key, TID, key incarnation, authenticity
nor ordering, and the pinned mac80211 path reads the PN from the in-frame CCMP header,
which the driver's `RX_FLAG_IV_STRIPPED` delivery removes — so nothing in this run changes
the crypto path.

## Observation-required gate

A valid runtime 32 C3 measurement requires the `data group1` observation line to be
present and consistent as the classifier defines consistency: a single line, placed after
the data phase end record and before the first cleanup submission or the terminal;
`present + absent` equal to the end record's delivered unicast and group counts; the
per-class mask bitmap limited to the admitted values 8..15 (group 4 mandatory), zero iff
the class total is zero, with an odd-index bit iff group 1 was present and an even-index
bit iff group 1 was absent. A missing, duplicated or inconsistent line is malformed and
the measurement does not count; the lifecycle verdicts (C2/C3, bounded join, healthy
cleanup) are decided exactly as in runtime 31 and are independent of this observation.

## Branches, each ending the lifetime once

1. Healthy lifetime with the observation present and consistent: group 1 observed as
   present or absent on each delivered class, recorded with the mask set; the first fully
   measured C3 lifetime that also answers the availability question. The network terms
   (lease, ping, SSH) are reported apart, as in runtime 31, and decide nothing here.
2. A healthy lifetime but a malformed or absent observation line: the lifecycle verdicts
   stand; the availability question is unanswered and the observation is retried only with
   a decision-changing change, never by repeating the identical boot.
3. A refusal, disconnect, footer or any named fault as in runtime 31's branches: recorded
   by its fields, fail-stop, seal, the reviewed native recovery once; the availability
   question is unanswered.

No branch repeats a boot without a decision-changing change. Nothing is reconnected or
rekeyed. Replay enforcement in firmware remains unknown and unclaimed.

## Bindings

| Adapter | Runtime 32 binding |
| --- | --- |
| `build-candidate.py` | `COMMIT 7fa36c01…`, `PACKAGE 521e1ce3…` (30ba55e3); every other pin unchanged |
| `install-passive.py` | predecessor `e758bf36…` (installed candidate 30), receipt `mt6797-wifi-phase-b-deployment-31`, `results/candidate-31.json`, slot `00662e5c…` |
| `capture-private.py` | `capture-32`, `session-32/deployment-summary.txt`, `results/candidate-31.json`, slot `00662e5c…` |
| `passive-session.py` | `results/candidate-31.json`; 63-member RAM root with the required supplicant |
| `passive-host.py` | `session-32`, `capture-32`; identity `runtime-32/results/candidate.json`; PSK-bound script required; `GEMINI_WIFI_SSH_RECEIPT` optional; `SCAN.SOURCE_LIMIT` 32768 |
| `prepare-runtime.py` | `results/candidate-31.json` against the compile-36 input and package, both slots, predecessor `e758bf36…`, the PSK-bound wrapper (≤ 32768 bytes); creates `wifi-phase-b/session-32` only |
| `join-once.sh`, `laptop-wifi-ssh.py` | unchanged from runtime 31 |

## Private installer 31 derivation (identity-only, from reviewed installer 30)

The custodian derives private installer 31 from the reviewed private installer 30
(SHA `e2b9ad42…`) with its existing generator, substituting only these identity values; no
implementation or code change, and every semantic change is the experiment's, not the
generator's:

| Identity field | Installer 30 | Installer 31 |
| --- | --- | --- |
| candidate receipt / manifest | `results/candidate-30.json` / `44117611…` | `results/candidate-31.json` / `00662e5c…` |
| candidate boot2 written (full 16 MiB readback target) | `e758bf36…` | `54791b43…` |
| candidate raw boot image | `7aee04b8…` | `416f502c…` (12302336 bytes) |
| predecessor boot2 (content overwritten) | `27005b8f…` (candidate 29) | `e758bf36…` (installed candidate 30) |
| `--previous-gemian-boot` (live Gemian) | `6a938937-…` | `505bcade-6441-4729-82ee-025c341648b9` |
| deployment receipt name | `mt6797-wifi-phase-b-deployment-30` | `mt6797-wifi-phase-b-deployment-31` |

Root reverifies identity, power, the GPT guard, the inactive/unmounted/non-root state, size,
writability and stable power at installation; skips an already-matching full-partition
checksum; otherwise records the predecessor, pads to exact size, writes, syncs and requires a
matching full readback (`54791b43…`), then a clean power-off. The owner selects boot2
physically. Validators run under Python 3.13. Fixtures follow the bindings; nothing is
installed or booted by this preparation.

## Checks on the input (proposal 0179)

Completed: the decoder C unit test (`tests/data-rx-test.c`, ASan/UBSan), the host/classifier
test (`tests/host-test.py`, 15 cases including the consistency negatives), `./scripts/check-repository`,
the managed Buildbox build (compile 36), and the pinned `scripts/checkpatch.pl --strict` on the
0179 patch. checkpatch reports one ERROR (missing Signed-off-by) and one commit-description
line-length WARNING, and no code-style defect in the change: the missing sign-off is the
archive's standing state — the proposals carry no DCO sign-off, which is never fabricated and
is added only at a truthful upstream submission — and the warning is a commit-log prose line,
consistent with the series. Neither is a material code or style failure.
