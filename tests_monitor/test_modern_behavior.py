"""No-network interaction checks for PolarWatch 2.1 desktop UI."""
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import customtkinter as ctk
import polarwatch_modern_ui as ui

class ModernUITests(unittest.TestCase):
    def setUp(self):
        self.root=ctk.CTk()
        self.sites=[
            {"id":"one","name":"Demo 1","url":"https://example.org"},
            {"id":"two","name":"Demo 2","url":"https://example.net"},
        ]
        self.app=ui.PolarWatchModern(self.root,sites=self.sites,autostart=False)
        self.root.update()

    def tearDown(self):
        if self.root.winfo_exists():
            self.app.close()

    def test_select_and_expert(self):
        self.app.select_site("two")
        self.assertEqual(self.app.selected_site()["name"],"Demo 2")
        self.app.expert_switch.select()
        self.app.toggle_expert()
        self.assertTrue(self.app.expert)
        self.assertEqual(self.app.mode_chip.cget("text"),"ESPERTO")

    def test_timer_pause_resume(self):
        self.app.change_interval("Off")
        self.assertEqual(self.app.interval_seconds,0)
        self.app.change_interval("15 min")
        self.assertEqual(self.app.interval_seconds,900)
        self.assertGreater(self.app.next_scan_at,time.monotonic())

    def test_mock_monitoring_and_chart(self):
        def fake(site,timeout=8):
            return {"id":site["id"],"name":site["name"],"url":site["url"],
                    "state":"UP","code":200,"latency":84,"ttfb":60,
                    "ssl_days":91,"checked":"12:00:00",
                    "security_headers":{},"notes":[],"dns":[],"error":""}
        with patch.object(ui,"probe_site",side_effect=fake):
            self.app.scan_all()
            end=time.monotonic()+5
            while self.app.working and time.monotonic()<end:
                self.root.update()
                time.sleep(.04)
        self.assertFalse(self.app.working)
        self.assertEqual(self.app.summary_vars["up"].get(),"2")
        self.assertEqual(self.app.summary_vars["avg"].get(),"84 ms")
        self.assertEqual(self.app.series["one"],[84])
        self.assertEqual(self.app.results["two"]["code"],200)

    def test_remove_only_selected_and_no_database(self):
        with patch.object(ui.messagebox,"askyesno",return_value=True), \
             patch.object(ui,"save_sites") as saved:
            self.app.remove_selected()
            saved.assert_called_once()
            saved_args=saved.call_args.args[0]
            self.assertEqual(len(saved_args),1)
            self.assertEqual(saved_args[0]["id"],"two")
        self.assertEqual(len(self.app.sites),1)

if __name__=="__main__":
    unittest.main()
