# Pre-patch chip capture result

The [runtime receipt](results/runtime-1.json) records one attributable boot of
kernel inputs `8956fbc1` and the validated padded candidate. Two equal private
region-19 preimages and complete WMT preparation passed. The owner sent exactly
26 command bytes, retained 22 reply bytes over six services and retired with
`-ETIMEDOUT`, terminal set and clocks held. No second trigger was issued.

The reply has a 16-byte mandatory-STP payload containing a 16-byte WMT event:
its declared inner payload length is 12. It carries opcode 0x08, status zero,
count one, returned address 0x80000008 and value 0x00000279. This resolves the
source template's conflicting length for the observed pre-patch chip read only.
HW/ROM replies and the full applicability tuple remain unmeasured. No identity
was accepted at runtime and no initialization continuation followed.

The shell reported printf status zero with no stderr despite the kernel terminal
result -110. The original host classifier therefore marked bounded_measurement
false. Read-only sysfs restoration and the unchanged boot checks passed; the
kernel record and complete bounded dumps independently account for the capture.
Do not reinterpret shell success as command success or repeat this lifetime to
repair the classification. The store calls the inherited deferred-start wrapper;
its selected source returns the recorded query result. The origin of the shell
status discrepancy is not yet established.

Complete zero-through-seal preservation retained 1902 records / 133980 bytes.
The provider was registered, the established A53 regression passed, and reviewed
native recovery confirmed a changed Gemian boot. Raw logs, region images and
firmware remain private. Publish only the parsed fields and sanitized receipts.

The next owner must strictly check chip framing/status/count/address/value,
measure and check HW/ROM reads before negotiation, and stop on the first unknown
result. This capture does not admit ROM patching, DLM writes, calibration or a
scan. The installed capture lifetime is retired; do not boot its identical
artifact again without a decision-changing measurement.
