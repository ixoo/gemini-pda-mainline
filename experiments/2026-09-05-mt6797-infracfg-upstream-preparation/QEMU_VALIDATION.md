# Exact-package QEMU acceptance preparation

Status: helper and host refusal fixtures prepared for integrator review. No
QEMU guest or schema command has run under this protocol. This does not select
a device candidate or reopen any physical session.

## Identity and scope

[qemu-contract.json](qemu-contract.json) pins the validated package built from
`4ec63076aeb6388ba24b33ee20afcf19ced541e1`: inventory SHA-256
`8393a89ef3dbdb3bbae967d6adc78cf5a1cd907c21f21e9ba2efc015ba041917`, release
`7.3.0-rc1-mt6797-infracfg-upstream-kunit`, Image.gz SHA-256
`c0a7e412f6d778ae523f1dfd63f9c54db91e269fe45b06d7411663dbf88dcc1e`.
The retained basename starts `linux-7.1.3-gemini-` because the publisher used
its global version label. Preserve that exact package: provenance and digests,
not the directory label, determine identity. This helper does not fix or rename it.

The [runner](scripts/qemu-check.py) validates all 132 inventory members,
rejects missing/extra/symlink/special entries and pins complete source, patch,
configuration, clean repository revision and enabled KUnit identities. There is
no alternate-contract CLI. Package checking is the default and launches nothing.
Traversal errors, including an unreadable extra subtree, refuse the inventory;
an omitted subtree is never treated as an empty directory.

The [fixtures](scripts/test-qemu-check.py) use synthetic tiny packages, KTAP
and Python subprocesses, never QEMU or kernel builds. They exercise complete
results in either suite order, missing structural lines, duplicated/truncated
results, wrong cases/plans/release/command line, skips/failures/diagnostics,
wrong poweroff/exit/timing, inventory/provenance changes, unsafe paths, handshake
and real TERM-resistant process cleanup. Temporary roots are context-managed.
Correction fixtures additionally cover a descendant that closes its pipes and
outlives a zero-exit leader, handled runner interruption, atomic receipt failure,
implicit configuration exclusion and privileged-executable refusal. A Linux-only
fixture kills the coordinator and checks direct-child parent-death containment.

## Reviewed execution proposal

Run the fixtures on Linux before execution. Once this helper is reviewed, use
its exact published revision with the retained package on Buildbox. Create one
managed evidence parent under the ignored artifact root, then use one new child
named `infracfg-qemu-4ec63076-attempt-1`. Keep that attempt directory even on
failure. Do not choose a new child to bypass consumed-attempt review.

```sh
python3 experiments/2026-09-05-mt6797-infracfg-upstream-preparation/scripts/test-qemu-check.py
python3 experiments/2026-09-05-mt6797-infracfg-upstream-preparation/scripts/qemu-check.py \
  --package "$retained_package"
# Only after integrator review of the helper and exact Linux fixture results:
python3 experiments/2026-09-05-mt6797-infracfg-upstream-preparation/scripts/qemu-check.py \
  --package "$retained_package" --execute \
  --output "$evidence_parent/infracfg-qemu-4ec63076-attempt-1"
```

The argv is fixed: `virt`, TCG, `max`, two CPUs, 512 MiB, Image.gz and the
admitted command line. No disks, networking, initramfs or supplied board DTB;
QEMU generates the virtual DT. No graphical display or human monitor exists.
`-no-user-config` disables implicit configuration loading; `-nodefaults` alone
only disables default devices and does not establish that configuration boundary.
Serial and stderr go to bounded separate logs. QEMU executable digest/version,
neutralized argv, events, elapsed time, exit status and log digests are retained.

