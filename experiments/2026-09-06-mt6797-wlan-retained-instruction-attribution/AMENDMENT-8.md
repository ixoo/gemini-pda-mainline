# Single-process analysis callback amendment

This eighth prospective amendment resolves the v6 analysis-handoff ambiguity
identified before any v6 file was created or executed. All earlier contracts,
bootstraps, refusals and diagnostics remain immutable. No new preflight or
private read occurred; the single private analysis remains unused.

The earlier bootstrap keeps the constructed Capstone engine and pyelftools
`ELFFile` class local, restores the source finder/native-load endpoint/path,
then performs final drift before returning. Recreating the engine afterward
would require a forbidden post-restoration decoder/native route, while handing
it to an unspecified later harness would leave lifetime and final-drift
chronology ambiguous. Amendment 7 changes only module budgeting, so this
separate amendment defines the sole handoff explicitly.

Before v6 construction, pin and verify in [inputs.json](inputs.json) the exact
SHA-256 values of this amendment, the amended [WORK_ITEM.md](WORK_ITEM.md), all
earlier amendments and every earlier bootstrap/refusal/diagnostic input.
Reject drift.

## One bootstrap, two frozen modes

`bootstrap-v6.json` must contain one complete independently written bootstrap
with an explicit immutable mode selected at process start:

- `preflight` reproduces the complete tool import, engine construction,
  mapping/native closure, named restoration and final drift lifecycle without
  accepting or invoking an analysis callback and without opening the private
  ELF. It emits the sanitized tool receipt and exits.
- `analysis` is used only by the later single private child. It reproduces all
  of the same identities, imports, engine construction, mapping/native closure
  and named restoration. After an additional complete pre-analysis component,
  package-tree and mapping drift pass, it invokes exactly one already frozen
  analysis callback in the same process, then performs the mandatory final
  component/package/mapping drift pass and exits.

Refuse an absent/unknown mode, a callback in preflight mode, no callback or
more than one callback invocation in analysis mode, or any lifecycle branch
not shared up to the explicit callback boundary. The irreversible audit hook
is installed before metadata discovery and remains active throughout either
process. The restored finder, native endpoint and isolated `sys.path` must stay
restored before, during and after callback execution; decoder imports and new
native-load requests remain forbidden after restoration.

## Frozen callback interface

The successful preflight receipt is necessary but cannot itself run or define
the callback. Use it to create `method.json` containing the complete callback,
ELF mapper, independent raw decoder, CFG/scans and result serializer source,
plus exact source hashes and every tool identity. Freeze and verify this file
before starting analysis mode.

The outer collector verifies the complete `method.json`, then supplies those
exact bytes to the private child on one inherited read-only input pipe; no
method path lookup is admitted inside the child. After installing its audit
hook, the child reads the pipe once, independently re-verifies the complete
method and callback-source hashes before package import or private access, and
closes it. Compile the exact callback source once in memory without an ordinary
finder, bytecode, path search or dynamic import. Before invocation, require the
callback code-object identity and source hash to equal the method freeze. Pass
exactly one immutable capability object containing only:

- the already constructed and configured Capstone engine;
- the already source-forced pyelftools `ELFFile` class;
- the frozen private-ELF identity and four accepted target envelopes;
- one exact-private-ELF read-only opener governed by the audit and original
  analysis limits; and
- immutable sanitized tool/mapping receipt data required by the verifier.

Do not expose the terminal finder, native-load wrapper, mutable module map,
raw package sources, arbitrary filesystem helper, subprocess, network, device
or second-run capability. The callback may open the exact private ELF once
through that function and returns its one bounded in-memory result to the
bootstrap; it has no filesystem result writer. The outer collector alone may
write the two already admitted private pipe captures. The callback may use the
existing engine and `ELFFile` class but must not import, instantiate a second
engine, reload a package, change decoder configuration, inspect vDSO bytes or
retain an object beyond process exit.

The callback returns one in-memory result object. The bootstrap validates its
bounded schema and authority fields before serialization, records invocation
entered/completed state, and refuses a successful result if the callback did
not return normally or any post-callback drift/restoration/audit predicate
fails. A refusal after private opening consumes the one private-analysis budget
and cannot be repaired with another run.

## Chronology and claims

Freeze `bootstrap-v6.json`, run exactly one no-ELF preflight process, freeze
`method.json` only from its successful receipt, then run at most one separate
analysis-mode process. Sharing the interface means sharing frozen source and
predicates, not sharing live Python objects across processes. The analysis
engine/class exist only for the lifetime of their own child and are never
recreated after its restoration boundary.

The preflight final drift proves only the no-ELF tool process. The private
child must separately pass both its pre-analysis and post-callback final drift
checks. No claim may merge their process identities, mapping addresses or live
objects. This interface change grants no new input, analysis scope, decoder
semantics, runtime/hardware conclusion, acquisition, network, device action or
build authority.
