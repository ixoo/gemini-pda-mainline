# One Gemian charger identity read

Status (2026-09-12): completed once; the register-request budget is consumed.
The observed identity matches BQ25896. Mainline charging remains untested.
This extends the [charger investigation](README.md) without a mainline boot.
The primary integration coordinator is the sole device custodian. The selected
Wi-Fi HPS candidate remains waiting for installation power; its boot budget and
inputs are unchanged.

## Question and decision

Does the populated I2C0 `0x6b` charger report part-number zero and revision two
in register `0x14`, as a BQ25896 would? A matching observation would narrow the
upstream driver's variant choice. Zero, another value, a failed identity gate,
an exception, or conflicting evidence ends this attempt without a retry or
charge-control change. A different value needs its own reference comparison.
The vendor interface hides I2C status and uses a shared cached result, so its
output cannot independently certify bus success or mainline probe safety.

## Reviewed access path

The pinned [Gemian source](https://github.com/gemian/gemini-linux-kernel-3.18/blob/8cfe6596a503612e3332d9c26e292a19525a7f07/drivers/misc/mediatek/power/mt6797/bq25890.c)
and the retained primary kernel agree on these branches:

- `store_bq25890_access()` treats an input length of at most three bytes as a
  hexadecimal register-address read. More than three bytes selects a hardware
  read/modify/write path. Only the immutable two bytes `b"14"` are admitted.
- The selected `bq25890_read_byte()` implementation requests two I2C messages:
  one address byte followed by one received byte, under the existing driver's
  mutex. Its local loop has one iteration. This is one helper request; normal
  I2C-core/controller retry behavior is not an independently measured wire count.
- `bq25890_read_interface()` initializes its temporary byte to zero and copies
  it into the diagnostic cache even when the transfer fails. The store handler
  discards the status and returns the input length. The show handler formats
  the cache as decimal without a further hardware read. No other source path
  writes this cache, but the interface does not lock out another sysfs writer.

TI's [BQ25896 datasheet, revision C](https://www.ti.com/lit/ds/symlink/bq25896.pdf)
describes the address-pointer/repeated-start single read in section 9.2.16.6,
figure 21 (page 30). Table 26 (page 48) makes PN bits 5:3 and DEV_REV bits 1:0
read-only, with values `000` and `10`. Register reset is bit 7 and needs a
data write of one; this procedure supplies no register data byte. Register
`0x0c`, whose fault semantics differ, and every other register are excluded.
The two cited PDF pages were rendered and visually checked.

The RE VM verified the retained `Image` against the reconstructed ELF's entire
`.kernel` section and inspected the user-space probe, store, show, read wrapper
and two-message transfer. The probe registers the expected device attribute.
The next-symbol ranges include alignment padding; they are not debug-symbol
function-size claims. Exact source, document, binary and range identities will
accompany the result. No vendor source, disassembly or firmware is published.

## Identity, finite effects and collection

The read-only metadata preflight established Gemian `Linux 3.18.41+ aarch64`,
boot `a1efb6e0-4c7e-43f6-9b56-0ba6086bd8c2`, and a live-GPT-selected primary
`boot` SHA-256 of
`1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513`.
That checksum matches the retained kernel container. This joins the known
Gemian boot and stored image; it is not runtime cryptographic attestation.
The four helper names exist in kallsyms but their addresses are masked even
under sudo, so there is no live-address comparison claim.

The first metadata collection stopped on a missing `of_node` sysfs link,
before any diagnostic access. A second metadata-only collection found the
same firmware name, full path and compatible in the I2C client's `uevent`:
`/soc/i2c@11007000/sw_charger@6b`, `mediatek,sw_charger`. It verified the client
driver `bq25890` and platform interface driver `bq25890-user`. Both metadata
attempts and the bounded primary-partition checksum read are retained privately.

Before the request, recheck boot/release, client name/driver/uevent, interface
driver/path/mode and the previously observed `/proc/version` digest. Require
the present/Good battery and unchanged boot. This is an identity read in the
running Gemian owner, not a deployment; the boot2 power threshold is unchanged.

One remote Python invocation is bounded by a 20-second process timeout and
35-second host timeout. Open the existing interface without changing its mode,
issue exactly one `os.write(fd, b"14")`, then obtain at most eight bytes from
the cached show handler. Require exactly two bytes accepted and a decimal byte
value. No input construction, newline, partial-write retry, second request,
scan, dump, raw I2C access, driver rebind, or control-register write is allowed.
Failures after the write consume the request. A timeout does not admit a retry.

A nonblocking `/dev/kmsg` reader starts at the current end before the request.
Afterward it may collect at most 32 records of at most 4,096 bytes each, without
clearing logs or changing logging. These records can corroborate the handler's
selected register, input length and value; missing logs leave that corroboration
unavailable. They do not expose the discarded transfer status. Recheck boot
and ordinary battery/external-power metadata afterward. Retain partial output
on any failure. No shutdown or recovery is required for this procedure.

All raw output and the exact one-use collector stay under ignored,
access-restricted `artifacts/charger-identity-review/20260912`. Publish only
sanitized identities, the requested address/value, consumed budgets and limits.

## Upstream boundary

The [current upstream driver](https://github.com/torvalds/linux/blob/cba2348ab114391f5b1a00fa65c5b739f13f0563/drivers/power/supply/bq25890_charger.c)
maps PN zero/revision two to BQ25896 and zero/one to BQ25892. Other revisions
with PN zero warn and fall back to BQ25892; the historical statement that all
unknown combinations are rejected is too broad. This fallback must not count
as silicon identification. Full probe invokes hardware initialization before
IRQ resolution and is not the read-only identification method used here.
IRQ ownership, board wiring, battery limits, protection and mainline operation
remain separate requirements regardless of this result.

## Result

The [sanitized receipt](results/charger-id-20260912.json) records one successful
collector invocation at device UTC `2026-09-12T20:54:31.820464Z`. It accepted
exactly two input bytes; the cached show returned decimal `6` (`0x06`). PN is
zero and DEV_REV is two, matching the BQ25896 identity fields in TI's table.
Five new kernel records corroborated input `14`, length two, register `0x14`,
value `0x06` and the same show value. The log reader reached the current end
within its budget. There was no retry or requested control-register write.

Boot identity remained unchanged. Before and after, Gemian reported a present,
Good battery at 31%, `Not charging`, with AC, USB and wireless online values
all zero. The Wi-Fi installation power gate therefore remains unsatisfied.
No new boot, cable change, charging-control test or recovery was performed.

This is a corroborated observation through the reviewed vendor read path,
with the transfer-status and shared-cache limitations above. It supports
BQ25896 variant selection for subsequent board-resource work; it does not
enable a charger node or establish safe mainline charging. The single request
is consumed and this collector must not be rerun. Syntax and inspection of the
single literal write passed; no kernel build was needed for this evidence-only
change. No vendor code or firmware was copied into the public record.
