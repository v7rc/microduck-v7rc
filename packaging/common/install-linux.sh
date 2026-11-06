#!/bin/bash
# Used by the Windows GUI after consent, or interactively by a Linux user.
set -euo pipefail
payload="${1:?payload zip required}"
target="${2:?versioned target directory required}"
version="${3:?version required}"
approved="${4:-}"
packages=(git curl python3 build-essential cmake pkg-config libssl-dev libudev-dev libasound2-dev libgl1 libegl1 libgl1-mesa-dri libglfw3 unzip)
missing=()
for package in "${packages[@]}"; do
    dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -qx 'install ok installed' || missing+=("$package")
done
printf 'System packages needed: %s\n' "${missing[*]:-(none)}"
printf 'Downloads: pinned Microduck upstreams, uv, Rust, Python and locked dependencies.\nTarget: %s\n' "$target"
if [[ "$approved" != --approved ]]; then
    read -r -p 'Install these packages and downloads? [y/N] ' answer
    [[ "$answer" == y || "$answer" == Y ]] || exit 2
fi
[[ $(id -u) -ne 0 ]] || { echo 'Initialize Ubuntu with a normal Linux user before installing.' >&2; exit 3; }
if ((${#missing[@]})); then
    sudo apt-get update
    sudo apt-get install -y --no-install-recommends "${missing[@]}"
fi
if [[ -e "$target/.installer-source.json" ]]; then
    python3 - "$target/.installer-source.json" "$version" <<'PY'
import json,sys
if json.load(open(sys.argv[1]))['version']!=sys.argv[2]:
 raise SystemExit('Existing installation version differs; choose a new version directory')
PY
elif [[ -e "$target" ]]; then
    echo 'Target exists without installer ownership; refusing to overwrite.' >&2; exit 4
else
    mkdir -p "$target"
    unzip -q "$payload" -d "$target"
fi
cd "$target"
python3 - "$version" <<'PYCODE'
import json,sys
from pathlib import Path
Path('.install-ready.json').write_text(json.dumps({'version':sys.argv[1],'ready':False})+'\n')
PYCODE
python3 scripts/verify-installation.py
scripts/setup --prepare-simulator
python3 - "$version" <<'PY'
import json,sys,time
from pathlib import Path
Path('.install-ready.json').write_text(json.dumps({'version':sys.argv[1],'ready':True,'completed_at':time.time()})+'\n')
PY
printf '\nINSTALLATION COMPLETE\n'
