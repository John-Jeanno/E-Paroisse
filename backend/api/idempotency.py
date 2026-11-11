import hashlib
import json
from functools import wraps

from django.db import IntegrityError, transaction
from rest_framework.response import Response
from rest_framework import status

from .models import IdempotencyRecord


def idempotent(handler):
    @wraps(handler)
    def wrapped(view, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler(view, request, *args, **kwargs)
        key = request.headers.get('Idempotency-Key', '').strip()
        if not key:
            return handler(view, request, *args, **kwargs)
        if len(key) > 128:
            return Response(
                {'detail': 'La clé de synchronisation est trop longue.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request_hash = hashlib.sha256(
            b'\0'.join((request.method.encode(), request.path.encode(), request.body))
        ).hexdigest()

        def replay(record):
            if record.request_hash != request_hash:
                return Response(
                    {'detail': 'Cette clé de synchronisation a déjà été utilisée pour une autre action.'},
                    status=status.HTTP_409_CONFLICT,
                )
            return Response(record.response_data, status=record.response_status)

        existing = IdempotencyRecord.objects.filter(user=request.user, key=key).first()
        if existing:
            return replay(existing)

        try:
            with transaction.atomic():
                response = handler(view, request, *args, **kwargs)
                if 200 <= response.status_code < 300:
                    response_data = json.loads(json.dumps(response.data))
                    IdempotencyRecord.objects.create(
                        user=request.user,
                        key=key,
                        request_hash=request_hash,
                        response_status=response.status_code,
                        response_data=response_data,
                    )
                return response
        except IntegrityError:
            existing = IdempotencyRecord.objects.filter(user=request.user, key=key).first()
            if existing:
                return replay(existing)
            raise

    return wrapped
