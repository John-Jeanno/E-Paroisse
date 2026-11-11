import html
import json
from datetime import date
from html.parser import HTMLParser
from urllib.request import urlopen

from .models import LiturgicalReading


class _TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        text = ' '.join(data.split())
        if text:
            self.parts.append(text)

    def text(self):
        return html.unescape(' '.join(self.parts))


def _plain_text(content):
    parser = _TextParser()
    parser.feed(content or '')
    return parser.text()


def fetch_and_cache_reading(day):
    source = f'https://api.aelf.org/v1/messes/{day.isoformat()}/romain'
    with urlopen(source, timeout=20) as response:
        payload = json.load(response)

    informations = payload.get('informations', {})
    mass = next(
        (item for item in payload.get('messes', []) if item.get('nom') == 'Messe du jour'),
        payload.get('messes', [{}])[0],
    )
    sections = []
    for item in mass.get('lectures', []):
        kind = (item.get('type') or '').replace('_', ' ').title()
        title = (item.get('titre') or '').strip()
        content = _plain_text(item.get('contenu'))
        sections.append(f'{kind} : {title}\n{content}'.strip())

    reading, _ = LiturgicalReading.objects.update_or_create(
        date=day,
        defaults={
            'title': informations.get('ligne1') or 'Liturgie du jour',
            'content': '\n\n'.join(section for section in sections if section),
            'source': source,
        },
    )
    return reading