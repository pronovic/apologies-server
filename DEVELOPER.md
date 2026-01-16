# Developer Notes

## Packaging and Dependencies

This project uses [UV](https://docs.astral.sh/uv/) to manage Python packaging and dependencies.  Most day-to-day tasks (such as running unit tests from the command line) are orchestrated through UV.

A coding standard is enforced using [Ruff](https://docs.astral.sh/ruff/).  Python 3 type hinting is validated using [MyPy](https://pypi.org/project/mypy/).

## Pre-Commit Hooks

We rely on pre-commit hooks to ensure that the code is properly-formatted,
clean, and type-safe when it's checked in.  The `run install` step described
below installs the project pre-commit hooks into your repository.  These hooks
are configured in [`.pre-commit-config.yaml`](.pre-commit-config.yaml).

If necessary, you can temporarily disable a hook using Git's `--no-verify`
switch.  However, keep in mind that the CI build on GitHub enforces these
checks, so the build will fail.

## Line Endings

The [`.gitattributes`](.gitattributes) file controls line endings for the files
in this repository.  Instead of relying on automatic behavior, the
`.gitattributes` file forces most files to have UNIX line endings.

## Prerequisites

All prerequisites are managed by UV.  All you need to do install UV itself,
following the [instructions](https://docs.astral.sh/uv/getting-started/installation/).
UV will take care of installing the required Python interpreter and all of the
dependencies.

> **Note:** The development environment (the `run` script, etc.) expects a bash
> shell to be available.  On Windows, it works fine with the standard Git Bash.

## Developer Tasks

The [`run`](run) script provides shortcuts for common developer tasks:

```
$ ./run --help

------------------------------------
Shortcuts for common developer tasks
------------------------------------

Basic tasks:

- run install: Install the Python virtualenv and pre-commit hooks
- run update: Update all dependencies, or a subset passed as arguments
- run outdated: Find top-level dependencies with outdated constraints
- run rebuild: Rebuild all dependencies flagged as no-binary-package
- run format: Run the code formatters
- run checks: Run the code checkers
- run build: Build artifacts in the dist/ directory
- run test: Run the unit tests
- run test -c: Run the unit tests with coverage
- run test -ch: Run the unit tests with coverage and open the HTML report
- run suite: Run the complete test suite, as for the GitHub Actions CI build
- run suite -f: Run a faster version of the test suite, omitting some steps
- run clean: Clean the source tree

Additional tasks:

- run docs: Build the Sphinx documentation for readthedocs.io
- run docs -o: Build the Sphinx documentation and open in a browser
- run release: Tag and release the code, triggering GHA to publish artifacts

The Python interpreter version is controlled by the .python-version file.  To
test with a different version of Python temporarily, set $UV_PYTHON in your
shell, and execute 'run install'.  Make sure to unset and reinstall when done.
```

## Running the Server

To run the server from the codebase for local testing, use the `run server`
command.  This is equivalent to the installed `apologies-server` script.

```
$ ./run server --help
usage: apologies-server [-h] [--quiet] [--verbose] [--debug] [--config CONFIG]
              [--logfile LOGFILE] [--override OVERRIDE]

Start the apologies server and let it run forever.

optional arguments:
  -h, --help           show this help message and exit
  --quiet              decrease log verbosity from INFO to ERROR
  --verbose            increase log verbosity from INFO to DEBUG
  --debug              like --verbose but also include websockets logs
  --config CONFIG      path to configuration on disk
  --logfile LOGFILE    path to logfile on disk (default is stdout)
  --override OVERRIDE  override a config parameter as "param:value"

By default, the server writes logs to stdout. If you prefer, you can specify
the path to a logfile, and logs will be written there instead. The default
configuration file is "/Users/kpronovici/.apologiesrc". If the default
configuration file is not found, default values will be set. If you override
the default config file, it must exist. You may override any individual config
parameter with "--override param:value".
```

The simplest way to start the server is with no arguments:

```
$ ./run server
2020-06-10 14:31:39,831Z --> [INFO   ] Apologies server started
2020-06-10 14:31:39,832Z --> [INFO   ] Configuration: {
  "logfile_path": null,
  "server_host": "localhost",
  "server_port": 8080,
  "close_timeout_sec": 10,
  "websocket_limit": 1000,
  "total_game_limit": 1000,
  "in_progress_game_limit": 25,
  "registered_player_limit": 100,
  "websocket_idle_thresh_min": 2,
  "websocket_inactive_thresh_min": 5,
  "player_idle_thresh_min": 15,
  "player_inactive_thresh_min": 30,
  "game_idle_thresh_min": 10,
  "game_inactive_thresh_min": 20,
  "game_retention_thresh_min": 2880,
  "idle_websocket_check_period_sec": 120,
  "idle_websocket_check_delay_sec": 300,
  "idle_player_check_period_sec": 120,
  "idle_player_check_delay_sec": 300,
  "idle_game_check_period_sec": 120,
  "idle_game_check_delay_sec": 300,
  "obsolete_game_check_period_sec": 300,
  "obsolete_game_check_delay_sec": 300
}
2020-06-10 14:31:39,832Z --> [INFO   ] Adding signal handlers...
2020-06-10 14:31:39,832Z --> [INFO   ] Scheduling tasks...
2020-06-10 14:31:39,832Z --> [INFO   ] Completed starting websocket server
```

The server displays its configuration when it boots.  You can override any of
this configuration using the switches on the `run server` command.

## Running the Demo

While this is primarily a websockets server, it includes a quick'n'dirty demo
that plays a game as a websockets client, to demonstrate the protocol and the
websockets client code.

```
$ ./run demo --help
usage: demo [-h] [--quiet] [--verbose] [--debug] [--logfile LOGFILE]
            [--host HOST] [--port PORT]

Start the apologies server demo client.

optional arguments:
  -h, --help         show this help message and exit
  --quiet            decrease log verbosity from INFO to ERROR
  --verbose          increase log verbosity from INFO to DEBUG
  --debug            like --verbose but also include websockets logs
  --logfile LOGFILE  path to logfile on disk (default is stdout)
  --host HOST        host where the server is running
  --port PORT        port where the server is running on the host

The client requires that you already have the server running. By default, the
client writes logs to stdout. If you prefer, you can specify the path to a
logfile, and logs will be written there instead.
```

To run the demo, you must also have a server running elsewhere.  Your
simplest option is to start the server in one window:

```
./run server
```

and the demo in another window:

```
./run demo
```

The demo registers a "human" player, starts a 4-player game (getting 3
programmatic players as opponents), and then runs through the entire game until
it completes.  To simulate "human" game play, each time it is the human
player's turn, a move is chosen randomly.  The programmatic opponents are
played as usual by the server using its reward-based play choice algorithm.

The demo assumes it can register a player with handle `leela`.  You should be
able to run the demo multiple times in a row against the server without any
problems, because it cleans up after itself properly.  However, if you have
been making changes to the demo - or if it crashed or was interrupted - and the
`leela` handle is still registered, the demo will fail to run.

## Integration with PyCharm

Currently, I use [PyCharm Community Edition](https://www.jetbrains.com/pycharm/download) as 
my day-to-day IDE.  By integrating the `run` script to execute MyPy and Ruff,
most everything important that can be done from a shell environment can also be
done right in PyCharm.

PyCharm offers a good developer experience.  However, the underlying configuration
on disk mixes together project policy (i.e. preferences about which test runner to
use) with system-specific settings (such as the name and version of the active Python 
interpreter). This makes it impossible to commit complete PyCharm configuration 
to the Git repository.  Instead, the repository contains partial configuration, and 
there are instructions below about how to manually configure the remaining items.

### Prerequisites

Before going any further, make sure sure that you have installed UV and have a
working bash shell.  Then, run the suite and confirm that everything is working:

```
./run suite
```

### Open the Project

Once you have a working shell development environment, **Open** (do not
**Import**) the `apologiesserver` directory in PyCharm, then follow the remaining
instructions below.  By using **Open**, the existing `.idea` directory will be
retained and all of the existing settings will be used.

### Interpreter

As a security precaution, PyCharm does not trust any virtual environment
installed within the repository, such as the UV `.venv` directory. In the
status bar on the bottom right, PyCharm will report _No interpreter_.  Click
on this error and select **Add Interpreter**.  In the resulting dialog, click
**Ok** to accept the selected environment, which should be the UV virtual
environment.

### Project Structure

Go to the PyCharm settings and find the `apologiesserver` project.  Under
**Project Structure**, mark `src` as a source folder and `tests` as a test
folder.  In the **Exclude Files** box, enter the following:

```
LICENSE;NOTICE;PyPI.md;build;dist;docs/_build;out;uv.lock;run;.coverage;.coverage.lcov;.coveragerc;.gitattributes;.github;.gitignore;.htmlcov;.idea;.mypy_cache;.pre-commit-config.yaml;.pytest_cache;.readthedocs.yaml;.ruff_cache;.run;.tabignore;.venv
```

When you're done, click **Ok**.  Then, go to the gear icon in the project panel 
and uncheck **Show Excluded Files**.  This will hide the files and directories 
in the list above.

### Tool Preferences

In the PyCharm settings, go to **Editor > Inspections** and be sure that the
**Project Default** profile is selected.

Unit tests are written using [Pytest](https://docs.pytest.org/en/latest/),
and API documentation is written using [Google Style Python Docstring](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html).  However,
neither of these is the default in PyCharm.  In the PyCharm settings, go to
**Tools > Python Integrated Tools**.  Under **Testing > Default test runner**,
select _pytest_.  Under **Docstrings > Docstring format**, select _Google_.

### Running Unit Tests

Right click on the `src/tests` folder in the project explorer and choose **Run
'pytest in tests'**.  Make sure that all of the tests pass.  If you see a slightly
different option (i.e. for "Unittest" instead of "pytest") then you probably 
skipped the preferences setup discussed above.  You may need to remove the
run configuration before PyCharm will find the right test suite.

### External Tools

Optionally, you might want to set up external tools for some of common
developer tasks: code reformatting and the Ruff and MyPy checks.  One nice
advantage of doing this is that you can configure an output filter, which makes
the Ruff linter and MyPy errors clickable.  To set up external tools, go to
PyCharm settings and find **Tools > External Tools**.  Add the tools as
described below.

#### Linux or MacOS

On Linux or MacOS, you can set up the external tools to invoke the `run` script
directly.

##### Shell Environment

For this to work, it's important that tools like `uv` are on the system
path used by PyCharm.  On Linux, depending on how you start PyCharm, your
normal shell environment may or may not be inherited.  For instance, I had to
adjust the target of my LXDE desktop shortcut to be the script below, which
sources my profile before running the `pycharm.sh` shell script:

```sh
#!/bin/bash
source ~/.bash_profile
/opt/local/lib/pycharm/pycharm-community-2020.3.2/bin/pycharm.sh
```

##### Format Code

|Field|Value|
|-----|-----|
|Name|`Format Code`|
|Description|`Run the Ruff code formatter`|
|Group|`Developer Tools`|
|Program|`$ProjectFileDir$/run`|
|Arguments|`format`|
|Working directory|`$ProjectFileDir$`|
|Synchronize files after execution|_Checked_|
|Open console for tool outout|_Checked_|
|Make console active on message in stdout|_Unchecked_|
|Make console active on message in stderr|_Unchecked_|
|Output filters|_Empty_|

##### Run MyPy Checks

|Field|Value|
|-----|-----|
|Name|`Run MyPy Checks`|
|Description|`Run the MyPy code checks`|
|Group|`Developer Tools`|
|Program|`$ProjectFileDir$/run`|
|Arguments|`mypy`|
|Working directory|`$ProjectFileDir$`|
|Synchronize files after execution|_Unchecked_|
|Open console for tool outout|_Checked_|
|Make console active on message in stdout|_Checked_|
|Make console active on message in stderr|_Checked_|
|Output filters|`$FILE_PATH$:$LINE$`|

##### Run Ruff Linter

|Field|Value|
|-----|-----|
|Name|`Run Ruff Linter`|
|Description|`Run the Ruff linter code checks`|
|Group|`Developer Tools`|
|Program|`$ProjectFileDir$/run`|
|Arguments|`ruff`|
|Working directory|`$ProjectFileDir$`|
|Synchronize files after execution|_Unchecked_|
|Open console for tool outout|_Checked_|
|Make console active on message in stdout|_Checked_|
|Make console active on message in stderr|_Checked_|
|Output filters|`$FILE_PATH$:$LINE$`|

#### Windows

On Windows, PyCharm has problems invoking the `run` script.  The trick is to
invoke the Bash interpreter and tell it to invoke the `run` script.  The
examples below assume that you have installed Git Bash in its standard location
under `C:\Program Files\Git`.  If it is somewhere else on your system, just
change the path for `bash.exe`.

##### Format Code

|Field|Value|
|-----|-----|
|Name|`Format Code`|
|Description|`Run the Ruff code formatter`|
|Group|`Developer Tools`|
|Program|`powershell.exe`|
|Arguments|`& 'C:\Program Files\Git\bin\bash.exe' -l './run format' \| Out-String`|
|Working directory|`$ProjectFileDir$`|
|Synchronize files after execution|_Checked_|
|Open console for tool outout|_Checked_|
|Make console active on message in stdout|_Unchecked_|
|Make console active on message in stderr|_Unchecked_|
|Output filters|_Empty_|

##### Run MyPy Checks

|Field|Value|
|-----|-----|
|Name|`Run MyPy Checks`|
|Description|`Run the MyPy code checks`|
|Group|`Developer Tools`|
|Program|`powershell.exe`|
|Arguments|`& 'C:\Program Files\Git\bin\bash.exe' -l './run mypy' \| Out-String`|
|Working directory|`$ProjectFileDir$`|
|Synchronize files after execution|_Unchecked_|
|Open console for tool outout|_Checked_|
|Make console active on message in stdout|_Checked_|
|Make console active on message in stderr|_Checked_|
|Output filters|`$FILE_PATH$:$LINE$`|

##### Run Ruff Linter

|Field|Value|
|-----|-----|
|Name|`Run Ruff Linter`|
|Description|`Run the Ruff linter code checks`|
|Group|`Developer Tools`|
|Program|`powershell.exe`|
|Arguments|`& 'C:\Program Files\Git\bin\bash.exe' -l './run ruff' \| Out-String`|
|Working directory|`$ProjectFileDir$`|
|Synchronize files after execution|_Unchecked_|
|Open console for tool outout|_Checked_|
|Make console active on message in stdout|_Checked_|
|Make console active on message in stderr|_Checked_|
|Output filters|`$FILE_PATH$:$LINE$`|

## Release Process

### Documentation

Documentation at [Read the Docs](https://apologiesserver.readthedocs.io/en/stable/)
is generated via a GitHub hook.  So, there is no formal release process for the
documentation.

### Code

Code is released to [PyPI](https://pypi.org/project/apologiesserver/).  There is a
partially-automated process to publish a new release.

> **Note:** In order to publish code, you must must have push permissions to the
> GitHub repo.

Ensure that you are on the `main` branch.  Releases must always be done from
`main`.

Ensure that the `Changelog` is up-to-date and reflects all of the changes that
will be published.  The top line must show your version as unreleased:

```
Version 0.1.0      unreleased
```

Run the release command:

```
./run release 0.1.0
```

This command updates `NOTICE` and `Changelog` to reflect the release version
and release date, commits those changes, tags the code, and pushes to GitHub.
The new tag triggers a GitHub Actions build that runs the test suite, generates
the artifacts, publishes to PyPI, and finally creates a release from the tag.

> **Note:** This process relies on a PyPI API token with upload permissions for
> the project.  This token is stored in a GitHub Actions secret called
> `PYPI_TOKEN`.
