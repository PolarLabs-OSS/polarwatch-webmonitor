"""PolarWatch v2 regression tests. No external HTTP or DNS requests."""
from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
import urllib.error
from email.message import Message
from pathlib import Path
from unittest.mock import patch

import polarwatch_monitor_core as c

class FakeResponse:
    def __init__(self,code=200,url="https://example.org/final",headers=None):
        self.status=code
        self.url=url
        self.headers=Message()
        for key,val in (headers or {}).items():
            self.headers[key]=val
    def __enter__(self):return self
    def __exit__(self,*_):pass
    def geturl(self):return self.url
    def read(self,count):return b"OK"[:count]

class MonitorTests(unittest.TestCase):
    def test_url_validation(self):
        self.assertEqual(c.normalize_url("example.org"),"https://example.org")
        self.assertEqual(c.normalize_url("http://example.org/"),"http://example.org/")
        for value in ["", "file:///tmp/abc", "ftp://example.org",
                      "https://john:pw@example.org","https://example.org:99999"]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    c.normalize_url(value)

    def test_site_list_is_json_only_and_deduplicated(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/"test"/"sites.json"
            s=c.new_site("Demo","example.org")
            c.save_sites([s],path)
            self.assertTrue(path.is_file())
            self.assertEqual(len(c.load_sites(path)),1)
            duplicate=[s, dict(s,id="another")]
            c.save_sites(duplicate,path)
            self.assertEqual(len(c.load_sites(path)),1)
            self.assertEqual(set(json.loads(path.read_text())[0]),{"name","url","id"})

    def test_broken_json_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/"sites.json"
            path.write_text("malformed")
            with self.assertRaises(ValueError):
                c.load_sites(path)
            self.assertEqual(path.read_text(),"malformed")

    def test_success_dns_redirect_security_headers(self):
        s=c.new_site("Example","example.org")
        fake=FakeResponse(200,"https://example.org/final",{
            "Server":"UnitTest",
            "Content-Type":"text/html",
            "Strict-Transport-Security":"max-age=100",
            "X-Content-Type-Options":"nosniff"
        })
        with patch.object(c,"_dns_ips",return_value=["203.0.113.10"]), \
             patch.object(c.urllib.request,"urlopen",return_value=fake), \
             patch.object(c,"_tls_details",return_value={
                 "tls":"TLSv1.3","cipher":"TLS_AES_128_GCM_SHA256",
                 "ssl_days":46,"ssl_until":"test"}):
            out=c.probe_site(s)
        self.assertEqual(out["state"],"UP")
        self.assertEqual(out["code"],200)
        self.assertEqual(out["server"],"UnitTest")
        self.assertTrue(out["redirect"])
        self.assertEqual(out["ssl_days"],46)
        self.assertTrue(out["security_headers"]["HSTS"])
        self.assertFalse(out["security_headers"]["CSP"])
        self.assertEqual(out["dns"],["203.0.113.10"])

    def test_http_not_found_is_down(self):
        s=c.new_site("Gone","http://gone.example")
        fake=FakeResponse(404,s["url"])
        with patch.object(c,"_dns_ips",return_value=[]), \
             patch.object(c.urllib.request,"urlopen",return_value=fake):
            out=c.probe_site(s)
        self.assertEqual(out["state"],"DOWN")
        self.assertEqual(out["code"],404)
        self.assertIn("HTTP 404",out["error"])

    def test_connection_error_is_down(self):
        s=c.new_site("Timeout","https://timeout.example")
        with patch.object(c,"_dns_ips",return_value=[]), \
             patch.object(c.urllib.request,"urlopen",side_effect=urllib.error.URLError("offline")), \
             patch.object(c,"_tls_details",side_effect=OSError):
            out=c.probe_site(s)
        self.assertEqual(out["state"],"DOWN")
        self.assertIsNone(out["code"])
        self.assertIsNotNone(out["latency"])
        self.assertNotEqual(out["error"],"")

    def test_warn_on_expiring_cert(self):
        s=c.new_site("SSL","https://ssl.example")
        with patch.object(c,"_dns_ips",return_value=[]), \
             patch.object(c.urllib.request,"urlopen",return_value=FakeResponse(200,s["url"])), \
             patch.object(c,"_tls_details",return_value={
                 "tls":"TLSv1.3","cipher":"cipher","ssl_days":4,"ssl_until":"soon"}):
            out=c.probe_site(s)
        self.assertTrue(any("scadenza" in n for n in out["notes"]))

if __name__=="__main__":
    unittest.main()
