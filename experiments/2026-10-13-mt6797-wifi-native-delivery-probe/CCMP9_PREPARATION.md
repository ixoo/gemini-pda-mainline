# C9: refused descriptor framing hints

Status: [consumed once](CCMP9_RESULT.md), 2026-10-18 UTC. The guarded
installation/preparation record below is historical. The
[source decision](REFUSED_RXD_FRAMING_SUCCESSOR.md) owns the hypothesis,
unique observation and branches. C8 is consumed. This is a bounded observation,
not a receive repair, crypto contract or maintained Wi-Fi claim.

## Real candidate

One ordinary 32-job Buildbox build completed at `2026-10-18T00:33:22Z`,
modules off, from clean pushed input `79a2c883`. Profile
`mt6797-a53-wifi-ccmp-framing-hint` selects exact C8 ordered 693 plus 0199,
with identical 26 fragments. Existing named profiles/series remain unchanged;
canonical order and all 32 profile checks pass.

| Input | SHA-256 / identity |
| --- | --- |
| Clean kernel input | `79a2c883f2feaff6f5ed4583d05998fe73924ab6` |
| Package inventory, 850 members | `e3f5a03788d2865f005b65b5b6b0ce193500916aa8f6f1eb3b6250651fdb7d15` |
| Image.gz | `e1d5c1d748dc6228e87a9ac1050ce7d3588bca9145d015f0c45c2df2e42f268f` |
| Resolved configuration | `483e0165368ce521f7f6e082e5acbc612c26badab7cacdc1e1cd60166f15c350` |
| Built MAC | `ec6f81b87b9a81465c88ba217af6e6ff2b6e9178e1adaaba454107576b77659b` |
| Built HIF | `5b499e5bab26811bfabfc5dc23ff02f8632d9cc0fd6ec7480eaeed23e9161a3e` |
| Proposal 0199 | `c3dba8b04ec1a9c3f509e497d915dc9b487d74637f1670827715beb79fce461a` |
| Real receipt | `a8f83b101371f8fb81f93c94777bf551d95140c5dba408d463f00475397a81c8` |
| Raw boot.img / 12673024 bytes | `9de1555fa4a263a5dc7f0519635196bcfb8b5b35b032947dab733b7e354fe867` |
| Full boot2 / 16777216 bytes | `851a465efddff08895b726767b95d74a59a690ab648222c2dc67a936a06f6f61` |

The [build record](results/ccmp9-build-validation.json) records provenance and
built source hashes. Kernel and 123 DTBs compiled; ordinary package validation
and fetch passed exact inventory/checksums. No DT change or schema test.
The [compositor](build-ccmp-candidate-9.py) uses the real package and verified
C32/private64 parent. All six private members independently match hash, size
and mode. Config, DT and RAM equal C8 byte-for-byte; only the kernel changes.
The [receipt](results/ccmp-stable-monitor-candidate-9.json) equals its
[runtime copy](runtime-ccmp9/results/candidate.json) byte-for-byte.

Integration source `614688341c84b9b29aacd9ab7d158155b316c6bd` is the bounded
driver authoring snapshot, not a standalone Linux revision. The full build is
pinned by its project input. Runtime release remains
`7.1.3-gemini-a53-wifi-ccmp-stable-monitor`; release alone cannot identify C9.
Bind the runtime to installed full readback, actual boot and source chain.

## Validation and retained scope

Actual-source ASan/UBSan tests pass locally, on Linux in an isolated child,
and against the exact applied build source: 3956 paired cases, 3632 injected
faults, plus retained C8 selected/legacy cases. Both ports, three APIs, five
observed mismatch pairs, full-base/type/capacity bounds, valid-zero values,
incomplete reads and expiration at the guard after full transfer pass. No-copy,
poison, no second I/O and cleared hint validity on the later call pass.
Parent/child I/O/publication tables match. Actual MAC formatter and classifier/
helper negatives pass; the extra hint cannot manufacture a pass or fault.
Other driver files and all MAC code outside the formatter are byte-identical.
Linux keeps the existing non-PIE sanitizer convention and 1 MiB output bounds.

Strict checkpatch reports only the deliberately absent truthful DCO sign-off:
one error, zero warnings/checks, internal non-certifying proposal. Repository
checks pass. Synthetic cases prove host behavior, not firmware descriptor
validity, conversion, integrity, replay, key retirement or FIFO enforcement.

Fresh receipt/wiring, composition/config, no-scan failure/ownership,
installer-source and retained-session-source fixtures pass locally and on
Linux from clean published tooling `e7b05705`. C8 arbitration,
all hardware acquisitions, complete transfers/equality/poison, deadlines,
all-RX512/1MiB/delivery64/wall10s-or-lower, private64 admission, PSK-bound
one-cycle leaf, helper ownership and recovery source pins remain unchanged.
No ordinary PN bypass, payload/address/key/PN logging or extra mode command.

## Installer and next physical boundary

The [installer review](results/ccmp9-installer-review.json) verifies the full
603-line derived shell against frozen C8 under exact candidate/tool/predecessor
identity substitutions only. Bash syntax and ShellCheck pass; the historical
source pins and `0f0fc88c…` live-GPT guard are unchanged. Credential/calibration
storage remains separate from historical source roots. No credentials copied.

Read-only Gemian preflight matched `3.18.41+` / aarch64 and C8's returned boot
`8cffe5a0-4a2e-4441-aa93-1cc8be97cd59`. This is not deployment proof. Expected
boot2 predecessor is C8 full `e3c347f1…`, or already-matching C9. Require the
reviewed live identity/GPT/inactive/unmounted/non-root/size/power gates, exact
full readback and clean shutdown before owner physical boot2 selection.
No primary boot, boot3, GPT, calibration or whole-device write is in scope.

Preparation claimed fresh session 9 only; capture 9 remains absent. After a
verified installation, copy its actual summary and complete actual offline
session preparation with the retained source cohort before physical selection.
Then verify changed mainline identity, run one capture and one session under
unchanged limits, preserve/seal/quiesce and make one reviewed return. If this
fails earlier or yields no eligible hint, record the missing observation; no
unchanged retry, new read, credit refund or deadline extension follows.

## Verified installation and physical handoff

The [deployment scalars](results/ccmp9-deployment-scalars.json) record the actual
guarded C8-to-C9 write from the expected Gemian boot. Both block identity gates
and stable power passed. Sync/flush/full readback matched C9 `851a465e…`;
clean shutdown and unreachability were confirmed, with no reboot. Executed
tooling is `e7b057059ad3cd479a169860a40765973bc4b8e1`.

The actual deployment summary is retained byte-exact, mode 0600, in session 9.
Its SHA-256 is `15099957f1e2dbe6856d32e5f182ce9665af5e5f4e7b4910439567f15f4e25f8`
(944 bytes). Complete actual offline session preparation passed with
that real summary, candidate, current credential/calibration checkout and
separate retained recovery source cohort. No Wi-Fi helper was started; bind
it to the fresh boot only after live mainline identity is verified.
At that preparation boundary, capture 9 was absent and no session execution
claim existed.

Owner subsequently selected boot2; [C9 ran once](CCMP9_RESULT.md) and returned
to independently confirmed Gemian. This preparation record does not authorize
an unchanged retry. Ordinary integrity/PN,
GTK/rekey/key retirement, healthy reusable lifetimes and clean-profile
ten-minute SSH remain required for the complete Wi-Fi goal.
