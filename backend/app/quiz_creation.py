"""Canonical request identity, without source text or provider credentials."""
import hashlib
import json


def creation_fingerprint(document_id, request):
    payload = {'document_id': document_id, **request.model_dump(mode='json', exclude={'request_id'})}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
