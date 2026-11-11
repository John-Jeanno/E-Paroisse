import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class WhatsAppDeliveryError(Exception):
    pass


def is_whatsapp_otp_configured():
    return all((
        settings.WHATSAPP_ACCESS_TOKEN,
        settings.WHATSAPP_PHONE_NUMBER_ID,
        settings.WHATSAPP_GRAPH_API_VERSION,
        settings.WHATSAPP_OTP_TEMPLATE_NAME,
    ))


def send_whatsapp_otp(phone_number, otp_code):
    if not is_whatsapp_otp_configured():
        raise ImproperlyConfigured('Les paramètres WhatsApp OTP sont incomplets.')

    url = (
        f'https://graph.facebook.com/{settings.WHATSAPP_GRAPH_API_VERSION}/'
        f'{settings.WHATSAPP_PHONE_NUMBER_ID}/messages'
    )
    payload = {
        'messaging_product': 'whatsapp',
        'to': re.sub(r'\D', '', phone_number),
        'type': 'template',
        'template': {
            'name': settings.WHATSAPP_OTP_TEMPLATE_NAME,
            'language': {'code': settings.WHATSAPP_OTP_TEMPLATE_LANGUAGE},
            'components': [{
                'type': 'body',
                'parameters': [{'type': 'text', 'text': otp_code}],
            }],
        },
    }
    request = Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {settings.WHATSAPP_ACCESS_TOKEN}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    try:
        with urlopen(request, timeout=10) as response:
            if not 200 <= response.status < 300:
                raise WhatsAppDeliveryError('Le fournisseur WhatsApp a refusé le message.')
    except (HTTPError, URLError, TimeoutError) as error:
        raise WhatsAppDeliveryError('Échec de l’envoi du code WhatsApp.') from error
