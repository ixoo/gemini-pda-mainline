# Provider release refusal design

The lifecycle now has an explicit shape:

    R01 acquire -> R02 held provider -> release callback -> rollback or refusal

The current provider implements only the left-hand refusal edges. Its release
callback validates its arguments, records a returned response, and returns
-EOPNOTSUPP. The owner registry serializes the callback with registration
and unregister, so a provider context cannot be released while a callback is
in flight.

This is intentionally not a write API. A future writable implementation must
first provide all of the following in the provider-owned context:

1. an exact DA921x page/selector owner and an entry-state readback;
2. a single bounded BUCKB mutation with a preserved control-byte mask;
3. post-settle enable and VSEL readbacks;
4. a same-generation handle proving which owner may release the rail; and
5. an inverse operation that writes only after the complete post-state is
   revalidated, otherwise terminating in fault-retain.

No field in the current refusal response authorizes any of those writes.
