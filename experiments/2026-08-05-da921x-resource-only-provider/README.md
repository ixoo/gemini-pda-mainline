# Experiment: legacy DA921x resource-only provider

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-05-da921x-resource-only-provider` |
| Status | `Buildbox-validated` (compile-only; no hardware action) |
| Subsystem | legacy DA9213/DA9214/DA9215 regulator provider boundary |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date | 2026-08-05 America/New_York |
| Claim | `PARTIAL_RESOURCE_ONLY_PROVIDER` |

## Question

Can the separated legacy-family driver register a default-off, resource-only
provider that reports only read-only selector and enable state, while retaining
the exact identification transcript and exposing no writable operation,
consumer, IRQ, A72 hook, or hardware write?

## Result

Patch 0170 adds an explicit `CONFIG_REGULATOR_DA9213_LEGACY_PROVIDER` gate.
When selected, the existing 14-read identity transcript must complete before
two internal Buck descriptors are registered. Their only operations are
`list_voltage`, `get_voltage_sel`, and `is_enabled`; selector reads use the
primary direct-address register bytes `0xd7`/`0xd9`, and enable reads use
`0x5d`/`0x5e`. Every read uses one combined two-message transaction under the
root-adapter lock. No setter, enable, disable, mode, current-limit, IRQ,
consumer, A72, page-selector, or write path is present.

The provider has no Device Tree consumer or child node. Its two descriptors
are intentionally internal and have no constraint init data. This is a
resource-only provider registration experiment, not rail-ownership or A72
support.

## Provenance

- Patch: [0170](../../patches/v7.1.3/0170-regulator-add-legacy-DA921x-resource-only-provider.patch)
- Prepared source commit: `f2e79a385`
- Parent: [legacy identification-only integration](../2026-07-29-da921x-legacy-bind/README.md)
- Profile: `da921x-resource-only-provider`

## Safety and nonclaims

This remains compile-only. It performs no device access, boot, partition read,
partition write, regulator request, or CPU request. Registration is default-off
and isolated to the named profile. The provider has no writable regulator
operation, so it cannot select a voltage, change enable state, alter mode or
current limit, or perform rollback. The read-only methods do not establish
that the register meanings, rail ownership, constraints, or resume behavior
are correct on hardware. CPU8 and CPU9 remain disconnected.

## Evidence

- [DESIGN.md](DESIGN.md) defines the resource-only boundary.
- [Static validator](scripts/validate.py)
- [Source validation](results/source-validation-20260805.txt)
- [Mutation validation](results/mutation-validation-20260805.txt)
- [Buildbox validation](results/buildbox-validation-20260805.txt)

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-05-da921x-resource-only-provider/scripts/validate.py
```

## Conclusion

`PARTIAL_RESOURCE_ONLY_PROVIDER` is Buildbox-validated for the exact pushed
commit. This closes only the source/provider-registration boundary; it does
not establish hardware support. The real provider-owner transaction, P24/CPU_ON,
rollback, safe-off, and all device gates remain closed.
