# vim: set ft=bash sw=3 ts=3 expandtab:

help_server() {
   echo "- run server: Start the websockets server"
}

task_server() {
   run_command latestcode
   poetry_run apologies-server "$@"
}

