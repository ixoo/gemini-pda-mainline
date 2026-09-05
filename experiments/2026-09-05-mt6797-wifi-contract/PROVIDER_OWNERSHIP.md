# CONN prerequisite ownership after an inconclusive transition

This source-only addendum follows consumer-ordering commit
`1720d8773de92715ef2c9027ca50de905ab2060c`. Its
[consumer analysis](CONSUMER_ORDERING.md) and validation receipt remain unchanged.
No hardware operations, driver skeleton, binding, domain data or selected patch
are introduced. The comparison uses the two revisions in the
[source ledger](results/provider-ownership-sources.json).

## Ownership conclusion

The smallest defensible direction is for the existing SCPSYS domain owner to
own both the outer rail/reset prerequisites and the actual island transition,
within its power callbacks and provider lifetime. A consumer-owned rail sequence
cannot safely infer island OFF from runtime suspend or detach. Moving those
resources into the provider removes that inference: only the callback that
observes completed OFF may release the prerequisites. Consumer probe failure or
removal then releases a client, not the prerequisite owner.

This is an implementation direction, not an established CONN sequence. The SPM
key, operation order, conditional rail requirements and recovery from partial
transitions remain unproved in the [power-domain contract](POWER_DOMAIN.md).
Provider ownership does not resolve them.

## Existing SCPSYS boundary and necessary changes

`scpsys_power_off()` already puts its clock and optional regulator release after
the OFF acknowledgement poll. A bus-protection, SRAM or acknowledgement error
returns before those releases. This demonstrates the useful ownership boundary;
it does not establish that the existing register sequence is valid for CONN.
Its optional single supply does not implement the external reset and ordered
VCN prerequisites established by this investigation.
[SCPSYS callbacks](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/pmdomain/mediatek/mtk-scpsys.c#L303).

The existing ON failure path is unsuitable for blind reuse: after a failed ON
acknowledgement or later preparation failure it disables clocks and the optional
regulator without proving island OFF. A CONN implementation would need to retain
its acquired prerequisites after an inconclusive transition, record that state
in the provider, and refuse unsafe further transitions until a proven recovery
is available. It cannot simply use the generic error labels as rollback.
Likewise, a regulator-release failure after confirmed island OFF needs explicit
accounting; it is not proof of restored ON state.

Genpd sets its software state to ON only after the provider's ON callback
succeeds. An ON callback failure can therefore leave physical uncertainty while
genpd still records OFF; a provider retention decision cannot rely solely on
that software state. Failed OFF leaves genpd without a successful OFF state
update, but runtime suspend can still return success as documented in the
consumer analysis. Prerequisite retention must survive either case in the
provider itself. After a failed OFF, genpd can also short-circuit a later ON
request because its software state still says ON. Resource retention therefore
does not by itself make subsequent consumer use safe; admission after such a
failure needs an explicit reviewed solution, not just a callback error flag.
[Genpd ON bookkeeping](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/pmdomain/core.c#L1038).

The lifetime conditions are concrete:

- Acquire all prerequisite handles and complete fallible preparation before
  exposing a passive, confirmed-OFF CONN domain. The
  [deferred registration proposal](DEFERRED_REGISTRATION.md) supplies only the
  registration-time part; it does not supply the missing CONN resources.
- Do not activate CONN during provider probe and then return a probe error whose
  cleanup releases prerequisites after an inconclusive transition. Any future
  publication path must be reviewed for activation before a later probe error.
- Keep the prerequisite owner bound after publication. Consumer devres must not
  own its rail-enable votes or reset lifetime. Failed OFF retains these resources
  regardless of consumer detach, and must not be converted into cleanup success.
- Provider teardown must not release retained resources while OFF is unconfirmed.
  The existing driver is built in, has no remove callback and suppresses bind
  attributes. That is a bounded starting point for a permanent provider, not a
  universal protection against platform-device removal. Suppressing bind
  attributes alone does not make devres immortal. A removable implementation is
  not justified by this review; its teardown contract would remain unresolved.

[Provider registration](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/pmdomain/mediatek/mtk-scpsys.c#L1146).
This keeps one owner of the existing SPM mapping; it does not justify a second
mapping or an external sequencer independently manipulating the same island.

## Standard power sequencing: useful callbacks, insufficient lifetime guarantee

At the upstream pin, consumer calls are `pwrseq_enable()` and
`pwrseq_disable()`. At the v7.1.3 pin they are named `pwrseq_power_on()` and
`pwrseq_power_off()`; the relevant retention behavior is the same. Provider unit
callbacks return an integer status at both pins.

On the last enable reference, `pwrseq_unit_disable()` calls the unit's disable
callback before disabling dependencies. If that callback fails, it returns the
error without decrementing the enable count or releasing dependencies.
`pwrseq_disable()` clears the descriptor's powered-on flag only on success.
This can preserve prerequisites for a caller that retains the descriptor and a
provider that remains bound. A non-final reference release can return success
without powering the unit off. A callback that merely wraps runtime suspend
still has the original missing OFF witness.
[Unit transitions](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/power/sequencing/core.c#L795),
[consumer disable](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/power/sequencing/core.c#L943).

There are three concrete limits to using this as automatic failure retention:

1. `pwrseq_put()` ignores the disable result, frees the descriptor and drops its
   module/device references. `devm_pwrseq_get()` installs that same cleanup for
   probe failure and removal. The unit may retain enabled dependencies, but the
   consumer descriptor and its references are not retained on failure.
2. `pwrseq_device_unregister()` warns about active users, then removes the device
   and drops its reference. It has no error return or active-user veto. Managed
   provider registration installs that unregister action. Retaining a reference
   to the sequencer object does not itself retain its parent driver's resource
   ownership through parent teardown.
3. Enable failure automatically attempts to disable dependencies; dependency
   rollback return values are ignored. A `post_enable` failure also attempts unit
   disable and clears the descriptor flag without checking that disable result.
   Splitting uncertain island activation and essential rails into independent
   units therefore does not prove safe recovery on every error path.

[Descriptor cleanup](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/power/sequencing/core.c#L701),
[provider unregister](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/power/sequencing/core.c#L541),
[dependency rollback](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/power/sequencing/core.c#L759),
[post-enable cleanup](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/power/sequencing/core.c#L910).

Pwrseq could organize a proven sequence under a retained provider, but it does
not remove the need for that owner to hold all essential prerequisites across
partial failure. Adding it outside genpd would also leave the established
platform pre-probe activation problem. The smaller source direction is thus
SCPSYS-owned sequencing, with failure retention implemented there before CONN
is exposed. Neither framework currently supplies a complete CONN implementation.

## Independent integration review

The upstream worker independently reviewed this handoff and its consumer-ordering
prerequisite, verifying six decisive upstream source files and the stable pwrseq
core against the recorded hashes. Project Planning accepts the source-only
direction and its explicit implementation blockers. With all required outer
preparation owned by the provider, a new single-domain bus bypass is not
inherently necessary; the earlier consumer-only proposal does not establish
such a bypass as a prerequisite for provider-owned sequencing.

The review found one additional pwrseq error path at both pins: a target's
`post_enable` callback is invoked even after `pwrseq_unit_enable` fails, and
its return replaces the earlier error. A successful `post_enable` can therefore
mask enable failure while the descriptor remains marked unpowered. This
strengthens the framework limitation above; no pwrseq fix or hardware result
is claimed here.
