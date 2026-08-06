#!/usr/bin/env python3
"""Model the bounded, fail-closed MT6797 PCM adapter admission order."""

from dataclasses import dataclass
from enum import Enum
import hashlib
import re


class Phase(Enum):
    UNAVAILABLE = "UNAVAILABLE"
    SNAPSHOTTED = "SNAPSHOTTED"
    RESOURCES_HELD = "RESOURCES_HELD"
    IMAGE_READY = "IMAGE_READY"
    RESET_INITIALIZED = "RESET_INITIALIZED"
    IMAGE_ACKED = "IMAGE_ACKED"
    CONTROL_INITIALIZED = "CONTROL_INITIALIZED"
    RUNNING = "RUNNING"
    LEASE_REGISTERED = "LEASE_REGISTERED"
    INVALIDATED = "INVALIDATED"
    FAULTED = "FAULTED"


class AdapterError(RuntimeError):
    pass


@dataclass(frozen=True)
class State:
    generation: int
    cluster_mask: int
    fields_complete: bool = True


@dataclass(frozen=True)
class Resources:
    cspm_base: int
    cspm_size: int
    csram_base: int
    csram_size: int
    clock_owner: str
    semaphore_owner: str
    held: bool = True


@dataclass(frozen=True)
class Image:
    digest: str
    target_revision: str
    loader_domain: str
    physical: int
    length: int
    alignment: int
    cache_maintained: bool
    lifetime: str


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class Adapter:
    REQUIRED_CLUSTER_MASK = 0xF
    CSPM_BASE = 0x11015000
    CSPM_SIZE = 0x1000
    CSRAM_BASE = 0x0012A000
    CSRAM_SIZE = 0x3000

    def __init__(self):
        self.phase = Phase.UNAVAILABLE
        self.state = None
        self.resources = None
        self.image = None
        self.lease_generation = None
        self.owner_handle = None
        self.reason = None

    def _require(self, *phases: Phase):
        if self.phase not in phases:
            raise AdapterError(f"phase={self.phase.value}")

    def _validate_state(self, state: State):
        if (state.generation <= 0 or
                state.cluster_mask != self.REQUIRED_CLUSTER_MASK or
                not state.fields_complete):
            raise AdapterError("incomplete startup state")

    def snapshot(self, state: State):
        self._require(Phase.UNAVAILABLE)
        self._validate_state(state)
        self.state = state
        self.phase = Phase.SNAPSHOTTED

    def hold_resources(self, resources: Resources):
        self._require(Phase.SNAPSHOTTED)
        if (resources.cspm_base != self.CSPM_BASE or
                resources.cspm_size != self.CSPM_SIZE or
                resources.csram_base != self.CSRAM_BASE or
                resources.csram_size != self.CSRAM_SIZE or
                not resources.clock_owner or
                not resources.semaphore_owner or
                not resources.held):
            raise AdapterError("resource ownership is incomplete")
        self.resources = resources
        self.phase = Phase.RESOURCES_HELD

    def admit_image(self, image: Image):
        self._require(Phase.RESOURCES_HELD)
        if (not re.fullmatch(r"[0-9a-f]{64}", image.digest) or
                not image.target_revision or
                image.loader_domain not in {"linux", "secure", "trusted-service"} or
                image.physical <= 0 or image.length <= 0 or
                image.alignment <= 0 or image.physical % image.alignment or
                not image.cache_maintained or not image.lifetime):
            raise AdapterError("image identity/residency is incomplete")
        self.image = image
        self.phase = Phase.IMAGE_READY

    def revalidate(self, state: State):
        self._validate_state(state)
        if self.state is None or state.generation != self.state.generation:
            self.invalidate("state-generation-changed")
            raise AdapterError("startup state changed")

    def initialize_reset(self, state: State):
        self._require(Phase.IMAGE_READY)
        self.revalidate(state)
        self.phase = Phase.RESET_INITIALIZED

    def acknowledge_image(self, state: State, acknowledged: bool = True):
        self._require(Phase.RESET_INITIALIZED)
        self.revalidate(state)
        if not acknowledged:
            self.fault("image-ready-timeout")
            raise AdapterError("image-ready timeout")
        self.phase = Phase.IMAGE_ACKED

    def initialize_control(self, state: State):
        self._require(Phase.IMAGE_ACKED)
        self.revalidate(state)
        self.phase = Phase.CONTROL_INITIALIZED

    def kick_pcm(self, state: State, acknowledged: bool = True):
        self._require(Phase.CONTROL_INITIALIZED)
        self.revalidate(state)
        if not acknowledged:
            self.fault("pcm-start-timeout")
            raise AdapterError("PCM start timeout")
        self.phase = Phase.RUNNING

    def register_lease(self, state: State):
        self._require(Phase.RUNNING)
        self.revalidate(state)
        self.lease_generation = state.generation
        self.phase = Phase.LEASE_REGISTERED

    def acquire(self, state: State, owner_handle: int):
        self._require(Phase.LEASE_REGISTERED)
        self.revalidate(state)
        if not owner_handle:
            raise AdapterError("missing firmware owner handle")
        self.owner_handle = owner_handle

    def release(self, state: State, owner_handle: int):
        self._require(Phase.LEASE_REGISTERED)
        self.revalidate(state)
        if self.owner_handle != owner_handle:
            raise AdapterError("stale firmware owner handle")
        self.owner_handle = None

    def invalidate(self, reason: str):
        self.owner_handle = None
        self.lease_generation = None
        self.reason = reason
        self.phase = Phase.INVALIDATED

    def fault(self, reason: str):
        self.owner_handle = None
        self.lease_generation = None
        self.reason = reason
        self.phase = Phase.FAULTED


