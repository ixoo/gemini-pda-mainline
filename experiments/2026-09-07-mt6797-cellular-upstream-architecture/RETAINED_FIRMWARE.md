# Retained MD1 firmware identity and header join

## Result

The retained July `md1img` capture has a v5 check header whose reported fields
match the [September Gemian observation](GEMIAN_HANDOFF.md): version, header
size, platform, build/version time, declared image size, memory requirement,
all five active region pairs, and DSP/ARM7 offsets and reservation sizes.
The [receipt](results/retained-firmware-header-20260908.json) now identifies the
three retained component containers and their declared payloads by SHA-256.
This establishes concrete retained inputs for further private analysis; it does
not establish the running-image digest, authentication or a loadable mainline
firmware bundle.

## Observed input boundaries

The existing captures were read only in the RE VM through the read-only project
mount. All three complete-file digests match their original capture manifest.
No device connection, new partition capture, firmware execution, extraction to
an executable file or calibration read was performed. Full digests and sizes
are in the receipt; no binary or raw header is published.

| Container name | Partition capture bytes | Declared payload bytes | Main-header memory allowance |
| --- | ---: | ---: | --- |
| `md1rom` | 25,165,824 | 18,223,992 | 128 MiB for the image-memory layout |
| `md1dsp` | 4,194,304 | 1,016,744 | 2 MiB at offset `0x01400000` |
| `md1arm7` | 3,145,728 | **1** | 3 MiB at offset `0x04530000` |

Each first container has MediaTek magic `0x58881688`, extension magic
`0x58891689`, a 512-byte header and zero high size/address words. The payload
digests cover exactly the declared size beginning at file offset 512. They
exclude the container header and unused partition extent. These digests must
not be relabeled as authenticated executable-image digests.

The one-byte ARM7 payload is not evidence of a full ARM7 executable. In the
pinned source, `load_image_by_name()` reads the declared payload, zeroes only
the remainder to the declared alignment, and returns the unrounded byte count.
There is no one-byte placeholder branch in that helper. If the normal path
selects this input and passes its security policy, this means one byte plus
15 zero padding bytes, not a synthesized 3 MiB image. The caller rejects
negative results and payloads larger than the header allowance; it does not
require equal sizes. Actual runtime treatment and the byte's purpose remain
unresolved, and the security hooks were not executed or bypassed.

The later [retained-LK selection audit](ARM7_SELECTION.md) corroborates the
compiled normal-v5 table selection, required ARM7 descriptor and header-based
destination/size assignment. Its subimage loop has no one-byte exception.
This narrows the static selection question without proving a runtime load,
the byte's purpose or permission to omit the component.

The loader searches the main-image partition before the component partition.
A bounded search found no additional matching MD1 component container headers
in these three captures, but it was not a complete loader/security-parser
emulation. Do not treat the memory reservation as payload size.

## Main check header

The pinned public LK structure and trailing-size locator identify a 344-byte
header at file offset `0x01161420`. Its SHA-256 is
`5176f3eccb13a360d76b99d7dd2274176e5ec0fae7ef8256b35e64b908fa58f3`.
It reports version 5, product version 2, image type 12, MD binding 1,
`MT6797_S00`, build `MOLY.LR11.W1630.MD.MP.V105.8`, and build time
`2018/12/08 11:40`. Its `0x08000000` memory requirement and `0x0116113c`
declared image size match the saved Gemian report. Matching these fields does
not prove equality of all loaded bytes or even of the complete live header.

There is a **228-byte interval** between the extent implied by the declared
image size and the start of the check header. It is not all zero, and its
purpose is not established. Preserve the complete container; do not strip or
reinterpret this interval to manufacture a supposed executable image. The receipt records its
location, size and digest without redistributing its contents.

The header has one nonempty padding record, offset `0x01170000` and length
`0x00290000`, entirely inside the 128 MiB image-memory layout. This is distinct
from the [32 MiB allocation tail](LOADER_TAIL.md) outside that layout. Header
padding metadata does not prove that LK emitted a corresponding retrieve tag
or that any consumer released the memory. Preserve both ranges until their
actual lifetimes and protection ownership are established.

Both header shared-memory size fields are zero, while the observed handoff
supplies nonzero shared regions. A future host must not infer that no shared
memory is required from those zero fields. All four header domain-attribute
words are `0xffffffff`; this records header data, not accepted hardware MPU
permissions or release authority.

## Validation and next boundary

The independently written private decoder checked capture hashes, both
container magics, header version/size/bounds, the trailing check-header locator,
contiguous five-region coverage of 128 MiB, zero unused region records, and
subimage bounds. A separate comparison checked the decoded fields and all five
region pairs against the published saved-log selections. The receipt pins the
source header and parser digest and defines the exact hash ranges; the parser
and original inputs remain in the RE VM/private capture store.

Repository, local-link, JSON, whitespace and bounded sensitive-data checks
passed before publication. No kernel build or hardware support test occurred.
The loaded-image identity remains open: the next evidence must join actual
loader selection and any transformations to the executing bytes. Repeating
build-string comparisons cannot supply that proof. Secure MPU acceptance and
shared MD3 release lifetime remain separate prerequisites.
