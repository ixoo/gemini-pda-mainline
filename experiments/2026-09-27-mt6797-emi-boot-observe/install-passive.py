#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the reviewed boot2 installer to the EMI read-only candidate."""

import importlib.util
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / '2026-09-27-mt6797-conn-domain-link-passive/install-passive.py'
SPEC = importlib.util.spec_from_file_location('conn_domain_installer', SOURCE)
DOMAIN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DOMAIN)
INSTALLER = DOMAIN.INSTALLER
INSTALLER.HERE = HERE
INSTALLER.EXPERIMENT = 'mt6797-emi-boot-observe'
INSTALLER.RECEIPT_NAME = 'mt6797-emi-boot-observe-deployment-1'
INSTALLER.MANIFEST_SHA = '455d10057108503f64094d77c1a97ff4c99de2b860de0d39f15b25a3778c10a4'
PREDECESSOR_SHA = 'a592c6032e26da3fc6125d954a134a20a30072dbf0f550f585901869e2ce536b'
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
MANIFEST_SHA = INSTALLER.MANIFEST_SHA
validate = INSTALLER.validate
receipt = INSTALLER.receipt


if __name__ == '__main__':
    INSTALLER.main()
