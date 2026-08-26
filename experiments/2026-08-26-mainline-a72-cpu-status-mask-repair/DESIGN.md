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

The host base64-encodes the exact source-pinned device probe, divides it into
chunks of at most 768 characters, and emits bounded shell assignments to one
in-memory variable. The final command prints a separating newline, decodes the
variable directly into BusyBox `sh`, and unsets it. No remote temporary file,
block-device access, partition read, retained write, or reboot command is used.
The collector preserves the source-pinned predecessor observation loop but
interposes an exact-input netcat shim: only the inherited legacy probe line is
accepted, it is converted to the bounded stream before reaching the wire, and
the real host netcat receives all original connection arguments unchanged.

Installer success requires two distinct shutdown observations: the inherited
SSH command must fail after the clean poweroff request, and the device's actual
TCP/22 listener must subsequently close. An SSH session failure while the port
still accepts connections is a half-responsive state, not proof of shutdown.

## Exclusions

No DT change, third platform sample, retry, delay, general-domain comparison,
provider call, retained checkpoint, protected-clock call, BigiDVFS read,
secure call, publisher, lifecycle owner, CPU hotplug call, or CPU8/CPU9 request
is part of this repair.
