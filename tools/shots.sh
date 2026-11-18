#!/bin/sh
# tools/shots.sh - render the game's own screens to PNG on a machine with no GPU.
#
# The CI recipe from release.yml ("Play on the clean pack"), lifted out of CI so a session can
# run it on demand instead of waiting for a pushed branch. Clean pack only: no Maxis file ever
# reaches the frame, so this is the right place to check Track A's clean-pack screens. (The
# original look is the same command without --clean, below; the original files are on this box.)
#
#   GODOT=~/work/godot-bin/Godot_v4.7.2-stable_mono_linux_x86_64/Godot_v4.7.2-stable_mono_linux.x86_64 sh tools/shots.sh   # all
#   GODOT=... sh tools/shots.sh game yard                                            # some
#
# Needs: that Godot mono build, the .NET 10 SDK (net10.0 since #112), xvfb, and mesa's software GL (libgl1-mesa-dri).
# Output: remake/build/shots/<name>.png + .log. Exits non-zero on a missing PNG or a crash.

set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
: "${GODOT:?set GODOT to the Godot 4.6 mono linux binary}"
out=$repo/remake/build/shots
mkdir -p "$out"

screens_title='--title --frames=120'
screens_game='--seed=1234 --ticks=600'
screens_yard='--seed=1234 --ticks=300 --yard'
screens_history='--seed=1234 --ticks=600 --history'
screens_antipedia='--antipedia'
screens_tutorial='--tutorial=5'

[ -f "$repo/remake/game/assets/clean/clean_pack.zip" ] || python3 "$repo/tools/clean_pack/build.py"
"$GODOT" --headless --path "$repo/remake/game" --import >/dev/null
dotnet build "$repo/remake/game/OpenSimAnt.csproj" >/dev/null

failed=
[ $# -gt 0 ] || set -- title game yard history antipedia tutorial
for name in "$@"; do
  eval "sel=\${screens_$name:-}"
  [ -n "$sel" ] || { echo "unknown screen '$name'"; exit 2; }
  rm -f "$out/$name.png"
  # A real GL context is the whole point: --headless gives a dummy renderer and a blank image.
  xvfb-run -a -s "-screen 0 1280x1024x24" "$GODOT" --path "$repo/remake/game" \
    --rendering-driver opengl3 --audio-driver Dummy -- \
    --clean $sel "--screenshot=$out/$name.png" >"$out/$name.log" 2>&1 || true
  if [ ! -s "$out/$name.png" ]; then
    echo "$name: no png"; failed="$failed $name"; continue
  fi
  if grep -Eq "Unhandled exception|[A-Za-z.]+Exception:| is missing" "$out/$name.log"; then
    echo "$name: the game failed (see $out/$name.log)"; failed="$failed $name"; continue
  fi
  echo "$name: $out/$name.png"
done

[ -z "$failed" ] || { echo "failed:$failed"; exit 1; }
echo "ok - $out"