A QMP channel supplies independent poweroff attribution. Start paused (`-S`),
receive the greeting, enable QMP capabilities, then issue exactly one `cont`.
Only those two commands are sent; no reset, poweroff or quit request is sent.
QMP is a host control/event channel, not guest networking or a userspace agent.
The [QMP reference](https://www.qemu.org/docs/master/interop/qemu-qmp-ref.html#event-SHUTDOWN)
provides the guest/reason fields used to distinguish guest shutdown from host
termination. `-no-reboot` prevents a guest reboot becoming another attempt.

The 45-second wall ceiling includes QEMU startup and handshake. Failure, timeout
or malformed output terminates the process group, with five seconds before
KILL. Serial/stderr file sizes are capped at 2 MiB each, QMP at 64 KiB; core
files are disabled. These limits supplement, not extend, the admitted time budget.
A timed-out run fails even if complete passing test lines appeared first.

Always inspect and clean the owned process group, including after a zero-exit
leader and stdout EOF. A surviving group refuses acceptance even if cleanup
successfully kills it. TERM is followed by KILL within the five-second grace;
a final one-second bounded reap does not extend the guest's runtime allowance.
SIGTERM, SIGHUP and SIGINT received by the runner are recorded rather than raised
inside process creation or cleanup. Repeated handled signals cannot bypass group
cleanup or final atomic, fsynced `INCOMPLETE` receipt publication. The initial
receipt is also durable before launch. An interrupted replacement preserves the
prior complete receipt instead of truncating it in place.

On Linux the direct QEMU child sets `PR_SET_PDEATHSIG=SIGKILL` before exec and
checks that its parent did not die before setup. Non-setid and no-file-capability
execution are required because privileged exec can clear that setting. This
contains the direct guest if the coordinator is abruptly killed; it cannot
publish a final receipt after uncatchable SIGKILL, so the initial incomplete
receipt remains authoritative. The
[Linux API contract](https://man7.org/linux/man-pages/man2/PR_SET_PDEATHSIG.2const.html)
clears the setting in forked descendants. This is not a cgroup or arbitrary
descendant-tree guarantee: a separately forked descendant could survive an
uncatchable coordinator kill. The reviewed QEMU invocation has no external
helper/service arguments. Any dependency on external descendants requires a
separate containment review. The surviving-descendant fixture exercises cleanup
robustness, not an observed QEMU child-process behavior.

Acceptance requires an exact release/command line, one complete top-level KTAP
plan with the two named suites and four exact cases each, no failures/skips/
unexpected structural records or kernel diagnostics, and a power-down marker
after the final result. It also requires QMP guest shutdown (`guest=true`,
`reason=guest-shutdown`), zero QEMU exit within budget, empty QEMU stderr and
unchanged package inventory after exit. No QMP guest reset/panic/watchdog event
is allowed. Every other outcome is refusal/incomplete and retains its evidence.

This strict parser may reject an unforeseen harmless log format. Review the
captured evidence and revise the contract prospectively; do not weaken the
classifier or rerun automatically to obtain a pass. A pass establishes pure
translation/descriptor arithmetic only, not provider registration, reset pulses,
unbind/rebind or MT6797 hardware behavior.

## Focused schema protocol for review

Reuse only the retained source
`/workspace/gemini-pda/src/linux-7.3-rc1-series-mt6797-infracfg-upstream-kunit-source`
and build
`/workspace/gemini-pda/build/linux-7.3-rc1-mt6797-infracfg-upstream-kunit`.
No source extraction, kernel recompile or package overwrite is part of this
protocol. Schema recipes can generate host tools, schemas and DTBs in that build
directory; execution requires coordinator admission and the normal build lock
because it mutates shared build outputs. Refuse an active build or changed state.

Before execution, verify prepared-source state and the full source-integrity
manifest with the existing repository helper; compare every changed-file hash
in [the generation receipt](results/coherent-topic-generation.json). Match the
build `.config`, kernel release, Image.gz and the four production/test object
files (`drivers/clk/mediatek/{reset,reset-test,clk-mt6797,clk-mt6797-reset-test}.o`)
to the integrator's exact build receipt. Pin their before digests; record
after digests and refuse unintended kernel/object/config changes. Do not call a
source preparation command to repair a mismatch.

```sh
python3 scripts/source-tree-integrity verify "$retained_source"
```

Record Python, dtschema package, `dt-doc-validate`, `dt-validate`, `dt-mk-schema`,
Yamllint, make, DTC and cross-compiler versions/paths before starting. Missing
required tools or missing diagnostics is refusal; do not install/update tools
silently. Use explicit `ARCH=arm64`, `CROSS_COMPILE=aarch64-linux-gnu-`, the same
`O=` path, and `DT_SCHEMA_FILES=clock/mediatek,infracfg.yaml` for both targets:

```sh
make -C "$retained_source" O="$retained_build" ARCH=arm64 \
  CROSS_COMPILE=aarch64-linux-gnu- DT_SCHEMA_FILES=clock/mediatek,infracfg.yaml \
  dt_binding_check
make -C "$retained_source" O="$retained_build" ARCH=arm64 \
  CROSS_COMPILE=aarch64-linux-gnu- DT_SCHEMA_FILES=clock/mediatek,infracfg.yaml \
  dtbs_check
```

Proposed ceiling: one invocation of each target, one make job, 300 seconds per
target plus five-second termination grace, each with a 16 MiB diagnostic cap.
Capture complete stdout/stderr and exit status independently of pipelines.
These are prospective schema budgets, requiring review before execution.

Require diagnostics showing the selected binding was processed and both
`mediatek/mt6797-evb.dtb` and `mediatek/mt6797-x20-dev.dtb` were validated.
If incremental make omits attribution, do not infer validation from silence.
A reviewed direct `dt-validate` invocation against the generated processed schema
and those two exact DTBs may supply explicit attribution without a kernel build.
Record the precise command and selected-schema identity before using it.

Inspect each resulting DTB with the retained DTC tools: require one compatible
`mediatek,mt6797-infracfg` node and `#reset-cells = <1>`. Verify the new public
header's only reset ID definitions are thermal 0 and PMIC-wrapper 1, including
its exact receipt digest. DTB structure alone does not establish schema validity.

Zero status alone is insufficient. Every diagnostic must be reviewed; do not
exclude unrelated messages without an explicit pinned baseline. Missing tool,
wrong source/build, timeout, output truncation, missing target/schema attribution
or an unclassified diagnostic leaves the result inconclusive/refused. Preserve
logs and identities before any follow-up. Do not recreate an unpatched source
copy merely to classify warnings. Root owns subsequent baseline admission.
