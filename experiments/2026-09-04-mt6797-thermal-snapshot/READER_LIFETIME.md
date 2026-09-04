# Thermal reader lifetime audit

The audit uses the prepared Linux 7.1.3 source of observer build `fc37244f`.
Core source digests are recorded below; no hardware removal was requested.

`drivers/base/dd.c` calls `device_remove()` before `device_unbind_cleanup()`,
which calls `devres_release_all()`. The earlier driver closed the V4 thermal
transaction inside `.remove`, leaving devres-managed readers registered until
after that close. Its terminal probe-trace failure similarly closed after zone
registration without first unregistering readers. Device-managed allocation
alone therefore did not establish safe hardware lifetime.

Patch `0539` opens a group after V4 transaction acquisition and before the
first thermal-zone registration. The group contains the zone, optional hwmon
registration and optional observer attributes, and closes only after the last
registration. Allocation failure publishes no reader and goes to transaction
cleanup. Remove and late probe failure release the group before transaction
close. Earlier allocations and mappings remain outside the group. The change
also applies when the default-off observer is disabled, because the existing
zone/hwmon readers need the same ordering. Non-V4 removal is unchanged.

The relevant kernel guarantees are:

- `drivers/base/devres.c:release_nodes()` invokes releases in reverse order.
  `devres_release_group()` removes the selected group's nodes and invokes those
  releases synchronously, after dropping the devres spinlock.
- `drivers/base/core.c:devm_attr_group_remove()` calls `sysfs_remove_group()`.
  Kernfs removal deactivates nodes and `fs/kernfs/dir.c:kernfs_drain()` waits
  for active references. The observer callbacks hold no device-unbind lock;
  they take only their owner lock and the existing per-bank lock. The removal
  path takes neither lock while draining.
- `drivers/thermal/thermal_hwmon.c:thermal_remove_hwmon_sysfs()` removes input
  files before freeing their per-zone data. Its devres release precedes the
  thermal zone's release because hwmon registration followed zone registration.
- `drivers/thermal/thermal_core.c:thermal_zone_device_unregister()` exits the
  zone, cancels the polling work synchronously, deletes the zone device and
  waits for its removal completion before freeing it.

Together these source contracts support draining observer, hwmon and thermal
polling before transaction close. The userspace lifetime oracle executes the
actual late-probe and remove bodies with injected resource callbacks; its
reverse-order release adapter relies on the separately audited devres contract.
It does not execute real kernfs or thermal workqueues, and does not demonstrate
hardware removal or suspend/resume behavior.

The actual interface oracle separately uses real pthread mutexes around the
unchanged owner and scan code, with IO and sysfs formatting adapters. It checks
three admitted reads against competing observers and normal polling, bounded
failure text and exhausted-read purity. This validates algorithmic isolation;
it is not a kernel lockdep or real-device contention claim.

## Audited core source identities

```text
8810cf8a16706ef8f86fcc4944e1bfd8158012af415a6ec2e47a9bf02d9a3b09  drivers/base/core.c
950d0a64be85b106837298a1c38ee4124e99071ca1f80b5f3a5184b14a4f152f  drivers/base/dd.c
71e9a931b8746a85a0c67c9f2370aace6aa2c1c67e1110cf49e157fb79522d4d  drivers/base/devres.c
945aab1bee1ca860075ac855c7e009cbe6ee2fef863ea2ed3203868ea81116d2  drivers/thermal/thermal_core.c
0107bb9da111bb3fc7a864c5083800232836abe6ea10f69b4253c82ac26a3a92  drivers/thermal/thermal_hwmon.c
9c36000b318bc93138f023d7b9b66a44c8261d08c12b3b57527953aa3b0df5a8  fs/kernfs/dir.c
```
