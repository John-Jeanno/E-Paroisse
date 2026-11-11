#!/usr/bin/env python3
import html
import json
import os
import sys
from calendar import monthrange
from datetime import date
from html.parser import HTMLParser
from urllib.request import urlopen

import django

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(ROOT)
BACKEND_ROOT = os.path.join(PROJECT_ROOT, 'backend')
sys.path.insert(0, BACKEND_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models import LiturgicalReading


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        text = ' '.join(data.split())
        if text:
            self.parts.append(text)

    def text(self):
        return html.unescape(' '.join(self.parts))


def plain_text(content):
    parser = TextParser()
    parser.feed(content or '')
    return parser.text()


def fetch_day(day):
    url = f'https://api.aelf.org/v1/messes/{day.isoformat()}/romain'
    with urlopen(url, timeout=20) as response:
        return json.load(response), url


def seed_august(year=2026):
    total = monthrange(year, 8)[1]
    for day_number in range(1, total + 1):
        day = date(year, 8, day_number)
        payload, source = fetch_day(day)
        informations = payload.get('informations', {})
        mass = next(
            (item for item in payload.get('messes', []) if item.get('nom') == 'Messe du jour'),
            payload.get('messes', [{}])[0],
        )
        readings = mass.get('lectures', [])
        title = informations.get('ligne1') or informations.get('jour_liturgique_nom') or 'Liturgie du jour'
        sections = [f"{item.get('type', '').replace('_', ' ').title()} : {(item.get('titre') or '').strip()}\n{plain_text(item.get('contenu'))}" for item in readings]
        content = '\n\n'.join(section for section in sections if section.strip())
        LiturgicalReading.objects.update_or_create(
            date=day,
            defaults={
                'title': title,
                'content': content,
                'source': source,
            },
        )
        print(f'Imported {day.isoformat()}')


if __name__ == '__main__':
    seed_august()