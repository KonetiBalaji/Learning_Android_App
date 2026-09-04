"""Response-delay fixture installed only by the explicitly opted-in localhost QA runner."""
import asyncio
from fastapi.responses import JSONResponse


def install_upload_delay(app, seconds: int, fail_saved_response: bool = False):
    if not 1 <= seconds <= 20:
        raise ValueError('QA upload response delay must be 1 to 20 seconds')

    failed_request_ids = set()

    @app.middleware('http')
    async def delay(request, call_next):
        response = await call_next(request)
        if request.method == 'POST' and request.url.path == '/v1/documents':
            await asyncio.sleep(seconds)
            request_id = request.headers.get('X-Upload-Request-ID')
            if fail_saved_response and response.status_code == 201 and request_id not in failed_request_ids:
                failed_request_ids.add(request_id)
                return JSONResponse({'detail': 'Scripted QA lost upload response'}, status_code=503)
        return response
