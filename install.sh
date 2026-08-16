#!/usr/bin/env bash
# install.sh — rend les 9 outils appelables par leur nom, de partout.
#
# POURQUOI DES LIENS ET PAS UNE COPIE : une skill ne devrait jamais connaître
# le chemin d'un dépôt. Elle appelle `jamai-midi.py`, point. Si ce dépôt
# déménage demain, on relance ce script et rien d'autre ne bouge.
# C'est déjà le motif de `jamai-publish-melody` sur cette machine.
#
#   ./install.sh            installe dans ~/.local/bin
#   ./install.sh --check    vérifie sans rien écrire
#   ./install.sh --uninstall  retire les liens posés par ce script
set -euo pipefail

RACINE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CIBLE="${JAMAI_BIN:-$HOME/.local/bin}"
OUTILS=(ecoute/jamai-midi.py ecoute/jamai-chords.py ecoute/jamai-chords-audio.py
        ecoute/jamai-measure.py rendu/jamai-tab.py rendu/jamai-score-video.py
        rendu/jamai-defile.py atelier/jamai-unread.py atelier/jamai-related.py
        atelier/jamai-voir-fork
        diffusion/jamai-cast-visual diffusion/jamai-say-kitchen)

# jamai-cast-visual sert ses pages depuis ce dossier et y lit la géométrie de
# la télé. Le chemin est en dur dans le script : on lie donc la feuille de
# style plutôt que de la copier, pour qu'elle reste éditable dans le dépôt.
WEB="$HOME/.local/share/jamai-cast/web"

mode="${1:-install}"
mkdir -p "$CIBLE"
n=0
for rel in "${OUTILS[@]}"; do
  src="$RACINE/$rel"; nom="$(basename "$rel")"; dst="$CIBLE/$nom"
  case "$mode" in
    --check)
      if [ -e "$dst" ] && [ "$(readlink -f "$dst")" = "$(readlink -f "$src")" ]
        then echo "✓ $nom"; n=$((n+1))
        else echo "✗ $nom — absent ou pointe ailleurs"; fi ;;
    --uninstall)
      if [ -L "$dst" ] && [ "$(readlink -f "$dst")" = "$(readlink -f "$src")" ]
        then rm "$dst"; echo "retiré : $nom"; n=$((n+1)); fi ;;
    *)
      [ -x "$src" ] || chmod +x "$src"
      ln -sfn "$src" "$dst"; echo "→ $nom"; n=$((n+1)) ;;
  esac
done

socle="$RACINE/diffusion/web/_socle.css"
case "$mode" in
  --check)
    [ "$(readlink -f "$WEB/_socle.css" 2>/dev/null)" = "$(readlink -f "$socle")" ] \
      && echo "✓ _socle.css" || echo "✗ _socle.css — absent ou pointe ailleurs" ;;
  --uninstall)
    [ -L "$WEB/_socle.css" ] && rm "$WEB/_socle.css" && echo "retiré : _socle.css" ;;
  *)
    mkdir -p "$WEB"; ln -sfn "$socle" "$WEB/_socle.css"; echo "→ _socle.css ($WEB)" ;;
esac

echo "$n / ${#OUTILS[@]} — $CIBLE"
case ":$PATH:" in
  *":$CIBLE:"*) ;;
  *) echo "⚠ $CIBLE n'est pas dans le PATH — ajoute-le à ton shell." ;;
esac
