# Legacy DA921x resource-only provider design

## Boundary

The existing `dlg,da9214-legacy` node remains identification-only and has no
`regulators` child or supply phandle. A separate manifest profile enables
`CONFIG_REGULATOR_DA9213_LEGACY_PROVIDER`; this symbol is off in the default
and prior identification/lifecycle profiles. The provider therefore cannot
become an accidental default or create an A72 consumer.

After the exact two-pass, seven-sample identity transcript succeeds, the
provider profile registers two internal regulator descriptors. Registration
does not call any regulator operation and does not perform a register-data
write. The descriptors intentionally omit Device Tree init data and all
constraints until the hardware ownership audit is complete.

## Read-only operation contract

Each descriptor implements only:

| Operation | Contract |
| --- | --- |
| `list_voltage` | Pure linear table, 300000–1570000 µV in 10000 µV steps. |
| `get_voltage_sel` | One direct primary-address combined read of `0xd7` (Buck A) or `0xd9` (Buck B), masked to `0x7f`. |
| `is_enabled` | One direct primary-address combined read of `0x5d` (Buck A) or `0x5e` (Buck B), masked to bit 0. |

The raw read helper locks the root adapter, issues exactly one pointer-write
message followed by one one-byte read message through `__i2c_transfer()`, and
rejects partial results. It never selects a page, uses regmap, retries,
modifies a register, or falls back to SMBus.

All writable regulator operations are absent: no `set_voltage_sel`,
`enable`, `disable`, `set_mode`, `set_current_limit`, GPIO enable, IRQ, PM,
consumer, CPUHP, PSCI, or A72 call exists in this slice.

## Ownership and failure

The identification driver remains the owner of the two I2C client addresses.
The provider owns only the lifetime of its read-only descriptor objects. A
failed descriptor registration returns the error and managed cleanup removes
any earlier software registration; no inverse register operation is attempted.
A failed or uncertain read returns the I2C error to the regulator core and
changes no state. The provider is not allowed to infer rail ownership from
`is_enabled` or a selector value.

## Exit criteria

Offline exit requires:

1. the provider symbol is isolated to the named profile and disabled in the
   existing identification/lifecycle profiles;
2. the exact canonical-series and manifest audit passes;
3. strict static review finds only the three read-only operations and no
   writable or A72 path;
4. the source patch applies and passes focused checkpatch; and
5. the clean pushed commit passes the full Buildbox package validation.

This does not authorize a kernel candidate, a boot2 write, a hardware probe,
or a consumer request. The next design must establish a genuine regulator
consumer identity and transaction owner before any bounded write or CPU_ON
path is considered.
