#!/bin/bash
# Invoked only after the native app displays the dependency plan and obtains consent.
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
app_root="${1:?application root}"
version="${2:?version}"
state="${3:?installer status path}"
exec > >(tee -a "${state%/*}/install-${version}.log") 2>&1
trap 'code=$?; if [[ $code -ne 0 ]]; then printf "{\"status\":\"failed\",\"exit_code\":%s}\n" "$code" > "$state"; fi' EXIT
printf '{"status":"installing"}\n' > "$state"
if ! xcode-select -p >/dev/null 2>&1; then
    xcode-select --install || true
    printf '\nComplete the Apple developer tools dialog, then return here.\n'
    read -r -p 'Press Enter after installation completes. ' _
    xcode-select -p >/dev/null
fi
if ! command -v cmake >/dev/null || ! command -v pkg-config >/dev/null; then
    if ! command -v brew >/dev/null; then
        installer="${state%/*}/install-homebrew.sh"
        curl -fL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh -o "$installer"
        /bin/bash "$installer"
    fi
    if [[ -x /opt/homebrew/bin/brew ]]; then brew_bin=/opt/homebrew/bin/brew; else brew_bin=/usr/local/bin/brew; fi
    "$brew_bin" install cmake pkg-config
fi
cd "$app_root"
/usr/bin/python3 scripts/verify-installation.py
scripts/setup --prepare-simulator
/usr/bin/python3 - "$version" <<'PY'
import json,sys,time
from pathlib import Path
Path('.install-ready.json').write_text(json.dumps({'version':sys.argv[1],'ready':True,'completed_at':time.time()})+'\n')
PY
printf '{"status":"complete"}\n' > "$state"
printf '\nINSTALLATION COMPLETE. Return to Microduck V7RC.\n'
