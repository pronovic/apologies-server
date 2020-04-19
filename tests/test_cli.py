# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:

import sys

import pytest

from apologiesserver.cli import _example, _lookup_method, cli


class TestCli:
    """
    Unit tests for the CLI interface.
    """

    def test_lookup_method(self):
        assert _lookup_method("_example") is _example
        with pytest.raises(AttributeError):
            assert _lookup_method("")
        with pytest.raises(AttributeError):
            assert _lookup_method("bogus")

    def test_cli(self):
        assert cli("_example") is sys.argv  # example simply returns its arguments
