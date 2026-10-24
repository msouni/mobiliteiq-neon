#!/usr/bin/env bash
# À exécuter depuis le dépôt de travail avec l'artefact de la CI réussie.
set -euo pipefail
package=$(realpath "${1:?Usage: bash scripts/deploy.sh CHEMIN/mobiliteiq-release.tar VERSION}")
version=${2:?Indiquer une nouvelle version, par exemple v1.0.0}
[[ "$version" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo 'Version attendue : v1.0.0'; exit 1; }
project=$(pwd)
[ -f "$project/.env" ] || { echo 'Exécuter depuis le dossier du projet contenant .env'; exit 1; }
target="$HOME/mobiliteiq-releases/$version"
[ ! -e "$target" ] || { echo 'Cette version existe déjà; choisir un nouveau tag'; exit 1; }
mkdir -p "$target"
tar -xf "$package" -C "$target"
for d in data logs models exports; do
  mkdir -p "$project/$d"
  ln -s "$project/$d" "$target/$d"
done
ln -s "$project/.env" "$target/.env"
cd "$target"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
# Les tests utilisent exclusivement mobiliteiq_test. Ils précèdent la promotion.
.venv/bin/python -c 'from mobiliteiq.__main__ import settings; settings(); import os,pytest; os.environ["RUN_PG_TESTS"]="1"; raise SystemExit(pytest.main(["-q"]))'
.venv/bin/python -m mobiliteiq init-db
ln -s "$target" "$HOME/mobiliteiq-current.new"
mv -Tf "$HOME/mobiliteiq-current.new" "$HOME/mobiliteiq-current"
printf '%s %s\n' "$(date -Is)" "$version" >> "$project/logs/deploy.log"
echo "Version promue : $version"
