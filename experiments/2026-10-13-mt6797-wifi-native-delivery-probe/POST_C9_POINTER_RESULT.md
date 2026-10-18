# Post-C9: observed monitor callback and a three-bit control primitive

Incomplete, 2026-10-18 UTC. The [source review](POST_C9_SOURCE_REVIEW.md)
advanced to two bounded read-only Gemian observations. They resolved the three
opaque pointer values and captured one complete callback body. The second
callback constructs a three-bit mask from its arguments and stores it to one
control register. No configuration write or new mainline boot ran. This does
not yet identify the controlled RX groups, prove the length-mismatch mechanism
or implement ordinary secure Wi-Fi.

## Source and live admission

Pinned public gen3 source remains `59e00a9144d782e148332009a835b99c43382467`.
Three additional files were retained and checked:

| File | SHA-256 | Relevant result |
| --- | --- | --- |
| `os/linux/gl_proc.c` | `0b1ae241f181e199290d999c71caa9a48dc0fb891fc40236c56585742b8f57e5` | Lines 384-416 ignore query return status before printing the result. Reject this path: printed data cannot prove success. |
| `nic/nic_cmd_event.c` | `cc61d706a4013126c1b3a60021c370590fd5b8c3df2114a1a3a99148fe27dd8f` | Lines 55-82 copy response address/value and complete the query. |
| `os/linux/include/gl_wext_priv.h` | `f587d7aee62d6e2613ccb689e4210e846cf9384232b3f3de59c60773b22cb1b3` | Existing `get_oid` ABI: query ioctl, subcommand, OID and fixed transport structure. No new maintained API. |

The existing structured-query path preserves status and output length; the
client also required response address, OID, input length, sentinel and padding
checks. The advertised 256-byte buffer was fully allocated, with an eight-byte
firmware payload. No setter ioctl, proc selector write, debug unlock, test mode,
radio configuration or key operation was used. A static SIOCGIWPRIV query
confirmed both the stock `get_oid` subcommand and its backing ioctl before any
firmware query. A disabled/refused route would have stopped the observation.

Fresh strict SSH verified Gemian `3.18.41+` / aarch64, boot
`770cff12-273b-4465-899f-f9ad54d0078a`, the expected firmware file and live driver
binding. The firmware read handler's remaining operand shapes passed with the
prior decoder cases: 60 synthetic vectors. Pinned decoder semantics and the
independent GNU/GCC definitions agree on the address guard's unsigned comparison
and implicit branch registers. Synthetic checks establish decoding/host behavior,
not firmware enforcement or a hardware safety guarantee.

## Two finite observations

| Observation | Budget and verified result | Limit |
| --- | --- | --- |
| Pointer words | Four queries: one existing dispatch-data anchor, then the three pointer words already loaded by the monitor handler. Four responses passed all gates. | The anchor plus file identity is a narrow running-image check, not full live-image attestation. |
| One callback window | Fresh identity/anchor and selected-pointer checks, then sixteen aligned words at that observed target. Eighteen queries and eighteen checked responses. | Exactly one fixed 64-byte code window; no register sweep, range discovery or automatic following of returned targets. |

The first helper had a 30-second whole-run alarm; the second had 60 seconds.
Both completed normally. Each request was recorded before issuance; no retry,
alternate route, reset or recovery was needed. All three pointers lie outside
the retained firmware CODE/DATA sections, explaining why the earlier retained
image scan could not resolve their bodies. This does not identify an entire
external memory region or justify dumping it.

The second target was selected because the existing monitor handler passes
three Boolean arguments, all one on enable and all zero on disable. Binary
interpretation occurred only in the RE VM. The fixed window contains fifteen
instructions through a return, followed by nine undecoded trailing halfwords.
It has no nested call. Three initially unvalidated byte-extension records and
the XOR shape passed an independent GNU-derived decoder addendum: all 64 vectors
pass. Frozen decoder source and earlier results remain unchanged.

## Established primitive and remaining ambiguity

For Boolean inputs, the complete visible body produces one mask bit from each
argument and performs one full-word store. The observed monitor call therefore
selects mask 7 on enable and mask 0 on disable. The precise destination and
instruction records remain in private evidence; no firmware code is published.
This identifies a concrete control primitive, rather than a guessed register
or a search for the number 48.

The pinned public [RXD layout](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/wlan/gen3/include/nic/nic_rx.h#L455-L484)
defines Group1/2/3 spans of 16/8/24 bytes. Their
sum is 48, but neither that arithmetic nor this mask establishes that these
bits control those groups, that pending frames are rewritten, or that FIFO
lengths are published before a format change. No packet-pointer, length-store
or FIFO-publication linkage was captured. C9's 427/379 refusal remains fatal.
Do not subtract 48, copy a prefix or infer a valid packet from it.

The next source decision is whether this exact primitive has a supported group
reporting contract independent of the monitor filter/channel changes. Review
its address/bit ownership and the standard firmware write-command path before
proposing a narrowly controlled comparison. Any such comparison needs its own
resource-write protocol, actual-source tests, clean pushed Buildbox input,
validated package and boot admission. No write or C10 candidate is admitted by
this observation. A diagnostic result would still need per-frame integrity/PN
checks; missing metadata must continue to reject traffic.

Ordinary PTK/GTK attribution, rekey/deletion and safe reuse, healthy repeated
lifetimes, three replies and sustained ten-minute SSH remain separate acceptance
gates. Resolving a control primitive is progress toward those gates, not support.

## Preservation and current device

All 26 exported VM evidence entries independently match their manifest. The
private laptop manifest covers 50 admission/source/helper/capture/result files,
SHA-256 `49937dfe80e31c27a099cb891ee8e6138ac568d99a871039affb9689d0964255`.
Raw words, code, instruction listings and private operational identities are
excluded from publication. The [scalars](results/post-ccmp9-pointer-scalars.json)
contain only sanitized counts and verdicts.

Both helpers terminated; RE process quiescence was independently checked.
Separate strict LAN SSH verified the same Gemian kernel and unchanged boot
following the observations. No new boot2 installation or physical selection is
pending. C9 remains consumed, and the unrelated restored research is separate.
