# CPU-status mask and bounded transport design

## Kernel invariant

`CPU_PWR_STATUS` and `CPU_PWR_STATUS_2ND` remain full raw `u32` fields. The
stability predicate uses only `GENMASK(7, 6)` independently in each word:

```text
((first ^ second) & GENMASK(7, 6)) != 0
```

Bits outside that mask remain observable but cannot cause the two-sample A72
transaction to fail. The source still performs two and only two samples. CCI
change-pending retains `-EBUSY` precedence, a masked A72 change returns
`-EAGAIN`, read errors leave both public outputs zero, and success publishes the
complete second raw sample.

## Transport invariant

The host first derives the exact concrete device probe from the source-pinned
two-wrapper chain without executing the probe locally. It requires the exact
wrapper hash, derivation depth, final probe hash, framing markers, and candidate
identity. It then base64-encodes those concrete bytes, divides them into chunks
of at most 768 characters, and emits bounded shell assignments to one in-memory
variable. The final command prints a separating newline, decodes the variable
directly into BusyBox `sh`, and unsets it. No remote temporary file,
block-device access, partition read, retained write, or reboot command is used.

The collector preserves the source-pinned predecessor observation loop but
interposes an exact-input netcat shim. Only the inherited legacy wrapper line
is accepted; its decoded hash must match the source wrapper, the replacement
bytes must match the concrete probe, and only those concrete bytes are
converted to the bounded stream before reaching the wire. The real host netcat
receives all original connection arguments unchanged. This prevents the
source-pinning wrapper from being transmitted as though it were the device
probe.

Installer success requires two distinct shutdown observations: the inherited
SSH command must fail after the clean poweroff request, and the device's actual
TCP/22 listener must subsequently close. An SSH session failure while the port
still accepts connections is a half-responsive state, not proof of shutdown.

## Exclusions

No DT change, third platform sample, retry, delay, general-domain comparison,
provider call, retained checkpoint, protected-clock call, BigiDVFS read,
secure call, publisher, lifecycle owner, CPU hotplug call, or CPU8/CPU9 request
is part of this repair.
