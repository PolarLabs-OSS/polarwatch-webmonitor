"""Fail publishing unless the four required archives are structurally valid."""
import sys
import tarfile
import zipfile
from pathlib import Path

root=Path(sys.argv[1])
expected=[
    ("PolarWatch-WebMonitor-v2.1.0-Windows-x64.zip","PolarWatch-WebMonitor.exe"),
    ("PolarWatch-WebMonitor-v2.1.0-Windows-ARM64.zip","PolarWatch-WebMonitor.exe"),
    ("PolarWatch-WebMonitor-v2.1.0-Linux-x64.tar.gz","PolarWatch-WebMonitor"),
    ("PolarWatch-WebMonitor-v2.1.0-Linux-ARM64.tar.gz","PolarWatch-WebMonitor"),
]
for filename,exe in expected:
    p=root/filename
    assert p.is_file() and p.stat().st_size>1_000_000,filename
    if p.suffix==".zip":
        with zipfile.ZipFile(p) as z:
            assert z.testzip() is None,filename
            candidates=[x for x in z.infolist() if x.filename.endswith("/"+exe)]
            assert candidates and candidates[0].file_size>1_000_000
    else:
        with tarfile.open(p) as z:
            candidates=[x for x in z.getmembers() if x.name.endswith("/"+exe)]
            assert candidates and candidates[0].size>1_000_000
            assert candidates[0].mode & 0o111
    print("VALIDATED",filename,p.stat().st_size)
print("ALL_FOUR_PLATFORMS_VALID")
