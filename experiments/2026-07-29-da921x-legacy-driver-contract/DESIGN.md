# DA9213/DA9214/DA9215 legacy-family driver contract

## Decision

The first implementation is a separate, identification-only I2C driver for
the non-A DA9213/DA9214/DA9215 register generation. It does not share the
DA9211/A-family probe, paged regmap, device-ID read, regulator registration, or
IRQ path.

The initial Gemini profile selects only the DA9214 variant. It binds only
after the exact fixed tuple already observed on the named board is returned
twice. A successful bind means only that the fixed read-only board contract
matched. It does not identify the silicon uniquely and does not create a
regulator provider.

## Upstream and local naming

The proposed source unit is `drivers/regulator/da9213-regulator.c`, with
Kconfig symbol `REGULATOR_DA9213`. It models the common non-A
DA9213/DA9214/DA9215 register generation and keeps variant topology in match
data rather than in board-specific code.

The isolated integration profile uses the following programming-model
compatibles:

```text
dlg,da9213-legacy
dlg,da9214-legacy
dlg,da9215-legacy
```

Only `dlg,da9214-legacy` is enabled in the first board patch. The `-legacy`
suffix is an integration name that prevents the current `dlg,da9214`
compatible from falling through to the incompatible DA9211/A-family probe.
It has no `dlg,da9214` fallback. Upstream review may choose a different stable
name or reassign the existing ambiguous compatible, but that decision must
preserve the separated probe and zero-write contract. The local compatible is
deleted when an accepted upstream binding supplies the same safe distinction.

## Hardware model

| Variant | Output topology | Initial implementation state |
| --- | --- | --- |
| DA9213 | One logical Buck A assembled from four phases | Represented in match data; no board enables it until an exact read-only match contract exists. |
| DA9214 | Buck A and Buck B, two phases each | Enabled only for the Gemini isolated profile and exact tuple below. |
| DA9215 | Three-phase Buck A and one-phase Buck B | Represented in match data; no board enables it until an exact read-only match contract exists. |

The common non-A model has application registers on pages 0 and 1. In I2C
mode, pages 2 and 3 are directly accessible at an adjacent slave address.
The first driver does not select a page and does not construct a paged regmap.

## Binding contract

The new binding is separate from `dlg,da9211.yaml`. Its initial schema:

- accepts the three programming-model compatibles above;
- requires two `reg` entries named `primary` and `page2`;
- requires the addresses to be fixed at `0x68` and `0x69` for the isolated
  Gemini DA9214 profile;
- permits one hardware `interrupts` description because the pin exists, but
  the Gemini node omits it until IRQ ownership and semantics are validated;
- describes optional `regulators` children for the physical outputs, but the
  isolated profile contains no such child and the identification-only driver
  does not parse or register one; and
- rejects custom voltage, enable, page-selection, retry, reset, or consumer
  properties.

The initial board node is therefore exactly:

```dts
regulator@68 {
        compatible = "dlg,da9214-legacy";
        reg = <0x68>, <0x69>;
        reg-names = "primary", "page2";
};
```

There is no generic compatible fallback, `regulators` child, supply phandle,
enable GPIO, `regulator-boot-on`, `regulator-always-on`, voltage/current
constraint, interrupt, or A72 consumer.

The driver binds to the primary client and claims the named secondary address
with `devm_i2c_new_dummy_device()` or the current managed equivalent. Claiming
the secondary address performs no bus transaction. Any occupied, missing, or
different secondary address fails probe before a transfer.

## Ownership

| Resource | Owner after a successful first-stage bind |
| --- | --- |
| I2C6 controller and DVFSP handoff | Existing MT6797 controller and handoff drivers |
| I2C addresses `0x68` and `0x69` | Legacy-family identification driver |
| Register pages and selector | Existing firmware state; Linux makes no claim |
| Buck A, Buck B, voltage, enable, and current limits | Existing firmware/hardware owners; no Linux provider |
| IRQ line | Unclaimed |
| CPU8 and CPU9 rail consumers | Disconnected |
| Suspend and resume state | Existing firmware state; the driver has no PM callback |

No public read, write, debugfs, sysfs-control, module-parameter, ioctl, or
regmap interface is added. The only visible result is ordinary driver bind
state and bounded informational/error logging.

## Exact probe state machine

Probe requires:

1. exact `dlg,da9214-legacy` match data;
2. a 7-bit primary address of `0x68`;
3. named secondary address `page2` equal to `0x69`;
4. `I2C_FUNC_I2C`, because every observation is one combined two-message
   transfer;
5. successful exclusive claim of `0x69`; and
6. no regulator children in the active board node.

Probe takes the root adapter lock once around the complete observation
sequence. Each observation consists of exactly two messages under one
`__i2c_transfer()`:

1. a one-byte pointer write containing only the fixed register address; and
2. a one-byte read into a freshly initialized destination.

The pointer byte is required by the I2C read protocol and is not a
register-data write. A transfer succeeds only when `__i2c_transfer()` returns
exactly two. The locked internal transfer primitive deliberately bypasses the
adapter retry loop. There is no SMBus fallback, split transfer, driver-level
retry or reset request, page selection, or alternate engine. Adapter-internal
error recovery remains controller-owned; any transfer error blocks bind and
is not regulator evidence.

