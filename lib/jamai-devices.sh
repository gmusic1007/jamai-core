# jamai-devices.sh — find a Chromecast device by the name a person says. Sourced, never run.
#
#   jamai_device_resolve "<name>"   prints the device's exact name, or explains on stderr and
#                                   returns 1 when the name matches no device or several
#
# Order: the exact name (any case), then the one name that starts with it, then the one name
# that contains it. "Bathroom" finds "Bathroom speaker"; "kitchen" matches "Kitchen Tv" and
# "kitchen speaker" and is refused with both names. catt itself wants the exact name, and
# answered "Specified device not found" to "Bathroom".
#
# Names come from `catt scan`, cached in $JAMAI_CAST_STATE/appareils.txt (the cache jamai-cast
# already keeps). A name the cache does not know triggers one fresh scan before refusing.

_jamai_dev_cache() { printf '%s/appareils.txt' "${JAMAI_CAST_STATE:-$HOME/.local/state/jamai-cast}"; }

_jamai_dev_scan() {
  local cache; cache="$(_jamai_dev_cache)"
  mkdir -p "$(dirname "$cache")" || return 1
  printf '… scan du réseau (mis en cache dans %s)\n' "$cache" >&2
  if timeout 60 "${CATT:-$HOME/.local/bin/catt}" scan > "$cache.tmp" 2>&1; then mv "$cache.tmp" "$cache"
  else rm -f "$cache.tmp"; return 1; fi
}

_jamai_dev_names() { awk -F' - ' 'NF >= 3 { print $2 }' "$(_jamai_dev_cache)" 2>/dev/null | sort -u; }

_jamai_dev_match() {   # _jamai_dev_match NAME exact|prefix|inside → the matching names, one per line
  local want="${1,,}" rule="$2" name low
  while IFS= read -r name; do
    low="${name,,}"
    case "$rule" in
      exact)  [ "$low" = "$want" ] && printf '%s\n' "$name" ;;
      prefix) [[ "$low" == "$want"* ]] && printf '%s\n' "$name" ;;
      inside) [[ "$low" == *"$want"* ]] && printf '%s\n' "$name" ;;
    esac
  done < <(_jamai_dev_names)
  return 0
}

_jamai_dev_list() { _jamai_dev_names | paste -sd'|' - | sed 's/|/, /g'; }

jamai_device_resolve() {
  local want="$1" pass rule hits count
  [ -n "$want" ] || { echo "✗ aucun nom d'appareil" >&2; return 1; }
  if [ ! -s "$(_jamai_dev_cache)" ]; then
    _jamai_dev_scan || { echo "✗ le scan des appareils a échoué (catt scan)" >&2; return 1; }
  fi
  for pass in cache fresh; do
    for rule in exact prefix inside; do
      hits="$(_jamai_dev_match "$want" "$rule")"
      count="$(printf '%s' "$hits" | grep -c .)"
      if [ "$count" -eq 1 ]; then printf '%s\n' "$hits"; return 0; fi
      if [ "$count" -gt 1 ]; then
        printf '✗ « %s » désigne plusieurs appareils : %s. Donne le nom complet.\n' \
          "$want" "$(printf '%s\n' "$hits" | paste -sd'|' - | sed 's/|/, /g')" >&2
        return 1
      fi
    done
    [ "$pass" = cache ] || break
    _jamai_dev_scan || break
  done
  printf '✗ aucun appareil ne s'\''appelle « %s ». Vus : %s\n' "$want" "$(_jamai_dev_list)" >&2
  return 1
}