def expect_failure(fn, label: str):
    try:
        fn()
    except AdapterError:
        return
    raise AssertionError(f"accepted forbidden transition: {label}")


def make_image() -> Image:
    return Image(_digest("exact-reference-image"), "mt6797-gemini-rev1",
                 "secure", 0x48000000, 2025 * 4, 4, True, "owner-held")


def make_resources() -> Resources:
    return Resources(Adapter.CSPM_BASE, Adapter.CSPM_SIZE,
                     Adapter.CSRAM_BASE, Adapter.CSRAM_SIZE,
                     "mt6797-clock-owner", "mt6797-semaphore-owner")


def happy_path() -> Adapter:
    adapter = Adapter()
    state = State(7, Adapter.REQUIRED_CLUSTER_MASK)
    adapter.snapshot(state)
    adapter.hold_resources(make_resources())
    adapter.admit_image(make_image())
    adapter.initialize_reset(state)
    adapter.acknowledge_image(state)
    adapter.initialize_control(state)
    adapter.kick_pcm(state)
    adapter.register_lease(state)
    adapter.acquire(state, 0xA72)
    adapter.release(state, 0xA72)
    assert adapter.phase is Phase.LEASE_REGISTERED
    return adapter


def main():
    cases = 0
    happy_path()

    expect_failure(lambda: Adapter().register_lease(State(1, 0xF)),
                   "premature callback registration")
    cases += 1

    incomplete = Adapter()
    expect_failure(lambda: incomplete.snapshot(State(1, 0xF, False)),
                   "incomplete state")
    cases += 1

    wrong_resources = Adapter()
    wrong_resources.snapshot(State(1, 0xF))
    expect_failure(lambda: wrong_resources.hold_resources(
        Resources(Adapter.CSPM_BASE, Adapter.CSPM_SIZE, 0, Adapter.CSRAM_SIZE,
                   "clock", "semaphore")), "wrong CSRAM identity")
    cases += 1

    wrong_image = Adapter()
    wrong_image.snapshot(State(1, 0xF))
    wrong_image.hold_resources(make_resources())
    expect_failure(lambda: wrong_image.admit_image(
        Image("not-a-digest", "rev", "secure", 0x48000000, 8, 4, True, "held")),
        "unidentified image")
    cases += 1

    stale = Adapter()
    stale.snapshot(State(1, 0xF))
    stale.hold_resources(make_resources())
    stale.admit_image(make_image())
    expect_failure(lambda: stale.initialize_reset(State(2, 0xF)),
                   "stale generation before reset")
    assert stale.phase is Phase.INVALIDATED
    cases += 1

    blocked = Adapter()
    blocked.snapshot(State(1, 0xF))
    blocked.hold_resources(make_resources())
    blocked.admit_image(make_image())
    blocked.initialize_reset(State(1, 0xF))
    blocked.acknowledge_image(State(1, 0xF))
    blocked.initialize_control(State(1, 0xF))
    blocked.kick_pcm(State(1, 0xF))
    blocked.register_lease(State(1, 0xF))
    blocked.acquire(State(1, 0xF), 0xA72)
    expect_failure(lambda: blocked.release(State(1, 0xF), 0xA73),
                   "stale owner handle")
    cases += 1

    invalidated = happy_path()
    invalidated.invalidate("suspend-resume")
    expect_failure(lambda: invalidated.acquire(State(7, 0xF), 0xA72),
                   "lease after invalidation")
    cases += 1

    print("adapter_contract=bounded_pcm_admission")
    print("happy_path=SNAPSHOTTED>RESOURCES_HELD>IMAGE_READY>RESET_INITIALIZED>IMAGE_ACKED>CONTROL_INITIALIZED>RUNNING>LEASE_REGISTERED")
    print("negative_cases=%d" % cases)
    print("premature_lease=reject")
    print("incomplete_state=reject")
    print("resource_identity=exact")
    print("image_identity=sha256_target_revision_loader_domain_residency")
    print("generation_revalidation=reject_stale_and_invalidate")
    print("owner_handle=exact_and_generation_bound")
    print("suspend_resume=invalidates_before_callback")
    print("hardware_writes=0")
    print("device_action=none")
    print("status=PASS_PCM_ADAPTER_MODEL")


if __name__ == "__main__":
    main()