The complete successful sequence is:

| Ordinal | Pass | Address | Pointer | Expected byte |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 0 | `0x69` | `0x05` | `0xd9` |
| 2 | 0 | `0x69` | `0x06` | `0xd0` |
| 3 | 0 | `0x69` | `0x47` | `0xc0` |
| 4 | 0 | `0x68` | `0xd3` | `0x1f` |
| 5 | 0 | `0x68` | `0x5e` | `0x00` |
| 6 | 0 | `0x68` | `0xd9` | `0x46` |
| 7 | 0 | `0x68` | `0xda` | `0x46` |
| 8 | 1 | `0x69` | `0x05` | `0xd9` |
| 9 | 1 | `0x69` | `0x06` | `0xd0` |
| 10 | 1 | `0x69` | `0x47` | `0xc0` |
| 11 | 1 | `0x68` | `0xd3` | `0x1f` |
| 12 | 1 | `0x68` | `0x5e` | `0x00` |
| 13 | 1 | `0x68` | `0xd9` | `0x46` |
| 14 | 1 | `0x68` | `0xda` | `0x46` |

The implementation compares each returned byte immediately and stops on the
first mismatch. Therefore every possible hardware transaction trace is a
prefix of this table; only an exact 14-transfer trace can bind. The second
pass must also equal the first byte for byte.

`probe-contract.json` is the machine-readable authority for this table.
`scripts/validate-contract.py` rejects changes to the address, order, pointer
length, read length, expected byte, pass count, retry count, or write
boundary.

## Failure behavior

| Failure | Required result |
| --- | --- |
| Wrong compatible or variant not enabled | No probe by this driver |
| Missing raw I2C functionality | `-EOPNOTSUPP`, zero transfers |
| Primary or secondary address mismatch | `-ENODEV`, zero transfers |
| Secondary address already claimed | Preserve the underlying error, zero transfers |
| Negative or partial `i2c_transfer()` result | Return an I/O error immediately; no retry or reset |
| Returned byte mismatch | `-ENODEV` immediately; no remaining reads |
| Regulator child or consumer present in the isolated node | `-EINVAL`, zero transfers |
| Allocation failure | Preserve the allocation error; devres releases prior software-only state |

No failure falls back to the DA9211/A-family device-ID probe. No failure
changes `PAGE_CON`, voltage, enable, current limit, interrupt mask, controller
policy, CPU state, or storage.

## Bind, unbind, suspend, and resume

After an exact match, probe stores only immutable match metadata and the two
client handles. It registers no `regulator_dev`, IRQ, PM hook, or userspace
control surface.

Unbind releases the secondary dummy client and software allocations through
managed cleanup. It performs zero I2C transactions and has no hardware state
to restore.

Suspend and resume have no callbacks and perform zero I2C transactions. The
driver makes no claim that the tuple or rail state survives suspend. Resume
ownership remains a later, separate experiment.

Failed probe cleanup, unbind, shutdown, suspend, and resume must all be
transaction-free. Driver shutdown must not be implemented for this stage.

## Forbidden implementation shortcuts

The first implementation must not:

- modify `da9211-regulator.c` to emulate this protocol;
- read device ID `0x201` or any production/test page;
- access `PAGE_CON` at `0x00`, `0x80`, or `0x100`;
- use regmap ranges, a page selector, cache, or implicit read-modify-write;
- send a two-byte register/data write;
- use vendor-shaped retry, reset, fatal, or arbitrary-transfer policy;
- register Buck A or Buck B with the regulator core;
- parse or accept a consumer supply;
- expose voltage, enable, mode, current, or status operations;
- request an IRQ;
- add a writable debug or userspace surface;
- request CPU8 or CPU9; or
- access a block device or boot partition.

## Patch layering and deletion conditions

Gate 2 must produce separate logical patches in this order:

1. binding for the separated non-A programming model;
2. identification-only legacy-family driver;
3. MT6797/Gemini board node with no provider or consumer;
4. isolated configuration/profile and zero-write validators.

Each patch must name the intended upstream regulator, Devicetree, or arm64
tree. The local binding name and patches are removed after an accepted
upstream interface is present in the pinned kernel. None of the rejected
historical patches 0096 or 0104–0110 is a foundation; they are evidence of
unsafe or incompatible approaches only.

## Gate 1 review checklist

- The non-A DA9213/DA9214/DA9215 register model and variant topology are
  explicit.
- The Gemini instance uses fixed direct addresses `0x68` and `0x69`.
- The exact observed tuple is the only successful match.
- Probe, failed-probe cleanup, unbind, suspend, and resume contain no
  register-data write.
- The successful probe trace is the fixed 14-entry table; every failure trace
  is a prefix.
- There is no provider, writable operation, A72 consumer, or IRQ owner.
- Ownership, constraints, error handling, unbind, and resume behavior are
  defined.
- The implementation is separate from the DA9211/A-family probe.
- Vendor policy code is neither required nor copied.
