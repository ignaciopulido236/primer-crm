import json
from urllib.parse import urlparse
from urllib.request import Request, urlopen, HTTPRedirectHandler, build_opener
from urllib.error import URLError, HTTPError

DEFAULT_URL = 'https://script.google.com/macros/s/AKfycby7ga3OfgyTcNRbPgm4YvkAC8va2sCf37JRywtjytovzFHUfGgAse-s_WjXu1Nl89An/exec'
FIELDS = ['nombre','apellido','email','telefono','empresa','cargo','estado','origen','responsable','direccion','ciudad','pais','notas']
STATES = ['nuevo','contactado','calificado','cliente','inactivo']

class ApiError(Exception):
    pass

def validate_url(url):
    p = urlparse(url)
    if (p.scheme != 'https' or p.netloc != 'script.google.com' or
        not p.path.endswith('/exec') or p.query or p.fragment):
        raise ValueError('Usa la URL HTTPS de Apps Script terminada en /exec, sin parámetros.')
    return url

class GoogleRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        p = urlparse(newurl)
        if p.scheme != 'https' or p.hostname not in ('script.google.com', 'script.googleusercontent.com'):
            raise ApiError('Google solicita autenticación o redirige a un destino no permitido. Revisa los permisos de implementación.')
        return super().redirect_request(req, fp, code, msg, headers, newurl)

class Client:
    def __init__(self, url, key):
        self.url = validate_url(url)
        self.key = key

    def call(self, action, **params):
        body = json.dumps(dict(params, action=action, api_key=self.key)).encode('utf-8')
        req = Request(self.url, data=body, headers={'Content-Type':'application/json'}, method='POST')
        try:
            with build_opener(GoogleRedirect()).open(req, timeout=45) as response:
                raw = response.read(8_000_001)
            if len(raw) > 8_000_000:
                raise ApiError('Respuesta demasiado grande. Reduce el tamaño de página.')
            result = json.loads(raw)
        except HTTPError as exc:
            raise ApiError(f'Google devolvió HTTP {exc.code}. Revisa acceso y URL de implementación.') from None
        except (URLError, TimeoutError, OSError):
            raise ApiError('No se pudo completar la conexión. Revisa internet. Si estabas guardando, actualiza la lista antes de reintentar.') from None
        except (ValueError, UnicodeError):
            raise ApiError('Google no devolvió JSON. Revisa que la aplicación permita acceso a cualquier persona.') from None
        if not isinstance(result, dict):
            raise ApiError('Respuesta inválida de la API.')
        if result.get('ok') is not True:
            error = result.get('error') or {}
            raise ApiError(str(error.get('message','La API rechazó la solicitud.')))
        return result
