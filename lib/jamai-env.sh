# jamai-env.sh — load the jamai settings into the environment. Sourced, never run.
#
# Order, first match wins: the environment, jamai.env, secrets.env, the default in `settings`.
# It prints nothing, is safe under `set -u` and `set -e`, and may be sourced twice.
#
#   . "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../lib/jamai-env.sh"

_jamai_lib="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
_jamai_cfg="${JAMAI_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/jamai}"

for _jamai_f in "$_jamai_cfg/jamai.env" "$_jamai_cfg/secrets.env"; do
  [ -r "$_jamai_f" ] || continue
  while IFS= read -r _jamai_l || [ -n "$_jamai_l" ]; do
    case "$_jamai_l" in ''|'#'*) continue ;; esac
    _jamai_k="${_jamai_l%%=*}"; _jamai_v="${_jamai_l#*=}"
    case "$_jamai_k" in ''|*[!A-Z0-9_]*) continue ;; esac
    if [ -z "${!_jamai_k+x}" ]; then export "$_jamai_k=$_jamai_v"; fi
  done < "$_jamai_f"
done

if [ -r "$_jamai_lib/../settings" ]; then
  while IFS='|' read -r _jamai_k _jamai_kind _jamai_v _jamai_l || [ -n "$_jamai_k" ]; do
    _jamai_k="${_jamai_k//[[:space:]]/}"; _jamai_kind="${_jamai_kind//[[:space:]]/}"
    case "$_jamai_k" in ''|'#'*|*[!A-Z0-9_]*) continue ;; esac
    case "$_jamai_kind" in secret|auto) continue ;; esac
    _jamai_v="${_jamai_v#"${_jamai_v%%[![:space:]]*}"}"; _jamai_v="${_jamai_v%"${_jamai_v##*[![:space:]]}"}"
    [ -n "$_jamai_v" ] || continue
    case "$_jamai_v" in '~/'*) _jamai_v="$HOME/${_jamai_v#\~/}" ;; esac
    if [ -z "${!_jamai_k+x}" ]; then export "$_jamai_k=$_jamai_v"; fi
  done < "$_jamai_lib/../settings"
fi

if [ -z "${JAMAI_CORE_ROOT+x}" ]; then export JAMAI_CORE_ROOT="$(cd "$_jamai_lib/.." && pwd)"; fi
unset _jamai_lib _jamai_cfg _jamai_f _jamai_l _jamai_k _jamai_v _jamai_kind
