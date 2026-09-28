#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the reviewed boot2 installer to the VCN28 read-only candidate."""

import importlib.util
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / '2026-09-27-mt6797-conn-domain-link-passive/install-passive.py'
SPEC = importlib.util.spec_from_file_location('conn_domain_installer', SOURCE)
DOMAIN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DOMAIN)
INSTALLER = DOMAIN.INSTALLER
INSTALLER.HERE = HERE
INSTALLER.EXPERIMENT = 'mt6351-vcn28-boot-observe'
INSTALLER.RECEIPT_NAME = 'mt6351-vcn28-boot-observe-deployment-1'
INSTALLER.MANIFEST_SHA = '03b0782e90125f3c7e2b047afc652305878a35367aa7fcb2b04c7330606c17e3'
PREDECESSOR_SHA = '07dfcc16b6c66442f47c5540eb24a9c1e057c6827d20787b74f39fe945569230'
BASE_ADAPT = DOMAIN.ORIGINAL_ADAPT


def adapt(source, candidate, previous):
    source = BASE_ADAPT(source, candidate, previous)
    anchor = 'already_current="$(single_value already_current "$probe_output")" || die '\
             "'invalid current-state evidence'\n"
    if source.count(anchor) != 1:
        raise ValueError('predecessor-check anchor changed')
    return source.replace(anchor,
                          '[[ "$predecessor_sha256" == ' + PREDECESSOR_SHA +
                          ' || "$predecessor_sha256" == "$CANDIDATE_SHA256" ]] || die '\
                          "'unexpected boot2 predecessor'\n" + anchor)


INSTALLER.adapt = adapt
validate = INSTALLER.validate
receipt = INSTALLER.receipt


if __name__ == '__main__':
    INSTALLER.main()
