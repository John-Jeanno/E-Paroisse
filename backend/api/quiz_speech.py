import hashlib
import logging
import os
import tempfile
import threading
import wave
from functools import lru_cache
from pathlib import Path

from django.conf import settings


LOGGER = logging.getLogger(__name__)
VOICE_NAME = 'fr_FR-siwis-medium'
VOICE_MODEL = settings.BASE_DIR / 'models' / f'{VOICE_NAME}.onnx'
VOICE_CONFIG = settings.BASE_DIR / 'models' / f'{VOICE_NAME}.onnx.json'
CACHE_DIRECTORY = settings.PRIVATE_DOCUMENT_ROOT / 'quiz-audio' / VOICE_NAME
MAX_CACHE_BYTES = 256 * 1024 * 1024
_SYNTHESIS_LOCK = threading.Lock()


class SpeechUnavailableError(Exception):
    pass


@lru_cache(maxsize=1)
def _load_voice():
    if not VOICE_MODEL.is_file() or not VOICE_CONFIG.is_file():
        raise SpeechUnavailableError('La voix française intégrée est indisponible.')

    try:
        from piper import PiperVoice

        return PiperVoice.load(str(VOICE_MODEL))
    except (ImportError, OSError, RuntimeError) as error:
        LOGGER.exception('Unable to load the French quiz voice.')
        raise SpeechUnavailableError('La voix française intégrée n’a pas pu être chargée.') from error


def _trim_cache():
    files = sorted(
        CACHE_DIRECTORY.glob('*.wav'),
        key=lambda item: item.stat().st_mtime,
    )
    total_bytes = sum(item.stat().st_size for item in files)
    while total_bytes > MAX_CACHE_BYTES and files:
        old_file = files.pop(0)
        size = old_file.stat().st_size
        old_file.unlink(missing_ok=True)
        total_bytes -= size


def synthesize_quiz_audio(text):
    digest = hashlib.sha256(f'{VOICE_NAME}\0{text}'.encode('utf-8')).hexdigest()
    CACHE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    cached_audio = CACHE_DIRECTORY / f'{digest}.wav'
    if cached_audio.is_file():
        return cached_audio

    with _SYNTHESIS_LOCK:
        if cached_audio.is_file():
            return cached_audio

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=CACHE_DIRECTORY,
                prefix=f'.{digest}.',
                suffix='.wav',
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)

            with wave.open(str(temp_path), 'wb') as audio_file:
                _load_voice().synthesize_wav(text, audio_file)

            os.replace(temp_path, cached_audio)
            _trim_cache()
            return cached_audio
        except SpeechUnavailableError:
            if temp_path:
                temp_path.unlink(missing_ok=True)
            raise
        except (OSError, RuntimeError, ValueError):
            if temp_path:
                temp_path.unlink(missing_ok=True)
            LOGGER.exception('Unable to synthesize French quiz speech.')
            raise SpeechUnavailableError('La lecture audio française est momentanément indisponible.')
