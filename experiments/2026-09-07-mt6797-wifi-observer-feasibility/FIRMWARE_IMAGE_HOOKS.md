# Native firmware buffer and section capture

This unselected native observer component records the buffer passed from the
successful firmware mapping into the divided image loader. It follows the
[read safety patch](FIRMWARE_READ_SAFETY.md), which prevents failed or partial
reads from publishing an allocation. It is not an admitted boot candidate or
upstream driver change. The synthetic patch author makes no DCO certification.

## Producer and lineage

The [patch](patches/firmware-image/0001-wlan-capture-native-firmware-buffer-and-sections.patch)
and [source receipt](results/firmware-image-capture-sources.json) pin the eight
modified parent files and all ten resulting files at the existing native
revision. Apply after pstore, DMA, stop, firmware-read and firmware-read-safety,
in that order. The canonical kernel series and profiles do not select it.

A stack-owned witness in `gl_init.c` receives the borrowed allocation pointer,
length, adapter identity and read transaction only after successful mapping
publication is recorded. The separate ACPI power-management mapper passes a
null witness and retains its existing loader path. The synchronous `wlanAdapterStart()` call passes that
witness to `wlanImageDividDownload()`. Before additional buffer reads, the
observer requires the actual argument and header pointers to equal the witness,
a live matching DMA binding, and exactly 411632 bytes. It checks the MTKE
signature, four descriptors, bounded nonempty source spans after the 88-byte
header, and nonoverflowing 32-bit destination spans.

One `sha256-generic` shash transform computes the actual buffer digest at loader
entry and again at return. Kind 7 subtype 5 records that digest, size, section
count and read ID. Each native loop iteration records subtype 6 with its actual
source offset, size, destination, encryption byte and key byte. All three native
return paths preserve the native status and release the transform. Subtype 7 is
emitted only when both hashes agree and observation remains live; native success
also requires all four ordered sections. Missing records, hash errors, changed
boundary contents, stale bindings or invalid witnesses close the observation.
They do not change the native loader return or add HIF or EMI operations.

The native mapping remains owned by the synchronous caller until unmapping
after adapter startup. Inspected section submission copies source bytes into a
separate command buffer; the EMI path reads the source. This is source evidence,
not a complete proof that every possible consumer preserves the buffer.
Matching boundary hashes **do not prove interval immutability**. A test changes
and restores a byte between hashes and is deliberately accepted. These records
must not be described as proving the identity of every byte submitted to hardware.

## Added work and remaining admission

Normal image observation adds six 128-byte records (768 bytes), one transform
allocation/free, and at most two 411632-byte hashes (823264 payload bytes read),
plus bounded header reads. Existing read and DMA records remain additional.
Capture disabled adds no transform allocation or payload hashing. The native
configuration enables SHA256, but transform lookup can involve crypto-manager
or module lookup when the algorithm is unavailable. Acquisition, execution time,
stack use and the full capture budget still need candidate-level review and
measurement. There is no measured device latency or watchdog budget here.

The component supplies neither the cycle controller nor typed EMI, isolation or
provider OFF producers. Full kernel linking, capture initialization and recovery
admission remain outstanding. No device has executed this component.

## Validation

`test-firmware-image-capture.py PARENT CHANGED DMA_SOURCES` checks receipt-pinned
source fragments using the actual mapping helpers, divided loader, record writer
and capture helper. Its file, hardware and crypto interfaces are injected; the
crypto callback hashes the actual supplied bytes with host SHA256. This does not
execute the native crypto backend.

Six native paths preserve native effects and return values with capture enabled
and disabled: success, either HIF stage failure, missing EMI base, persistent
mutation and restored mutation. Tests also cover three mapping failures, six
crypto faults, four witness faults, three lost-record sites and nineteen guards.
Five valid-checksum wrong joins retain independently valid read and image records
but fail `check_image_read()`: read ID, adapter, extent, order and envelope ID.
The existing full image/EMI checker retains its separate requirements.

For native compilation, `check-startup-objects.py COMMIT --firmware-image` uses
the clean pushed checkout on Buildbox, applies all fifteen prerequisite patches,
and compiles complete `gl_kal.c`, `gl_init.c`, `wlan_lib.c`, `nic_pwr_mgt.c` and
`hif_fw_capture.c` translation units. It checks modified header dependencies and
emitted capture calls. The [compile receipt](results/firmware-image-object-compile.json)
records a successful run at `2d1c0e4370d9844a6dd622208a11d487ee59c14d` and exact
remote/local verification of all 26 package files. The native flags retain `-w`;
zero diagnostics do not establish warning-clean code. The emitted hash helper
reserves 304 stack bytes, excluding caller and crypto-backend frames. This is
not a complete stack budget. No kernel image or device action was performed.

An earlier four-unit compile at `f87a941846bc0deb2772cb8f40cc47ebe2f7f573`
missed the second mapping caller in `nic_pwr_mgt.c`. The recorded five-unit
success supersedes it. The [Linux repository check](https://github.com/ixoo/gemini-pda-mainline/actions/runs/34473691629)
passed at the five-unit input commit, including the mandatory Linux provenance
fixture and all eight changed publication paths.
