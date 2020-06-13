# -*- coding: utf-8 -*-
# vim: set ft=python ts=4 sw=4 expandtab:

from unittest.mock import patch

from apologiesserver.scripts import server


class TestServer:
    @patch("apologiesserver.scripts.cli")
    def test_server(self, cli):
        # this reflects how the script is invoked by the Poetry-generated stub
        server()
        cli.assert_called_once_with("run_server")
