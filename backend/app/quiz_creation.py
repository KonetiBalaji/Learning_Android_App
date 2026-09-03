"""Canonical request identity, without source text or provider credentials."""
import hashlib
import json


def creation_fingerprint(document_id, request):
    payload = {'document_id': document_id, **request.model_dump(mode='json', exclude={'request_id'})}
    # Keep pre-excerpt fingerprints stable for outstanding creation retries.
    if payload.get('source_ranges') is None:
        payload.pop('source_ranges', None)
    else:
        payload['source_ranges'] = sorted(payload['source_ranges'],
            key=lambda part: (part['start_character'], part['end_character'], part['chapter_id']))
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
