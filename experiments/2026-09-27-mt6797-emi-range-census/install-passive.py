#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the reviewed boot2 installer to the EMI census candidate."""

import importlib.util
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / '2026-09-27-mt6797-conn-domain-link-passive/install-passive.py'
SPEC = importlib.util.spec_from_file_location('conn_domain_installer', SOURCE)
DOMAIN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DOMAIN)
INSTALLER = DOMAIN.INSTALLER
INSTALLER.HERE = HERE
INSTALLER.EXPERIMENT = 'mt6797-emi-range-census'
INSTALLER.RECEIPT_NAME = 'mt6797-emi-range-census-deployment-1'
INSTALLER.MANIFEST_SHA = '78da06050f529657c7464e8240fd317a6e50c26e8314a0bae73cb754a94761da'
PREDECESSOR_SHA = '0f2bb23cda82e8b119a823a4ffa68d6b60b0bd9399f592b5ee4d9db1909c7710'
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
