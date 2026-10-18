# C8: post-CLOSED receive-selection comparison

Status: installed to guarded boot2, full readback and clean shutdown verified;
owner selection and fresh mainline identity verified, no runtime result,
2026-10-18 UTC. The
[source decision](CLOSED_RX_SELECTION_COMPARISON.md) owns the hypothesis,
unique observation and branches. This tests cleanup sequence sensitivity,
not a proved repair or ordinary secure Wi-Fi. C7 is consumed; no unchanged retry.

## Real inputs and unchanged scope

One ordinary 32-job Buildbox build completed at `2026-10-17T23:58:27Z`,
modules off, from clean pushed input `3dafb066`. Profile
`mt6797-a53-wifi-ccmp-closed-select` selects C7's 692 ordered patches plus
0198, with identical 26 fragments. The canonical superset gains only 0198;
all existing named profiles and series remain unchanged.

| Input | SHA-256 / identity |
| --- | --- |
| Clean kernel input | `3dafb0666295bab558b02a3b7c0ce3e70efa1b9c` |
| Package inventory, 849 members | `3a995af8b51a5ecb112a5881bce34b192cf6636eafba41e600fed3698a2f604d` |
| Image.gz | `85bd82e28775a03f03772ed7585e439a5fbcdb013016a864829db81f8c5def27` |
| Resolved configuration | `483e0165368ce521f7f6e082e5acbc612c26badab7cacdc1e1cd60166f15c350` |
| Built MAC | `2c07e7024e45fc5142d49b6d0b02b3a3ae3b70d3cfb66db32c367c053b77dec1` |
| Built HIF | `078b08c781d59cfbd624ba1792138013f4f703c9beb019da96c814d7a341851d` |
| Proposal 0198 | `55fdbe7c1a738b9b3705ac467bcd2e9e2723378e4b7d8abca6fb58cf797c5f34` |
| Real candidate receipt | `2f67ae1087fc3b967af527718f7edbc1cdd83e76e111679f3e4ea5a5fcaea98c` |
| Raw boot.img / 12673024 bytes | `e616a08cef7a2cb376528f1de8b06946681ef3e18e5e90d5d6850ea35710bc0d` |
| Full boot2 / 16777216 bytes | `e3c347f1f45a942746dec025a5666242807c849fdc91f71c5fb9279c73e0ec66` |

The [build record](results/ccmp8-build-validation.json) records package and
source checks. Compilation covered the kernel and 123 DTBs; ordinary package
validation and fetch verified the exact inventory and provenance. No DT change
or schema test. The [compositor](build-ccmp-candidate-8.py) pins the real package,
C32 parent, configuration and exact private 64-member RAM root. No fabricated
receipt or substitute parent. All six private candidate members independently
match size/hash/mode. Config, DT and RAM identities equal C7 byte-for-byte;
only the kernel changes. The
[receipt](results/ccmp-stable-monitor-candidate-8.json) equals its
[runtime copy](runtime-ccmp8/results/candidate.json) byte-for-byte.

The receipt's integration source `fbe469ca374f0297d7f4dd1a641cdf1e75e79802`
is the bounded driver authoring snapshot, not a standalone Linux revision.
The project kernel input pins the complete build. Runtime release stays
`7.1.3-gemini-a53-wifi-ccmp-stable-monitor`; the release alone cannot distinguish
C7/C8. Installed full checksum and the receipt/source chain must bind the trial.

## Source and host validation

The actual-source ASan/UBSan fixture passes locally, on Linux against an
isolated child, and on Linux against the exact applied build source. Legacy
boot/requested-port tables are byte-identical to C7. Both selected ports,
both-nonempty priority, empty/capacity/deadline paths, all four observed mismatch
pairs and 1846 injected I/O faults pass, retaining complete transfers,
strict equality, no-copy, poison and poisoned second-call no-I/O. The exact MAC
routing block passes 80 flag/state/port cases with the option compiled on and
another 80 with it off. Patch reversal recovers C7; other driver/boot files,
scan and all MAC code outside routing/reporting remain byte-identical.

These are host behavior tests, not hardware FIFO or firmware crypto proof.
Linux uses the existing non-PIE sanitizer convention with 1 MiB output bounds.
Strict checkpatch has only the deliberately absent truthful DCO sign-off on
this non-certifying internal proposal: one error, zero warnings/checks.
Repository/profile checks pass for all 31 profiles.

Fresh C8 composition/config, receipt/wiring, no-scan ownership/failure,
installer-source and retained-session-source fixtures pass locally and on
Linux from clean published tooling `d16cad16`. The
standard one-cycle DHCP/ping/fresh-boot SSH leaf, source/recovery pins, private64
admission, helper ownership and finite budgets are unchanged.

## Installer review and device boundary

The [installer review](results/ccmp8-installer-review.json) compares the entire
603-line derived shell with frozen C7 under exact candidate/tool/predecessor
identity substitutions only. Bash syntax and ShellCheck pass. The historical
source pins and `0f0fc88c…` live boot2 guard are unchanged. Credential/calibration
storage remains separate from historical installer and recovery source roots.
No credentials were copied and no completed C7 tool was modified.

Read-only known-good Gemian preflight identified `3.18.41+` / aarch64, boot
`baff9c68-f74b-4797-8d28-1982211adba6`. This is not a deployment receipt.
Expected boot2 predecessor is C7 full `5b4405e0…`, or already-matching C8.
The actual installer must resolve logical boot2 from live GPT; prove inactive,
unmounted, non-root, exact-size, writable and stable-power state twice; then
sync/flush/full readback and clean shutdown. Owner physical boot2 selection
remains mandatory. Primary boot, boot3, GPT and calibration are outside scope.

Preparation claimed fresh session 8 only; capture 8 remains absent. After a
verified installation, copy only its actual deployment summary and complete
actual offline session preparation against the retained recovery cohort before
physical selection. Then verify changed boot/release/candidate identity, one
capture and one session with unchanged limits; preserve/seal/quiesce and make
one reviewed return. No unchanged C8 retry or automatic boot2 selection.

## Verified installation and physical handoff

The [deployment scalars](results/ccmp8-deployment-scalars.json) record the actual
guarded C7-to-C8 write from the expected Gemian boot. Both block identity gates
and stable power passed. Sync/flush/full readback matched C8 `e3c347f1…`;
clean shutdown and unreachability were confirmed, without a reboot. Executed
tooling is `d16cad165f209460a3f7901de76be0524a92f24f`.

The actual deployment summary is retained byte-exact, mode 0600, in session 8.
Its SHA-256 is `6aa9a4370a22e8f7d6d0e6a40c7046cb69a75376cd122bd5bf8e25c5868d26f0`
(944 bytes). Complete actual offline session preparation then passed against
the real candidate, real summary, retained historical source cohort and current
credential/calibration checkout. No Wi-Fi helper was started; its fresh boot
binding must be supplied only after the next mainline identity is verified.
Capture 8 is absent and no session execution claim exists.

The owner confirmed physical boot2 selection. Strict USB SSH then verified
new mainline boot `69e90265-77e3-4aa9-9610-5e7607647ab1`, the expected release,
aarch64 and the new selected-reader symbol. This corroborates the installed
full-readback/source chain; no Phase-A capture or runtime trial has run yet.
No unchanged retry is admitted. Ordinary
integrity/PN, key retirement/reuse, healthy reconnect and clean-profile
ten-minute SSH remain required by the delivery plan.
