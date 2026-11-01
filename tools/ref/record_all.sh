#!/bin/sh
# Record traces of every reference test for the C# remake (remake/build/traces/, git-ignored).
# Runs the tests in parallel; logs go next to the traces.
cd "$(dirname "$0")"
OUT=../../remake/build/traces
mkdir -p $OUT
run() {
    name=$1; shift
    TRACE_TAG=$TAG python record_traces.py "$@" > $OUT/$name.log 2>&1
    echo "$name: exit $? $(tail -1 $OUT/$name.log | cut -c1-80)"
}
TAG= run test_terrain test_terrain &
TAG= run test_pheromones test_pheromones &
TAG= run test_colony test_colony &
TAG= run test_movement test_movement &
TAG= run test_surface test_surface &
TAG= run test_nest test_nest &
TAG=red run test_nest_red test_nest --red &
TAG= run test_world test_world &
TAG= run test_yard test_yard &
TAG= run test_player test_player &
wait
TRACE_MAX=40000 TAG= run test_sim test_sim 3000 &
TRACE_MAX=40000 TAG=beef run test_sim_beef test_sim 3000 beef &
TRACE_MAX=40000 TAG=full run test_sim_full test_sim 2500 beef full &
TAG= run test_newgame test_newgame &
TAG=play run test_newgame_play test_newgame play &
TAG= run test_events test_events &
TAG= run test_game test_game &
TAG= run test_savefile test_savefile &
wait
TAG= run test_cheats test_cheats &
TAG= run test_tools test_tools &
TAG= run test_experimental test_experimental &
TAG= run test_debug test_debug &
TAG= run test_markers test_markers &
TAG= run test_balloons test_balloons &
TAG= run test_panels test_panels &
TAG= run test_commands test_commands &
TRACE_MAX=20000 TAG= run test_tutorial test_tutorial &
wait
echo ALL DONE
