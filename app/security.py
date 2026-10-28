"""Request perimeter for the supported single-process service."""
import contextlib
import os
from urllib.parse import urlsplit
from starlette.responses import JSONResponse
from . import store
from .runtime import production

MAX_BODY = 9 * 1024 * 1024


class RequestPerimeter:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = dict(scope['headers'])
        async def reject(status, message):
            response = JSONResponse({'detail': message}, status_code=status)
            await response(scope, receive, secured_send)

        async def secured_send(message):
            if message['type'] == 'http.response.start':
                secure = [(b'x-content-type-options', b'nosniff'),
                          (b'referrer-policy', b'no-referrer'),
                          (b'x-frame-options', b'DENY'),
                          (b'content-security-policy', b"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"),
                          (b'permissions-policy', b'camera=(), microphone=(), geolocation=()')]
                if scope['path'].startswith('/api/'):
                    secure.append((b'cache-control', b'no-store'))
                if production():
                    secure.append((b'strict-transport-security', b'max-age=31536000'))
                message['headers'] = [(k,v) for k,v in message['headers'] if k.lower() not in {h[0] for h in secure}] + secure
            await send(message)

        health_probe=scope['path']=='/api/health' and scope.get('client',('',0))[0] in {'127.0.0.1','::1'}
        if production() and scope['scheme']!='https' and not health_probe:
            return await reject(400, 'Use the secure Niyam workspace address.')

        # Cookie requests are same-origin only. CLI clients may use Bearer auth.
        if scope['method'] not in {'GET', 'HEAD', 'OPTIONS'}:
            origin = headers.get(b'origin', b'').decode('latin1')
            expected = os.getenv('NIYAM_PUBLIC_URL', '').rstrip('/') or scope['scheme'] + '://' + headers.get(b'host', b'').decode('latin1')
            if (origin and origin != expected) or headers.get(b'sec-fetch-site') == b'cross-site':
                return await reject(403, 'This request must come from your Niyam workspace.')
        length = headers.get(b'content-length')
        if length is not None:
            try:
                if not length.isdigit():
                    raise ValueError()
                if int(length) > MAX_BODY:
                    return await reject(413, 'The request is too large. Attach files smaller than 8 MB.')
            except ValueError:
                return await reject(400, 'Invalid request size.')
        body = bytearray()
        # Enforce the actual bytes, including requests without Content-Length.
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            body.extend(message.get('body', b''))
            if len(body) > MAX_BODY:
                return await reject(413, 'The request is too large. Attach files smaller than 8 MB.')
            if not message.get('more_body', False):
                break
        if length is not None and len(body) != int(length):
            return await reject(400, 'Invalid request size.')
        delivered = False
        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
            return await receive()
        await self.app(scope, replay, secured_send)


@contextlib.contextmanager
def instance_lock():
    """Prevent a second worker resetting jobs or starting a duplicate scanner."""
    store.STATE.mkdir(parents=True, exist_ok=True)
    handle = open(store.STATE / 'service.lock', 'a+b')
    if handle.seek(0,2)==0:
        handle.write(b'0'); handle.flush()
    handle.seek(0)
    try:
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise RuntimeError('Only one Niyam worker may use this state directory.') from error
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)
    finally:
        handle.close()
