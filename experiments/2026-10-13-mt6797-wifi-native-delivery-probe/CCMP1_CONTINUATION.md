# CCMP1 failed-log-export continuation — narrow admission

ROOT observed fresh CCMP1 boot `da2acc9f-8821-4452-8631-ca7d487e4793`, exact
input83b91/receipt725a/full418. Common init/calibration completed, but exact7.1.3
`ieee80211_init_cipher_suites()` rejected SW_CRYPTO_CONTROL with no explicit
cipher list at `main.c:1076`; WLAN registration stopped -EINVAL. No association,
CCMP RX or helper launch occurred. This is not a Wi-Fi support result.

The ONE consumed no-scan session completed its original observation and probe,
then the inherited C2 wrapper refused before log-export: an enabled but never
started helper defaults to `owned=true/safe=false`. The original guard also wraps
supplicant/quiescence/cycle exports, which have no leaf-produced records in this
no-scan branch. Do not rerun capture/startup/session or fake child quiescence.

## Exact continuation only

[Program](continue-ccmp1-no-scan.py) is default-off/offline. It admits only the
[ROOT-reported14-file/two-directory inventory](results/ccmp1-no-scan-inventory.json),
SHA256 `06d1e6b89974e46f96380394c235d2d38b91e85d64e087ab4849d718493fc84c`, and
[pinned ROOT never-started report](results/ccmp1-startup-custodian.json), SHA256
`b03329f75a3e3063389632c4281da4976eb8581c80a92e9e413cb5b0b7c584c0`.
Every original file, including consumed execution claim/SSH command/deployment,
is checked and retained unchanged; missing/extra/changed/symlinked evidence or
any pending/recovery/continuation attempt causes refusal. No generic resume lane.

The existing offline preparation otherwise rejects any claimed root. The program
therefore derives **only its preparation function**, with one exact source-pinned
assertion replacement: the fresh-root-only assertion becomes stricter exact
continuation-inventory admission. Every original private64/source/calibration/
supplicant/CLI/candidate/credential/installer validation remains. No original
file is edited or renamed. Regenerated claim/context and authenticated command
must equal the saved original ones; saved observation/probe are reclassified
locally, not reexecuted.

Original pinned base invoker is restricted to the pending original-budget phases:
`log-export`, `wiphy-probe`, `provider-probe`, `native-reboot`. The first device
phase is the original identity-bound seal/export. Pending original read-only
regression callbacks and full original snapshot/recheck follow. The C2/helper
wrapper is not called; no helper is launched, marked safe or falsely quiesced.
One appended `ccmp1-continuation-claim.json` consumes this continuation attempt,
not a second observation/session budget. Only a complete log-through-seal proof
allows ONE original identity/tool-bound recovery, followed by original v2 changed-
boot Gemian confirmation. Unknown/failed request, incomplete seal, altered saved
evidence or failed return remain failures; there is no retry/alternate path.

ROOT-only CLI, using the existing private environment/binder/candidate and current
claimed roots (never re-run prepare-ccmp.py):

```sh
P=experiments/2026-10-13-mt6797-wifi-native-delivery-probe
python3 "$P/continue-ccmp1-no-scan.py" --candidate "$CANDIDATE"
# After ROOT reviews the exact source and the actual offline preflight:
python3 "$P/continue-ccmp1-no-scan.py" --candidate "$CANDIDATE" --execute
```

Offline preflight does not consume the continuation claim or contact hardware.
Candidate leaf remains `candidate-94a281d899d4caac51419352eda7a2cb28fb2f773f1e3888b61e0b903fe91bec`.
Output is `session-ccmp1/ccmp1-continuation-result.json`; original failed files are
not overwritten. Only ROOT may execute this. The agent authored/tested code with
host mocks; no private64 preflight, live seal or recovery execution is claimed.

[Focused tests](tests/ccmp1-continuation-test.py) exercise exact admission
mutations, pending-only append order, original-file preservation, complete-seal
before one recovery, unknown-request/no-return, failed-return and repeat refusal.
They simulate the continuation executor, not real device/credential/boot checks;
ROOT's actual offline preflight and source review remain required.

## Consumed continuation and available-evidence recovery correction

ROOT executed exact9d9588b once. Seal/export and both pending read-only probes
completed; the original snapshot verified37 files. The logger had reached its
600000ms deadline before this attempt:1996 records/145634B, terminal exit1, all
available bytes stable/untruncated/preserved. Classification is
`log-export-inconclusive`, not a complete log through this seal. The extra
`proof.log_complete` requirement in9d9588b was stricter than the original recovery
contract and refused the unused native request. It must not be rerun or silently
patched. Its original files/result remain evidence of this negative outcome.

[Recovery-only program](recover-ccmp1-preserved.py) instead admits the exact
[later39-file/five-directory inventory](results/ccmp1-recovery-only-inventory.json),
SHA256 `c72deace5e4276d99189d289d2d3b3fab52a0972b1331ae7edf7dc4334018181`.
The original37-file PRE_RECOVERY_SHA256SUMS is pinned
`c467e5071ceafc87ccc702260cf5eeeabfa07683ec7cf01c9c7e4f5071a0d7e2`.
It reuses the reviewed offline private context and original finish
`verified_snapshot`/`recheck_export`, requiring complete **AVAILABLE** transport/
export/preservation, not a manufactured complete-log verdict. It binds all39
files before ONE still-unused native request; budget15s/131072B, same original
live identity/recovery-binary script and v2 changed-boot return. No reseal/export/
probe/startup/session retry, no emergency available-RAM-loss premise, no helper
quiescence fiction. Successful return is `returned-with-incomplete-log` with
log-complete/regression/compatibility explicitly false.

ROOT reviewed exact program9f947213 and performed its REAL private offline
preflight. [Focused host tests](tests/ccmp1-recovery-only-test.py) pass available/
incomplete-log recovery, incomplete-available refusal, all39 unchanged, unknown
request/no return, failed-return and no second attempt. Worker did not execute
hardware. ROOT-only, from the admitted current39-file state:

```sh
python3 experiments/2026-10-13-mt6797-wifi-native-delivery-probe/recover-ccmp1-preserved.py --candidate "$CANDIDATE"
python3 experiments/2026-10-13-mt6797-wifi-native-delivery-probe/recover-ccmp1-preserved.py --candidate "$CANDIDATE" --execute
```

## Separate source correction (approved source only)

The approved successor source adds only a static CCMP cipher array and its
pointer/count inside the new-mode registration branch, retaining SW_CRYPTO_CONTROL
and actual no-fallback gates. Initial PTK/GTK install uses the same CCMP suite;
no other cipher, radio effect, HIF/PN/budget/callback change is admitted. This
fix addresses registration only, not parser/hardware integrity/support proof.
Existing684 foundation plus0190/0191 remains686; the new logical fix follows it.
Canonical additions affect four historical implicit consumers; they are not new
build foundations. The17 historical named series remain unchanged. Future runtime
must be fresh CCMP2 roots/claims, never CCMP1 overwrite or identical CCMP1 retry.
