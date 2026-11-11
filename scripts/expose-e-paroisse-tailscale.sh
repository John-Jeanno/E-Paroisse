#!/bin/sh
set -eu

if ! command -v tailscale >/dev/null 2>&1; then
    printf '%s\n' "Tailscale n'est pas installé ou la commande tailscale est absente du PATH."
    printf '%s\n' "Installez Tailscale sur le Mac, connectez-le au même compte que l'iPhone, puis relancez cette tâche."
    exit 1
fi

if ! curl --fail --silent --output /dev/null http://127.0.0.1:8083/; then
    printf '%s\n' "Le site web n'est pas démarré sur le port 8083. Lancez d'abord la tâche E-Paroisse Web."
    exit 1
fi

if ! curl --fail --silent --output /dev/null http://127.0.0.1:8000/api/; then
    printf '%s\n' "L'API Django n'est pas démarrée sur le port 8000. Lancez d'abord la tâche E-Paroisse API Django."
    exit 1
fi

tailscale serve --bg --https=443 127.0.0.1:8083
tailscale serve --bg --https=443 --set-path=/api http://127.0.0.1:8000/api
tailscale serve status
