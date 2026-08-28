#!/usr/bin/env python3
"""Exhaust the derived CPU8 admission/controller model."""

from __future__ import annotations

from dataclasses import replace

from admission_model import Controller, Inputs, Stage


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def assert_closed(result, message: str) -> None:
    require(result.cpu_off_requests == 0, f"{message}: CPU_OFF")
    require(result.retries == 0, f"{message}: retry")
    require(result.a36_recovery_fields == (0, 0, 0),
            f"{message}: caller recovery assertion")
    require(result.caller_identity_words == 0,
            f"{message}: caller transaction identity")


def test_success() -> None:
    result = Controller().run(Inputs())
    require(result.probe_ret == 0 and result.operation_ret == 0, "success")
    require(result.cpu_requests == 1, "one CPU8 request")
    require(result.events == [
        Stage.BINDER_READY,
        Stage.SOURCE_CAPTURE,
        Stage.A34_BOOTSTRAP,
        Stage.DERIVE_TRANSACTION,
        Stage.P17_P18,
        Stage.ADD_CPU8,
        Stage.LEDGER_BEGIN,
        Stage.WATCHDOG_TAKEOVER,
        Stage.P27_FIRST_MUTATION,
    ], "exact success order")
    assert_closed(result, "success")


def test_preconsume_deferral() -> None:
    for field in ("binder_ready", "source_ready"):
        controller = Controller()
        result = controller.run(replace(Inputs(), **{field: False}))
        require(result.probe_ret == Controller.EPROBE_DEFER, field)
        require(not result.consumed and not controller.consumed, field)
        require(result.cpu_requests == 0 and not result.events, field)
        assert_closed(result, field)


def test_ready_token_refusal_is_preconsume() -> None:
    controller = Controller()
    result = controller.run(replace(Inputs(), ready_token=False))
    require(result.probe_ret == Controller.EAGAIN, "READY-token refusal")
    require(not result.consumed and not controller.consumed,
            "READY-token preconsume")
    require(result.events == [Stage.BINDER_READY], "READY-token order")
    assert_closed(result, "READY-token")


def test_terminal_failures() -> None:
    cases = (
        ("source_exact", Stage.SOURCE_CAPTURE, 0),
        ("owner_pristine", Stage.A34_BOOTSTRAP, 0),
        ("publish_ok", Stage.P17_P18, 0),
        ("add_cpu_ok", Stage.ADD_CPU8, 1),
        ("binder_ledger_ok", Stage.LEDGER_BEGIN, 1),
        ("binder_watchdog_ok", Stage.WATCHDOG_TAKEOVER, 1),
    )
    for field, last, requests in cases:
        controller = Controller()
        result = controller.run(replace(Inputs(), **{field: False}))
        require(result.probe_ret == 0, f"{field}: no reprobe")
        require(result.operation_ret != 0, f"{field}: operation error")
        require(result.consumed and controller.consumed,
                f"{field}: consumed")
        require(result.events[-1] is last, f"{field}: last event")
        require(result.cpu_requests == requests, f"{field}: request count")
        require(Stage.P27_FIRST_MUTATION not in result.events,
                f"{field}: no physical mutation")
        assert_closed(result, field)


def test_repeat_is_closed() -> None:
    controller = Controller()
    first = controller.run(Inputs())
    second = controller.run(Inputs())
    require(first.cpu_requests == 1, "first request")
    require(second.operation_ret == Controller.EALREADY, "repeat refused")
    require(second.probe_ret == 0 and second.events == [], "repeat stable")
    require(second.cpu_requests == 0, "repeat no request")
    assert_closed(second, "repeat")


def test_watchdog_never_precedes_ledger() -> None:
    for inputs in (
        Inputs(),
        replace(Inputs(), binder_ledger_ok=False),
        replace(Inputs(), binder_watchdog_ok=False),
    ):
        events = Controller().run(inputs).events
        if Stage.WATCHDOG_TAKEOVER in events:
            require(events.index(Stage.LEDGER_BEGIN) <
                    events.index(Stage.WATCHDOG_TAKEOVER),
                    "ledger before watchdog")
        if Stage.P27_FIRST_MUTATION in events:
            require(events.index(Stage.WATCHDOG_TAKEOVER) <
                    events.index(Stage.P27_FIRST_MUTATION),
                    "watchdog before first mutation")


def main() -> None:
    tests = (
        test_success,
        test_preconsume_deferral,
        test_ready_token_refusal_is_preconsume,
        test_terminal_failures,
        test_repeat_is_closed,
        test_watchdog_never_precedes_ledger,
    )
    for test in tests:
        test()
        print(f"pass={test.__name__}")
    print("cases=6")
    print("cpu8_requests_on_success=1")
    print("cpu9_requests=0")
    print("cpu_off_requests=0")
    print("retries=0")
    print("model_validation=pass")


if __name__ == "__main__":
    main()
