"""Non-network smoke test of source and PyInstaller executable."""
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import customtkinter as ctk
from polarwatch_modern_ui import PolarWatchModern

root=ctk.CTk()
try:
    ui=PolarWatchModern(root,sites=[],autostart=False)
    root.update_idletasks()
    root.update()
    assert "PolarWatch" in root.title()
    assert ui.summary_vars["all"].get()=="0"
    assert ui.selected_site() is None
    ui.toggle_expert()
    print("SOURCE_GUI_OK",platform.platform(),root.winfo_geometry(),flush=True)
finally:
    ui.close()

exe=ROOT/"dist"/("PolarWatch-WebMonitor.exe" if os.name=="nt" else "PolarWatch-WebMonitor")
assert exe.is_file(),exe
if os.name!="nt":
    exe.chmod(0o755)
child=subprocess.Popen([str(exe)],cwd=str(ROOT),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
try:
    for i in range(13):
        time.sleep(1)
        if child.poll() is not None:
            out,err=child.communicate(timeout=1)
            raise RuntimeError(f"Packaged GUI exited unexpectedly: {child.returncode}\n"
                               f"STDOUT {out[-300:].decode(errors='replace')}\n"
                               f"STDERR {err[-1100:].decode(errors='replace')}")
    print("PACKAGED_GUI_RUNNING",exe.stat().st_size,flush=True)
finally:
    if child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)
