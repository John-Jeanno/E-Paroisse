import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.urls import reverse
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateDocumentStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(location=None, base_url=None)

    @property
    def location(self):
        return os.fspath(settings.PRIVATE_DOCUMENT_ROOT)

    @property
    def base_url(self):
        return None

    def url(self, name):
        return reverse(
            'admin:api_parishdocument_download_attachment',
            kwargs={'filename': name},
        )


private_document_storage = PrivateDocumentStorage()
