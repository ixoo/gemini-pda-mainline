# SPDX-License-Identifier: GPL-2.0-only
"""Synthetic-testable image sequencing; no file, device or secure-call adapter.

Provider objects are trusted implementations, not a security boundary against
malicious Python code. This module supplies no provider admission mechanism.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
import struct

from wifi_firmware import (EMI_OFFSET_MASK, EMI_WINDOW_BYTES, MAX_FILE_BYTES,
                           MTKE_HEADER_SIZE, ENTRY_SIZE, Refusal, parse_mtke)

SMC32_EMI_SET = 0x82000209  # Observed literal, including on vendor ARM64.
STATUS_NAMES = {0: "success", -1: "unsupported", -2: "invalid_parameters",
                -3: "invalid_range", -4: "permission_denied"}


class SecureFailure(Exception):
    def __init__(self, status):
        self.status = status  # Preserve signed firmware status, including unknowns.
        super().__init__(STATUS_NAMES.get(status, "unknown_secure_status"))


def check_status(status):
    if type(status) is not int or not -(1 << 31) <= status < (1 << 31):
        raise Refusal("invalid_secure_status_representation")
    if status != 0:
        raise SecureFailure(status)


class Session:
    """Identity of one non-retryable image attempt."""


@dataclass(frozen=True)
class Reservation:
    base: int
    size: int

    def __post_init__(self):
        # Conservative synthetic SMC32 address envelope, not firmware alignment.
        if (type(self.base) is not int or type(self.size) is not int or
                not 0 < self.base < (1 << 32) or
                self.size < EMI_WINDOW_BYTES or
                self.size > (1 << 32) - self.base):
            raise Refusal("invalid_reservation")

    def span(self, offset, length):
        if (type(offset) is not int or type(length) is not int or
                offset < 0 or offset > EMI_WINDOW_BYTES or length <= 0 or
                length > EMI_WINDOW_BYTES - offset):
            raise Refusal("emi_range_outside_owned_window")
        return self.base + offset, self.base + offset + length - 1


@dataclass(frozen=True)
class Protection:
    # Explicit provider-admitted policies; no default domain permissions.
    writable: int
    restricted: int

    def __post_init__(self):
        for value in (self.writable, self.restricted):
            if type(value) is not int or not 0 <= value < (1 << 24):
                raise Refusal("invalid_protection_policy")


class EmiLease(ABC):
    """An exclusive provider-owned reservation, retained after START submission.

    check_owned must raise on lost ownership. secure_set returns signed int32;
    copy and visible return None only after completion or raise on failure.
    Provider owns mapping, visibility and serialized protection/remap access.
    All leases remain retained for firmware lifetime/recovery, never released
    by this planner. A provider must not recycle memory after START.
    """

    def __init__(self, reservation, session, protection):
        if (not isinstance(reservation, Reservation) or
                not isinstance(session, Session) or
                not isinstance(protection, Protection)):
            raise Refusal("invalid_owner_binding")
        self.reservation = reservation
        self.session = session
        self.protection = protection

    @abstractmethod
    def check_owned(self):
        pass

    @abstractmethod
    def secure_set(self, function_id, start, inclusive_end, region_permission):
        pass

    @abstractmethod
    def copy(self, offset, data):
        pass

    @abstractmethod
    def visible(self):
        pass


class EmiOwner(ABC):
    @abstractmethod
    def acquire(self, session):
        """Return an actual exclusive EmiLease, not a Boolean permission flag."""


class OrdinaryTransport(ABC):
    @abstractmethod
    def submit(self, session, destination, data, encrypted, key_index):
        """Return None after CONFIG ACK and all PDA submissions; otherwise raise.

        A future adapter must use the frozen ordinary-section implementation.
        This boundary neither infers a CONFIG ACK nor duplicates its protocol.
        """

    @abstractmethod
    def start(self, session):
        """Submit START under its existing contract; readiness remains separate."""


@dataclass(frozen=True)
class Section:
    destination: int
    data: bytes
    encrypted: bool
    key_index: int


class Phase(Enum):
    NEW = auto()
    SECTIONS = auto()
    READY = auto()
    START_SUBMITTED = auto()
    FAILED = auto()


def completed(result):
    if result is not None:
        raise Refusal("invalid_provider_completion")


class WholeImage:
    def __init__(self, image, owner, ordinary):
        if not isinstance(image, (bytes, bytearray)) or len(image) > MAX_FILE_BYTES:
            raise Refusal("invalid_image_input")
        image = bytes(image)  # Own immutable snapshot before validation/extraction.
        metadata = parse_mtke(image)
        if metadata["status"] != "structurally_valid":
            raise Refusal("image_not_structurally_valid")
        if not isinstance(owner, EmiOwner) or not isinstance(ordinary, OrdinaryTransport):
            raise Refusal("missing_provider_object")
        sections = []
        for index in range(metadata["section_count"]):
            offset, key, encrypted, _, length, destination = struct.unpack_from(
                "<IBBHII", image, MTKE_HEADER_SIZE + ENTRY_SIZE * index)
            sections.append(Section(destination, image[offset:offset + length],
                                    bool(encrypted), key & 3))
        self._sections = tuple(sections)
        self._owner = owner
        self._ordinary = ordinary
        self._session = Session()
        self._lease = None
        self._binding = None
        self._phase = Phase.NEW
        self._next = 0
        self._protection_attempted = False
        self._restore_attempted = False
        self.failure = None
        self.restore_failure = None
        self._busy = False

    @property
    def phase(self):
        return self._phase

    @property
    def sections_complete(self):
        return self._next

    def _owned(self):
        lease = self._lease
        if (lease is None or lease.session is not self._session or
                lease.reservation is not self._binding[0] or
                lease.protection is not self._binding[1]):
            raise Refusal("owner_binding_changed")
        completed(lease.check_owned())

    def _protect(self, policy):
        self._owned()
        start, end = self._lease.reservation.span(0, EMI_WINDOW_BYTES)
        check_status(self._lease.secure_set(SMC32_EMI_SET, start, end,
                                           (18 << 27) | policy))

    def _fail(self, error):
        self._phase = Phase.FAILED
        self.failure = error
        # Even a failing set/copy may have side effects. Make one bounded restore
        # attempt under the same owner; never release, retry the image or START.
        if self._protection_attempted and not self._restore_attempted:
            self._restore_attempted = True
            try:
                self._protect(self._binding[1].restricted)
            except BaseException as restore_error:
                self.restore_failure = restore_error

    def step(self):
        """One whole section, or final visibility/protection step. No polling."""
        if self._busy or self._phase not in (Phase.NEW, Phase.SECTIONS):
            raise Refusal("invalid_image_phase")
        self._busy = True
        try:
            if self._phase is Phase.NEW:
                lease = self._owner.acquire(self._session)
                if not isinstance(lease, EmiLease):
                    raise Refusal("missing_reservation_lease")
                self._lease = lease
                self._binding = (lease.reservation, lease.protection)
                self._owned()
                for section in self._sections[2:]:
                    lease.reservation.span(section.destination & EMI_OFFSET_MASK,
                                           len(section.data))
                self._phase = Phase.SECTIONS
            self._owned()
            if self._next == len(self._sections):
                completed(self._lease.visible())
                if self._protection_attempted:
                    # Do not automatically repeat a failed final restore.
                    self._restore_attempted = True
                    self._protect(self._binding[1].restricted)
                self._owned()
                self._phase = Phase.READY
                return
            section = self._sections[self._next]
            if self._next < 2:
                completed(self._ordinary.submit(self._session, section.destination,
                                               section.data, section.encrypted,
                                               section.key_index))
            else:
                if not self._protection_attempted:
                    self._protection_attempted = True
                    self._protect(self._binding[1].writable)
                offset = section.destination & EMI_OFFSET_MASK
                self._lease.reservation.span(offset, len(section.data))
                completed(self._lease.copy(offset, section.data))
            self._owned()
            self._next += 1
        except BaseException as error:
            self._fail(error)
            raise
        finally:
            self._busy = False

    def abort(self):
        """Caller deadline/cancellation: retain ownership and block START."""
        if self._busy or self._phase in (Phase.FAILED, Phase.START_SUBMITTED):
            raise Refusal("invalid_abort_phase")
        self._busy = True
        try:
            self._fail(Refusal("image_aborted"))
        finally:
            self._busy = False

    def start(self):
        if self._busy or self._phase is not Phase.READY:
            raise Refusal("start_before_whole_image_completion")
        self._busy = True
        try:
            self._owned()
            completed(self._ordinary.start(self._session))
            self._owned()
            self._phase = Phase.START_SUBMITTED
        except BaseException as error:
            self._fail(error)
            raise
        finally:
            self._busy = False
