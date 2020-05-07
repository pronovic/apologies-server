# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:

import os

from apologiesserver.util import homedir, setup_logging


class TestUtil:
    """
    Unit tests for utilities.
    """

    def test_homedir(self):
        assert homedir() == os.path.expanduser("~")  # different way to get same value

    def test_setup_logging(self):
        setup_logging(quiet=True, verbose=False, debug=False)  # just confirm that it runs
        setup_logging(quiet=False, verbose=True, debug=False)  # just confirm that it runs
        setup_logging(quiet=False, verbose=False, debug=True)  # just confirm that it runs
