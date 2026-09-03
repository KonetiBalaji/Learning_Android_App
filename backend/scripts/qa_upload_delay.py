"""Response-delay fixture installed only by the explicitly opted-in localhost QA runner."""
import asyncio


def install_upload_delay(app, seconds: int):
    if not 1 <= seconds <= 20:
        raise ValueError('QA upload response delay must be 1 to 20 seconds')

    @app.middleware('http')
    async def delay(request, call_next):
        response = await call_next(request)
        if request.method == 'POST' and request.url.path == '/v1/documents':
            await asyncio.sleep(seconds)
        return response
