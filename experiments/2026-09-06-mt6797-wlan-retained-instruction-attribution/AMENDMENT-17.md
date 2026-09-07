# Exact getpagesize invocation amendment

This seventeenth prospective amendment resolves only the exact pre-call join in
[RESOURCE-CALLSITE-DIAGNOSTIC-2.md](RESOURCE-CALLSITE-DIAGNOSTIC-2.md). All
earlier bootstraps, refusals and diagnostics remain immutable. V2 joined the
exact frozen `resource.getpagesize` object to the sole frozen
`elftools.elf.elffile` line-17 callsite, then stopped at the documented
`c_call` pre-call boundary. It did not execute the function or complete the
package import. No engine, method, callback or private read occurred; the
single private analysis remains unused.

Python 3.12 documents `resource.getpagesize()` as a zero-argument function that
returns the number of bytes in a system page; see
<https://docs.python.org/3.12/library/resource.html#resource.getpagesize>.
Python documents `os.sysconf(name)` as returning an integer-valued system
configuration value; see
<https://docs.python.org/3.12/library/os.html#os.sysconf>. The upstream
pyelftools v0.30 source at
<https://github.com/eliben/pyelftools/blob/v0.30/elftools/elf/elffile.py>
has SHA-256
`457c93c8be327cbce2a86869aa40d9067f12f7c33052730f7e1cbcccb99b9b54`,
identical to the frozen installed source, and assigns the zero-argument call's
result to module global `PAGESIZE` at line 17.

These sources support only the exact query and assignment below. They do not
admit any resource-limit getter/setter, usage query, arbitrary extension call
or general package-native route.

Before replacement preflight, pin and verify in [inputs.json](inputs.json) the
exact SHA-256 values of this amendment, the amended
[WORK_ITEM.md](WORK_ITEM.md), all earlier controlling artifacts and the complete
v2 callsite-diagnostic trio. Reject drift.

## One exact query and return

Create and freeze `bootstrap-v8.json` with the complete two-mode bootstrap and
embedded SHA-256 before first execution. Reproduce the Amendment 13 dual-
inventory gate, Amendment 12 exact resource preload, Amendment 15 caller tuple,
and every v7 engine/lifetime/privacy predicate not superseded below.

Before package source entry, require exact frozen source SHA-256 and a unique
AST join in the module-level `try` body: line 16 imports `resource`; line 17 is
one assignment to the sole name `PAGESIZE`; its value is exactly a direct
`resource.getpagesize()` call with no positional arguments, keywords, star
arguments, decorator, comprehension or nested callable. Require no other
resource call candidate in any of the 52 frozen pyelftools sources.

Before installing the resource-call profile, call exactly
`os.sysconf("SC_PAGE_SIZE")` once under a distinct owner
`stdlib-page-size-reference`. Require `SC_PAGE_SIZE` is present in the frozen
`os.sysconf_names` dictionary and its mapped value is an integer but not a
boolean; freeze that name/value pair. Require the returned value is also an
integer but not a boolean, between 512 and 65536 inclusive, and a power of two.
This is the sole independent reference query. Require it creates no import,
file-backed mapping delta, resource event, write, cache, network or process
event.

Install a dedicated profile function before the top-level pyelftools import.
Admit exactly one `c_call` only when all of these hold:

- the function object is the exact frozen module-dictionary
  `resource.getpagesize` object and has exact module/name;
- the live binding is unchanged, and the caller frame is the exact frozen
  `elftools.elf.elffile` source at line 17 with the unique AST join above;
- the cached resource request, spec/create/exec/extension counters and complete
  resource/file-backed mapping identity equal their frozen expected state; and
- no earlier resource call/return/exception, engine, callback, method, private
  read or forbidden operation occurred.

Set state `entered` and return normally from the observer. While entered,
require the next matching resource event to be exactly one `c_return` for the
same function object and caller frame/line; refuse `c_exception`, a different
resource object, recursion, another resource event or an event-order mismatch.
Set state `returned`. No other resource `c_call`, `c_return` or `c_exception`
is admitted.

After the exact pyelftools module completes, require its global `PAGESIZE` is an
integer but not a boolean, equals the frozen `os.sysconf("SC_PAGE_SIZE")`
reference, remains within the same power-of-two bounds, and is not replaced or
deleted through final drift. Require every entered mapped module body to
complete within the exact 77-entry budget; as in Amendment 7, do not require
all 77 mapped sources to be demanded. Require pyelftools adds no file-backed
mapping/native request, and resource counters are exactly one
lookup/create/exec/extension/cached request/function call/function return with
zero function exceptions. Then continue v7's engine construction,
optional-route, mapping, component, restoration and final-drift checks.

Do not describe `getpagesize` as pure or side-effect-free beyond the documented
query/return contract and the observed unchanged guarded state. Do not admit
another resource function, argument, second call, exception fallback or value
source.

## Replacement v8 lifecycle

Run exactly one no-ELF v8 preflight. It must prove the complete tool/resource/
page-size/engine lifecycle with callback absent and zero private reads. A
failure writes only `VALIDATION-V8-REFUSED.md` and stops.

Only a complete successful v8 receipt may feed a newly frozen `method.json`.
Then at most the still-unused one analysis-mode child may run using Amendment
8's exact inherited-pipe method, existing-engine callback and pre/post-analysis
drift lifecycle. A post-private refusal consumes that one execution; no retry
is admitted. A successful final result uses the existing named analysis,
verifier, freeze, README and validation outputs.

No acquisition, network, device action or build is admitted. This narrow query
establishes no private-binary behavior, runtime driver invocation, teardown
safety, resource release, firmware success, radio operation or hardware
support.
