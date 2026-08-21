# MediaTek watchdog raw boot-status capture

## Claim boundary

The patch owns only a preserved observation:

```text
audited MT6797 TOPRGU status word -> immutable raw snapshot
```

It does not interpret the word as reset authority. It has no production A34
caller and cannot open or initialize the A72 lifecycle.

## Capture order and ownership

`struct mtk_wdt_dev` remains the sole owner. When the default-off capture
option is enabled, only match data for `mediatek,mt6797-wdt` advertises the
audited status register. Probe performs exactly one `readl()` of offset `0x0c`
after `devm_platform_ioremap_resource()` succeeds and before IRQ setup,
watchdog registration, or `mtk_wdt_init()`.

No capture occurs for unreviewed MediaTek variants. No later resume, restart,
reset-controller, watchdog, or consumer path reads the register again.

## Snapshot contract

The public typed snapshot contains only:

- the complete raw 32-bit word; and
- explicit validity.

The capture helper is first-write-wins. It publishes raw data before validity
with release ordering. The copy helper observes validity with acquire ordering,
copies the raw word with `READ_ONCE()`, and never returns stale caller data on
an invalid snapshot. The device getter returns `-EINVAL` for invalid arguments,
`-ENODEV` before driver data exists, `-ENODATA` before a supported capture, and
zero only with a valid immutable copy.

The API does not name individual bits, expose a “safe reset” boolean, or map
raw zero or any watchdog bit to platform/external-reset provenance.

## Hardware-free proof

Four focused KUnit cases exercise pure memory behavior:

1. an invalid store rejects and clears a prefilled output;
2. an exact nontrivial 32-bit word round-trips;
3. every individual bit round-trips from a fresh store; and
4. a second capture cannot replace the first value.

The tests instantiate no platform device and perform no MMIO, watchdog,
reset-controller, provider, firmware, or CPU operation.

## Explicit exclusions

The patch adds no reset classifier, ram-console mapping, command-line boot-
reason reader, A34 evaluator call, lifecycle publication, membership change,
transaction or provider call, I2C operation, P27/P28 effect, P30 arm, firmware
call, PSCI call, CPU_ON, CPU_OFF, boot-veto change, boot candidate, boot2 write,
or device action. A valid raw snapshot cannot make the A34 evaluator input
true without a later independently reviewed combiner.
