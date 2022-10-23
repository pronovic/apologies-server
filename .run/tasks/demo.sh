# vim: set ft=bash sw=3 ts=3 expandtab:

help_demo() {
   echo "- run demo: Run the demo client (requires running server)"
}

task_demo() {
   cat << EOF > "$WORKING_DIR/demo.py"
from apologiesserver.cli import cli
cli("run_demo")
EOF

   run_command latestcode
   poetry_run python "$WORKING_DIR/demo.py" "$@"
}

