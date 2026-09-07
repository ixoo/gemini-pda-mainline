# V8 mode-specific method-state clarification

This eighteenth prospective amendment resolves only a two-mode wording
conflict in [AMENDMENT-17.md](AMENDMENT-17.md) before v8 construction or
execution. Every earlier artifact remains immutable. Neither the v8 preflight
nor the single private analysis has run.

Amendment 17's exact `getpagesize` `c_call` gate says no earlier method or
callback occurred. Apply that predicate by mode, consistently with
[AMENDMENT-8.md](AMENDMENT-8.md):

- in `preflight` mode, the method and callback must both be absent, callback
  count zero and private-open count zero; and
- in `analysis` mode, only the already frozen post-preflight method may have
  been read exactly once from the inherited read-only pipe, hash/schema-
  verified and used to compile the exact callback before package import. The
  callback may exist but must remain uninvoked, with callback count zero,
  callback state `absent`, private-open count zero and no decoder engine at the
  page-size call boundary.

In both modes, no method artifact or source may be authored, derived, rewritten
or persisted in the child. Analysis mode may deserialize exactly one in-memory
method object solely from the hash/schema-verified frozen pipe bytes; that
object may not be mutated. No callback may run, and no private path or content
may be accessed before the existing post-engine/pre-analysis gates. The method
object, callback source/code
identity and zero-use state in analysis mode must remain exact through resource
preload, page-size query, package completion, engine construction and every
pre-analysis drift/restoration check. Only then may Amendment 8's single
callback invocation and private opener proceed.

This clarification does not weaken the one-preflight prerequisite: analysis
mode remains impossible until a complete successful v8 receipt has been
reviewed and used to freeze `method.json`. A v8 preflight refusal still stops
without any method or analysis child.

Before v8, pin and verify in [inputs.json](inputs.json) the exact SHA-256 values
of this amendment and the amended [WORK_ITEM.md](WORK_ITEM.md), in addition to
every existing controlling and dependency hash. Reject drift. No resource
function, engine, method creation, callback, private read, network, device
action or build is admitted by this clarification itself.
