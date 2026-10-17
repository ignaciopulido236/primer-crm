import json
import os
import unittest
from unittest.mock import patch, MagicMock
from api import Client, ApiError, DEFAULT_URL, validate_url
import security

class ApiTests(unittest.TestCase):
    def test_url(self):
        self.assertEqual(validate_url(DEFAULT_URL),DEFAULT_URL)
        for url in ['http://script.google.com/x/exec','https://evil.test/exec',DEFAULT_URL+'?key=secret']:
            with self.assertRaises(ValueError):validate_url(url)

    def request(self, payload):
        opener=MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value=payload
        return opener

    def test_post_secret_not_in_url(self):
        opener=self.request(b'{"ok":true,"data":[]}')
        with patch('api.build_opener',return_value=opener):
            Client(DEFAULT_URL,'test-secret').call('list',limit=50)
        req=opener.open.call_args.args[0]
        self.assertEqual(req.method,'POST')
        self.assertNotIn('test-secret',req.full_url)
        self.assertEqual(json.loads(req.data)['api_key'],'test-secret')

    def test_application_error(self):
        opener=self.request(b'{"ok":false,"status":401,"error":{"message":"Clave invalida"}}')
        with patch('api.build_opener',return_value=opener):
            with self.assertRaisesRegex(ApiError,'Clave invalida'):Client(DEFAULT_URL,'x').call('list')

    def test_html(self):
        with patch('api.build_opener',return_value=self.request(b'<html>login</html>')):
            with self.assertRaisesRegex(ApiError,'no devolvió JSON'):Client(DEFAULT_URL,'x').call('list')

    def test_redirect_rejects_other_hosts(self):
        from api import GoogleRedirect
        from urllib.request import Request
        with self.assertRaises(ApiError):
            GoogleRedirect().redirect_request(Request(DEFAULT_URL),None,302,'',{},'https://evil.test/')

    @unittest.skipUnless(os.name=='nt','DPAPI requiere Windows')
    def test_dpapi_roundtrip(self):
        encrypted=security.encrypt('clave-de-prueba')
        self.assertNotIn(b'clave-de-prueba',encrypted)
        self.assertEqual(security.decrypt(encrypted),'clave-de-prueba')
        with self.assertRaises(OSError):security.decrypt(b'corrupt')

    @unittest.skipUnless(os.name=='nt','UI Windows')
    def test_window_constructs(self):
        from app import App
        app=App()
        self.assertEqual(app.title(),'Primer CRM · Clientes')
        app.destroy()

if __name__=='__main__':unittest.main()
