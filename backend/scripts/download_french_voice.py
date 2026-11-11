import hashlib
import urllib.request
from pathlib import Path


VOICE_NAME = 'fr_FR-siwis-medium'
VOICE_BASE_URL = (
    'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/'
    'fr/fr_FR/siwis/medium'
)
VOICE_MODEL_SHA256 = '641d1ab097da2b81128c076810edb052b385decc8be3381814802a64a73baf99'
DESTINATION = Path('/app/models')


def download(filename, destination):
    url = f'{VOICE_BASE_URL}/{filename}'
    urllib.request.urlretrieve(url, destination)


def main():
    DESTINATION.mkdir(parents=True, exist_ok=True)
    model_path = DESTINATION / f'{VOICE_NAME}.onnx'
    config_path = DESTINATION / f'{VOICE_NAME}.onnx.json'
    card_path = DESTINATION / 'fr_FR-siwis-MODEL_CARD'

    if not model_path.exists():
        download(model_path.name, model_path)
    digest = hashlib.sha256(model_path.read_bytes()).hexdigest()
    if digest != VOICE_MODEL_SHA256:
        model_path.unlink(missing_ok=True)
        raise RuntimeError(f'Unexpected SHA-256 for the French Piper model: {digest}')

    if not config_path.exists():
        download(config_path.name, config_path)
    if not card_path.exists():
        download('MODEL_CARD', card_path)


if __name__ == '__main__':
    main()
