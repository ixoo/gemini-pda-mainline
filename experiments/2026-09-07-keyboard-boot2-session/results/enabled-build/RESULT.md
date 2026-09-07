# Enabled keyboard userspace build — passed

Buildbox produced and published one exact enabled ARM64 userspace package from
repository revision `93e2b8526daa683c2ba848011fac757a398a13dd`. The package
identity is
`0baad6b85ae68770b783245e2f1dcd7eeb4ef40d93c19e0b30e1f89f8adc3065`.
The ignored local export path and complete identities are recorded in
[`receipt.json`](receipt.json).

The 66,672-byte static `keyboard-monitor` has SHA-256
`4363a7d61d818bc443d5cfd76455ac38fc2cea35178d44a2dc81c229ff97b67f`
and manifest state `production_entry=enabled-admission-v1`. The separate static
`keyboard-disconnect-probe` has SHA-256
`560d00ab80040b90fead5d0a5b2672ed633f62599aa483ff0a33be0fa74d3681`.
Both came from two byte-identical replicas. The probe uses the same monitor
lifecycle engine with a built-in harmless child and fixed RAM parent; it cannot
open evdev or a VT.

The package checksum inventory, source revision, source inputs, tool inputs,
static AArch64 headers, link map, size bound and twelve ARM64/QEMU fixture tests
passed. A bounded postflight revalidated the remote package, clean exact checkout,
publication pointer and absence of the temporary build stage. The local package
validator independently passed after fetch. The disposable dispatch checkout's
console log was not retained before cleanup; the immutable package, remote
publication and explicit postflight are the retained build evidence.

This result supplies an enabled package, not permission to execute it. The host
capture gate is still default-off. The exact Dropbear disconnect proof, fresh
runtime/custody receipts, independent Astra admission and owner physical boot2
selection remain required. No kernel build, VM build, device access or hardware
claim occurred.
