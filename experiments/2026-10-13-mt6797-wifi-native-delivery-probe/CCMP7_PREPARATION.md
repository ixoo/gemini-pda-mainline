# C7: validated terminal credit-pair observation

Status: built, package-validated, privately composed and offline tooling-tested;
not installed or booted yet, 2026-10-17. The
[source/experiment decision](CCMP7_CREDIT_OBSERVATION.md) owns the hypothesis,
unchanged finite protocol and interpretation branches. The full objective
remains ordinary secure Wi-Fi with ten-minute SSH and healthy reconnect.

## Real inputs and candidate

One ordinary Buildbox build completed at `2026-10-17T23:26:43Z` from clean,
pushed input `e7c669a0c4b6861219045da2540a37aa1cfbf132`, 32 jobs, modules off.
Profile `mt6797-a53-wifi-ccmp-credit-observe` selects C6's 691 ordered patches
plus 0197, with identical 26 fragments. Resolved configuration, C32 parent DT
and private RAM root match C6 byte-for-byte.

| Input | SHA-256 / identity |
| --- | --- |
| Package inventory, 848 members | `5f2dea5afb596c90ab545dd2ff0ec5fb4586b79f0d1b08bdaf3f013947bd575c` |
| Image.gz | `81747e79ea64b4f45d1f2b4696fbf83a3002fe30a8e7631601c5871a0e14e7ad` |
| Resolved configuration | `483e0165368ce521f7f6e082e5acbc612c26badab7cacdc1e1cd60166f15c350` |
| Built MAC | `7faea3f09d29144e8cedd2b12558cfead70c7d4cd6a85916bb570e86624ef4e8` |
| Proposal 0197 | `e3b48d3b9b1c016a1d346379b24c54c2423c61e4900ed53d13cbc5eef73a41c8` |
| Real candidate receipt | `734b236535fe1f0f3309795c16892c42bf4a4c8f87bd95a83da778c81d85a40a` |
| Raw boot.img / 12673024 bytes | `ffa22883d2bb8db253816ec88989b247bb9b4a4c12231f2663b94aab49bfd928` |
| Full boot2 / 16777216 bytes | `5b4405e0060111173da65445e3e4b1ffcd13347c9cf0ddb23d36d85140665ee6` |

The [build record](results/ccmp7-build-validation.json) contains the complete
patchset and test-runner identities. Ordinary fetch verified the validated
package. The [compositor](build-ccmp-candidate-7.py) pins that real package;
all six private candidate members were independently size/hash/mode checked.
The [receipt](results/ccmp-stable-monitor-candidate-7.json) equals its
[runtime copy](runtime-ccmp7/results/candidate.json) byte-for-byte.
The source commit in the receipt denotes the bounded MAC authoring snapshot,
not a standalone Linux revision; the project input pins the whole build.

## Validation and sanitizer-runner correction

The actual source fixture passed locally and on Linux in an isolated child.
The initial applied-build-source Linux PIE sanitizer run emitted repeated
`DEADLYSIGNAL` without an actionable stack and was killed at 30 seconds. Its
original log identity is retained privately. The driver file was unchanged.

The runner now uses the existing actual-HIF fixture's `-fno-pie -no-pie`
Linux convention, keeps ASan/UBSan enabled, and limits each output file to
1 MiB with an 8192-byte failure tail. The same applied source passes with
those flags. The failure's exact sanitizer-runtime cause is not established;
no report was reclassified as a driver pass or hidden. Both results are
recorded. No binding/test-only kernel rebuild.

The fixture verifies byte-identical timeout gates after tag removal,
unchanged HIF/ledger/boot/RX files, exact patch reversal, raw versus pending
credit state, no refund/input mutation and once-only four-line output.
Kernel/DTB compilation and package validation passed. Strict checkpatch has
only the deliberately absent truthful DCO sign-off on this non-certifying
internal proposal, zero warnings/checks. No DT or schema change.

Fresh C7 composition/config, receipt/wiring, no-scan failure/ownership,
installer-source and retained-session-source fixtures pass locally. The
namespace, real C32/private64 guards, PSK-bound one-cycle leaf, helper,
recovery hashes, budgets and current credential roots remain unchanged.
No ordinary PN bypass, new monitor command or crypto route is selected.

## Installer and session gates

The [installer review](results/ccmp7-installer-review.json) verifies the full
derived C7 shell against frozen C6 under exact candidate/tool/predecessor
identity substitutions only. Bash syntax and ShellCheck pass. Historical
installer-source pins and the `0f0fc88c…` device guard remain unchanged.

Known-good Gemian was freshly observed as `3.18.41+` / aarch64, boot
`29fa9106-1c76-408e-b735-42cc2bc183ae`. That is a preflight, not a replacement
for live guards. Expected boot2 predecessor is C6 full `fbb5eb72…`, or an
already matching C7. Resolve logical boot2 from live GPT; require inactive,
unmounted, non-root, exact-size, stable-power and block-identity checks,
sync/flush/full readback, then clean shutdown. Owner physically selects boot2.

Keep the current credential/calibration checkout separate from the exact
historical source stores: export `GEMINI_INSTALLER_SOURCE_ROOT` and the
outside-checkout `GEMINI_SESSION_SOURCE_ROOT` throughout the tooling chain.
No keys or calibration were copied. Use Python 3.13 for CLI and children.
Prepare claims fresh session 7 only; capture 7 stays absent until executed.
Copy only the actual deployment summary after a verified installation.

Before physical selection, complete actual offline session preparation with
that real summary and retained source cohort. After selection, verify changed
boot/release/candidate chain, then one capture and one actual session. Existing
terminal symbol is shared with C6 and corroborates the release only; the
installed full checksum and the new credit-observation line bind C7.
Preserve/seal/quiesce and perform one reviewed return on every admitted
outcome. No C6/C7 repeat or automatic reboot/alternate partition.
