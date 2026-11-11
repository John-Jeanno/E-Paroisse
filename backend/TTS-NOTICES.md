# Voix française intégrée

Le service audio utilise Piper TTS (`piper-tts` 1.8.0), distribué sous licence
GNU GPL version 3 ou ultérieure : https://github.com/OHF-Voice/piper1-gpl

Le modèle français `fr_FR-siwis-medium` est fourni par le dépôt Piper Voices.
Sa fiche de modèle indique la langue `fr_FR`, la qualité « medium » et un
entraînement sur le corpus SIWIS, sous licence CC BY 4.0 :
https://huggingface.co/rhasspy/piper-voices/tree/v1.0.0/fr/fr_FR/siwis/medium

Le modèle et sa configuration sont téléchargés pendant la construction de
l’image backend et le SHA-256 du modèle est vérifié. Le modèle n’est pas inclus
dans les sources de l’application.
