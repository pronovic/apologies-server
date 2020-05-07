# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:

import sys
from unittest.mock import Mock, patch

import pytest

from apologiesserver.cli import _example, _lookup_method, cli, run_server


class TestUtil:
    """
    Unit tests for the general CLI code.
    """

    def test_cli(self):
        # When a script is invoked, it gets arguments like shown below - that's just how it works
        with patch.object(sys, "argv", ["src/scripts/example", "example", "a", "b", "c"]):
            assert cli("_example") == ["a", "b", "c"]

    def test_lookup_method(self):
        assert _lookup_method("_example") is _example
        with pytest.raises(AttributeError):
            assert _lookup_method("")
        with pytest.raises(AttributeError):
            assert _lookup_method("bogus")


@patch("apologiesserver.cli.server")
@patch("apologiesserver.cli.config")
@patch("apologiesserver.cli.setup_logging")
@patch("apologiesserver.cli.load_config")
class TestRunServer:
    """
    Unit tests for the server CLI.
    """

    def test_run_server_defaults(self, load_config, setup_logging, config, server):
        config.return_value = Mock(logfile_path="path")
        argv = []
        run_server(argv=argv)
        load_config.assert_called_once_with(None, {})
        setup_logging.assert_called_once_with(False, False, False, "path")
        server.assert_called_once()

    def test_run_server_h(self, _load_config, _setup_logging, config, _server):
        config.return_value = Mock(logfile_path="path")
        argv = ["-h"]
        with pytest.raises(SystemExit):
            run_server(argv=argv)

    def test_run_server_help(self, _load_config, _setup_logging, config, _server):
        config.return_value = Mock(logfile_path="path")
        argv = ["--help"]
        with pytest.raises(SystemExit):
            run_server(argv=argv)

    def test_run_server_quiet(self, load_config, setup_logging, config, server):
        config.return_value = Mock(logfile_path="path")
        argv = ["--quiet"]
        run_server(argv=argv)
        load_config.assert_called_once_with(None, {})
        setup_logging.assert_called_once_with(True, False, False, "path")
        server.assert_called_once()

    def test_run_server_verbose(self, load_config, setup_logging, config, server):
        config.return_value = Mock(logfile_path="path")
        argv = ["--verbose"]
        run_server(argv=argv)
        load_config.assert_called_once_with(None, {})
        setup_logging.assert_called_once_with(False, True, False, "path")
        server.assert_called_once()

    def test_run_server_debug(self, load_config, setup_logging, config, server):
        config.return_value = Mock(logfile_path="path")
        argv = ["--debug"]
        run_server(argv=argv)
        load_config.assert_called_once_with(None, {})
        setup_logging.assert_called_once_with(False, False, True, "path")
        server.assert_called_once()

    def test_run_server_config(self, load_config, setup_logging, config, server):
        config.return_value = Mock(logfile_path="path")
        argv = ["--config", "/path/to/config"]
        run_server(argv=argv)
        load_config.assert_called_once_with("/path/to/config", {})
        setup_logging.assert_called_once_with(False, False, False, "path")
        server.assert_called_once()

    def test_run_server_logfile(self, load_config, setup_logging, config, server):
        config.return_value = Mock(logfile_path="path")
        argv = ["--logfile", "/path/to/log"]
        run_server(argv=argv)
        load_config.assert_called_once_with(None, {"logfile_path": "/path/to/log"})
        setup_logging.assert_called_once_with(False, False, False, "path")
        server.assert_called_once()

    def test_run_server_override_single(self, load_config, setup_logging, config, server):
        config.return_value = Mock(logfile_path="path")
        argv = ["--override", "one:ONE"]
        run_server(argv=argv)
        load_config.assert_called_once_with(None, {"one": "ONE"})
        setup_logging.assert_called_once_with(False, False, False, "path")
        server.assert_called_once()

    def test_run_server_override_multiple(self, load_config, setup_logging, config, server):
        config.return_value = Mock(logfile_path="path")
        argv = ["--override", "one:ONE", "--logfile", "/path/to/log", "--override", "two:TWO"]
        run_server(argv=argv)
        load_config.assert_called_once_with(None, {"one": "ONE", "two": "TWO", "logfile_path": "/path/to/log"})
        setup_logging.assert_called_once_with(False, False, False, "path")
        server.assert_called_once()
