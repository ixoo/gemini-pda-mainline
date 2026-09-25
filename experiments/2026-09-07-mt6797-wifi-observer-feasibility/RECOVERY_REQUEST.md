# Refuse request-route changes after recovery takeover

The selected 52-patch kernel's linked symbol map contains both
`mtk_wdt_request_en_set()` and `mtk_wdt_request_mode_set()`. Its prepared source
has the exact watchdog file hash in the [source receipt](results/recovery-request-sources.json).
Both functions take the existing TOPRGU register lock, then write request-mode
or request-IRQ registers without testing the capture/recovery ownership flag.
The enable function can also write `EXT_REQ_CON`. An ordinary caller already
waiting for that lock can therefore change request routing after the timed
capture claims watchdog ownership. This is a source and linked-symbol finding,
not an observation of such a call on the PDA.

The [patch](patches/recovery-request/0001-watchdog-refuse-request-route-changes-after-capture.patch)
checks ownership under that lock in both setters and returns `-EBUSY` before
any register read or write. Before takeover, it retains the original operations.
The flag and lock are provided by the existing recovery patches. This is one
logical experiment change after the selected 52-patch parent; its synthetic
archive identity is not a DCO sign-off or upstream submission. It is the final
entry in the 53-patch [compile-only input](full-kernel-inputs.json); this does
not admit a new boot candidate or device action.

The [focused fixture](test-recovery-request.py) compiles the two complete
native function bodies from both source states. It injects register storage,
the existing lock and a caller paused before acquiring that lock. All nine
parent cases write, including each case already waiting when ownership changes.
The patched experiment cases retain pre-takeover writes but refuse every post-takeover
call without changing either request register or the external request
configuration. With the experiment configuration disabled, both source states
retain the original writes. The exact patch replays and reverses byte-for-byte;
strict Checkpatch reports zero findings with only the synthetic sign-off
exception.

The [53-patch native link](results/recovery-request-link.json) passed on Buildbox.
Its verified package contains both setter symbols and no unresolved symbols.
In each linked setter, the ownership load follows the register spinlock and
branches to an `-EBUSY` unlock before the first request-register read. The
configuration is byte-identical to the 52-patch parent. The inherited build
still reports 69 section mismatches.

The fixture and link do not prove real spinlock scheduling, register completion
or which request clients can run during the cycle. Direct request writers,
caller/configuration isolation, shared subsystem reset ownership and the full
recovery budget remain open. No radio, watchdog takeover, new boot image or
device action is admitted by this patch.

The later [selected-source audit](RECOVERY_SUBSYSTEM.md#request-route-writer-boundary)
narrows the active request-route writers for this exact configuration. It does
not turn the two-setter result into whole-TOPRGU ownership.
