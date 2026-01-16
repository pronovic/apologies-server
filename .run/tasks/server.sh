# vim: set ft=bash sw=3 ts=3 expandtab:
# runscript: customized=true

help_server() {
   echo "- run server: Start the websockets server"
}

task_server() {
   run_command uvrun apologies-server "$@"
}
