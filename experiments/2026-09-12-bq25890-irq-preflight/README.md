# BQ25890 interrupt lookup before hardware initialization

Status: source review, injected regression and isolated Buildbox compilation
pass. This unsigned preparation topic enables no Gemini board device and does
not select a boot candidate.

## Problem and change

The upstream BQ25890-family driver resolves its fallback GPIO interrupt after
`bq25890_hw_init()`. A missing GPIO or deferred GPIO/IRQ provider therefore
fails probe only after charger configuration. The default initialization
resets the chip; `linux,skip-reset` instead explicitly enables charging.
Initialization also disables the charger watchdog, reads or programs the
selected limits, obtains state and configures ADC conversion. Neither
`linux,skip-reset` nor `linux,read-back-settings` makes probe read-only.

For example, GPIO lookup returning `-EPROBE_DEFER` currently follows successful
hardware initialization. A later probe attempt can repeat those changes before
the interrupt provider is ready. This is a source-backed failure-path defect,
not a reproduced charging fault on Gemini.

The [single patch](../../patches/upstream-4d7d9486/power-supply/0001-power-supply-bq25890-resolve-IRQ-before-initializing.patch)
moves existing interrupt resolution and its error return before initialization.
It preserves the chip-ID and firmware-property checks, supplied positive IRQ
handling, GPIO input request, error codes and initialization body. The threaded
IRQ request stays after initialization and power-supply registration so its
handler sees initialized state. Later registration/request failures still
follow charger writes; this change neither adds rollback nor makes all failed
probes free of effects. GPIO acquisition itself may configure a GPIO input.
The pinned I2C core restores `client->irq` from `client->init_irq` at the start
of each probe, before calling the driver. A subsequent core-driven probe thus
does not inherit the fallback IRQ assignment from a failed driver attempt.

The [Gemian identity result](../2026-07-12-charger-power-recovery/CHARGER_ID.md)
matches BQ25896, a variant supported by this driver. Gemini's IRQ wiring,
board limits and protection remain unresolved. This correction is a generic
prerequisite for future integration, not permission to probe that board.
The selected Wi-Fi candidate and its finite boot budget remain unchanged.

## Inputs and overlap

The [source inventory](source-inputs.json) records exact upstream URLs, sizes
and hashes. The selected compile base is the already cached, manifest-pinned
`4d7d9486c04d917265f64c55bd23b2cc4fe7749c`. Its complete driver matches both
mainline `cba2348ab114391f5b1a00fa65c5b739f13f0563` and power-supply `fixes`
`a58cbc8b36ec0cd00d2ba3de7d003de818a27523` observed on 2026-09-12.
Power-supply `for-next` `4fc88ba435dadbc05990951e3f3fbd8ccd2df140` differs only
by correcting a suspend-comment typo. All four retain this probe ordering,
and the patch applies to each. A bounded public search for BQ25890 IRQ,
initialization and probe deferral found no matching ordering fix; refresh the
final outgoing base and public overlap before submission.

The original [driver introduction](https://github.com/torvalds/linux/commit/4aeae9cb0dad117f055add68c48decaf489aecf3)
already places hardware initialization before IRQ lookup. Its added driver
file and exact commit/title were checked. The eventual human-certified export
should include `Fixes: 4aeae9cb0dad ("power_supply: Add support for TI BQ25890 charger chip")`.
The unsigned archive tested below remains byte-identical to its build input.

The isolated `bq25890-irq-compile` profile selects only this patch and builds
the driver with I2C, GPIO, power-supply and regulator support. All 205 existing
profile definitions, selected patch bytes/order and fragment bytes are
unchanged. No binding, DT consumer, active Wi-Fi source or package is altered.

## Validation

The [host regression](test-probe.py) compiles the actual complete probe and
IRQ-lookup functions with injected GPIO, mapping, identity, property and
initialization results. Eleven cases cover supplied IRQs, missing/deferred
GPIOs, failed/deferred mappings, successful lookup, initialization failure,
early identity/property rejection and the unchanged later IRQ-request failure.
It checks returned errors, call counts and resource resolution before entry
to hardware initialization. The unpatched source compiles and fails the
missing-IRQ case. Patched base and `for-next` sources pass all eleven cases.
The test substitutes initialization and framework calls; it does not validate
GPIO-core cleanup, physical register effects or electrical behavior.

```sh
python3 experiments/2026-09-12-bq25890-irq-preflight/test-probe.py \
  /path/to/prepared/linux/drivers/power/supply/bq25890_charger.c
KERNEL_PROFILE=bq25890-irq-compile ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=bq25890-irq-compile ./scripts/buildbox fetch-package
```

Strict checkpatch passes with its pinned spelling/const tables and only
`MISSING_SIGN_OFF` excluded. The [Buildbox receipt](compile.json) binds the
successful compile at `dbcc256fb248f02e1c7ce25fdb31c10a43ce584e`. The charger
object compiled with all six required configuration options enabled, its probe
and driver symbols are linked, and the build log has zero compiler warning or
error lines. The exact prepared source matches the locally tested source and
passes all eleven regression cases on Buildbox. Remote package validation and
the fetched package's inventory/checksums pass.

Local repository checks and the [hosted Linux checks](https://github.com/ixoo/gemini-pda-mainline/actions/runs/34719211474)
pass for the build-input commit, including the Linux-only provenance fixtures.
No new schema check is required because no binding or DT changes. No mainline
device test, charger transaction, charge-policy change or kernel boot occurred
for this correction. A bounded Gemian power-status read still found insufficient
installation power; no Wi-Fi installation or additional identity-register read
was attempted.

## Publication boundary

The inspected driver declares `GPL-2.0-or-later`; only a moved six-line block
and ordinary diff context are included. The format-patch archive records a
synthetic, non-certifying author and LLM assistance. Human authorship review,
truthful DCO certification and final maintainer discovery remain required.
The pinned maintainer file routes the driver to Sebastian Reichel and
`linux-pm` through the power-supply tree. No upstream message has been sent.
Remove this local patch when an accepted equivalent reaches the selected
upstream baseline and the regression passes there.
