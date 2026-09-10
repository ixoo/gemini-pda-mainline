# Native firmware mapping failure handling

The [unselected patch](patches/firmware-read-safety/0001-wlan-reject-invalid-native-firmware-mappings.patch)
prevents invalid reads from being published to `wlanAdapterStart()`. It follows
the existing [read-capture patch](FIRMWARE_READ_HOOKS.md), preserving those
historical bytes and their results. The [source receipt](results/firmware-read-safety-sources.json)
pins both complete `gl_kal.c` inputs against Gemian revision
`59e00a9144d782e148332009a835b99c43382467`.

The native parent accepts a negative, short, zero or oversized read as success,
converts its signed return to the published unsigned length, and can call the
file reader with a failed allocation. Its file-size query truncates the signed
inode size before allocation rounding. These are concrete prerequisites for
any later payload hashing or loader observation, not merely decoder failures.

The fix rejects nonpositive inode sizes and sizes above `0xfffffffc` before
conversion; that is the largest length whose native 32-bit four-byte alignment
cannot wrap. It stops before a file read when allocation fails, and the read
helper rejects null arguments and zero requests. A called read must return
exactly the requested count. The observer still records its actual signed
return, including an error, before the mapping reports failure. No read is
retried and no payload hash or extra file read is introduced.

Size/allocation failures close the opened file. A read failure frees the
allocated buffer and closes the file. Failed mappings leave the caller's two
outputs untouched and return null, selecting the existing probe failure path.
Valid mappings retain the original file/allocation/publication order. The
selected gen3 source has no other call sites for the size/read helpers outside
this mapping path; their existing declarations remain available.

The upper size bound is arithmetic safety, not a candidate memory or timing
budget. This does not freeze file contents, prove a complete file read across
concurrent file mutation, validate firmware structure, establish buffer identity,
or fix the separate open/recovery/shared-resource lifetimes. The historical
native failure behavior remains evidence; this successor deliberately changes
that behavior and must be identified separately in any admitted experiment.

## Validation

The [host fixture](test-firmware-read-safety.py) compiles the complete parent
and changed size/read/mapping bodies with the real capture helpers and writer.
It reproduces five invalid publications in the parent. The successor passes
60 mapping cases across capture disabled, enabled and a lost first-record
store; ten signed-size boundary cases; and four invalid read-argument cases.
Nine valid native effect sequences match the parent, including capture
retirement during a read. Failure checks require no output publication, exact
close/free counts and no forbidden allocation/read. Actual signed failures
remain in the capture. Compiler flags include `-Wall -Wextra -Werror`.

File operations, allocation and assertions are injected. The tests do not
perform real null-buffer reads or allocate a multi-gigabyte buffer, and they
do not model concurrent filesystem changes, native faults, recovery or radio
behavior. Reproduce using the receipt-pinned files and DMA helper directory:

```sh
python3 experiments/2026-09-07-mt6797-wifi-observer-feasibility/test-firmware-read-safety.py PARENT_C SAFE_C DMA_PATCHED
```

The existing Buildbox lane accepts `check-startup-objects.py COMMIT
--firmware-read-safe` for the fourteen-patch composition. Native compilation
is pending. No manifest profile or boot candidate selects this patch; no
kernel image, device test or upstream certification is supplied here.

Patch replay and reversal pass. Strict Checkpatch reports zero errors,
warnings and checks with two explicit exclusions: the synthetic archive has
no sign-off, and existing native identifiers retain their mixed-case names.
The source receipt pins the checker; this does not certify upstream readiness.
