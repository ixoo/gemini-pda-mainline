# Bounded STK identity observation

Completed, 2026-09-08. The two-read budget is consumed; do not repeat it.

Original admission: identify the product and revision of the already bound
Gemian STK client without resetting, enabling or configuring a sensor. The
root task is the sole device custodian. Standing bounded read-only Gemian
inspection covers the hardware effect; the sysfs write below supplies a read
address to an audited callback, not a register value.

## Distinguishing observation

Read one byte at each of `0x3e` (product) and `0x3f` (vendor VID) from the bound
I2C1 `0x48` client. A recognized product narrows the explicit upstream
compatible; an unknown product preserves the driver-selection gap. Either
result leaves rails, interrupt wiring, electrical mode and wake behavior
unproved. It cannot admit a mainline sensor probe or change support claims.

The [one-boot observer](scripts/observe-stk-identity.py) defaults to preflight.
Only `--read-identity` issues the two read requests. It pins the current
Gemian boot ID, release, version and decompressed configuration digests,
client name, bound driver, and a retry count of three. Preflight also verifies
that a fresh non-clearing `/dev/kmsg` cursor can be opened. Each request uses
only the existing `als_ps/recv` store callback and selects exactly one byte.
The maximum budget is two requests and six underlying read attempts; there
is no observer retry, scan, unbind, module load, state/threshold/calibration
write, reset, sample acquisition or reboot.

Each result requires exactly one new, address-matching kernel log record
reporting transfer return `1`. The observer rejects a missing, competing,
malformed or failed record, log overrun, changed boot/driver/configuration,
or short request. It rechecks the cached retry setting and identity after
each read. A first-read failure stops before the second request. This assumes
the single custodian has exclusive use of these diagnostic attributes; the
callback does not lock configuration and read-request calls into one
transaction. The callback updates its diagnostic cache as a software side
effect; the observer never
uses that cache as hardware evidence. A successful sysfs write alone is
insufficient.

## Source and retained-kernel basis

The [source/binary receipt](results/stk-identity-sources.json) pins the
inspected inputs and function spans. The selected public Planet source is commit
`c5b0be85017ad0c599725e8273842efdbecdd88a`. Its ALS/PS Makefile selects
`alsps/stk3x1x-new/`, not the similarly named copy under `alsps/mediatek/`.
Source facts are corroborated by private RE-VM disassembly of the retained
primary boot kernel:

- `stk3x1x_hwmsen_read_block()` constructs a one-byte address message followed
  by a read message to the same client, under its existing mutex. Success
  requires `i2c_transfer()` to return two completed messages.
- `stk3x1x_master_recv()` retries using the cached limit and reports the
  requested length after success. A nonpositive retry limit can return that
  length without a transfer, so the observer requires the observed limit of
  three before and after each request; it never changes that setting.
- `stk3x1x_store_recv()` reads one byte, then logs the address, actual helper
  return and byte. Its compiled log arguments load the byte after the call.
  The function returns the sysfs input count and updates its cache even on
  transport failure. `stk3x1x_show_recv()` only prints that cache.
- `stk3x1x_show_config()` reads cached fields only. The observer uses its
  retry count and does not publish the other fields.

The complete reconstructed ELF kernel section equals the retained `Image`.
The observed live version/configuration digests and the 16 MiB logical
primary-boot checksum match this image's provenance. Live Kallsyms exposes
the expected callback names but masks their addresses, so it supplies no
runtime instruction-byte comparison. These checks attribute the selected
implementation; they are not a claim of measured I2C electrical waveforms.

The broader diagnostics remain excluded: reading `reg` performs sensor
configuration/threshold writes; `allreg` reads control, status and measurement
blocks as well as identity; and `read_id()` also invokes an OTP helper that
writes state and access registers. None is an identity-only substitute.

Private captures retain the exact observer digest, timestamps, SSH result
and stream hashes. Publish only the reviewed identity result and provenance;
no calibration, firmware, raw disassembly or unrelated log content belongs
in Git. The observation is tied to this one boot and is not an unattended
recurring test.

## Observed result and implementation decision

The [exact observation receipt](results/stk-identity-20260908.json) records two
successful requests on the admitted boot: `0x3e = 0x11`, `0x3f = 0xc2`, each
with helper return `1` and a fresh kernel-log sequence. The actual observer
matches its recorded SHA-256. Its default preflight had issued zero requests.
No final helper failure or identity change was reported, and no repeat is
selected.

The first byte is outside the pinned upstream driver's explicit ID list:
`0x31`, `0x13`, `0x1d`, `0x15`, `0x1e`, `0x12`, `0x51`. The vendor's broad
high-nibble acceptance includes `0x11`, which explains why binding alone did
not resolve the variant. The vendor calls the second register VID; do not
promote `0xc2` to an independently documented silicon-revision meaning.

The selected source also rewrites the STK client's address from its hardware
configuration. A post-observation read of the same boot's `cust_alsps@0`
properties gives bus 1 and address array `<0x48 0 0 0>`; the source copies that
array and assigns its first byte during probe. This corroborates the logical
`1-0048` client, but is not a physical bus trace or a read of its live address
field. No further sensor transaction was needed for that check.

A bounded public search did not resolve the marketed part for `0x11/0xc2`.
The publicly hosted manufacturer-authored
[STK3310 revision-1.3 datasheet](https://www.scribd.com/document/847510830/STK3310-Sensortek)
lists `0x13` in its product-ID table; that document does not identify this
observed value. Its `0x3f` field is reserved, further limiting a revision claim.
The existing STK3310-family driver remains a protocol-reuse candidate, but no
specific compatible or ID-table addition follows from these two bytes alone.
Resolve the `0x11` variant's part identity and register semantics next, then
its board rail/interrupt contract. An unknown-ID warning followed by a
successful mainline probe would still not resolve those questions.

Validation: Python 3.5-compatible syntax, reviewed source and retained-binary
call paths, successful live preflight and the one admitted observation.
Repository publication checks also apply. No error injection, kernel build,
mainline probe or sensor-function test was performed. Earlier log searches
found no usable probe-ID record and are not used as identity evidence.
