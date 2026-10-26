"""Create platform-native portable archives, including license and usage notes."""
import argparse
import io
import tarfile
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--os",choices=("windows","linux"),required=True)
    parser.add_argument("--arch",choices=("x64","ARM64"),required=True)
    parser.add_argument("--version",default="2.1.0")
    a=parser.parse_args()
    binary="PolarWatch-WebMonitor.exe" if a.os=="windows" else "PolarWatch-WebMonitor"
    exe=ROOT/"dist"/binary
    assert exe.is_file() and exe.stat().st_size>1_000_000, exe
    tag="Windows" if a.os=="windows" else "Linux"
    basename=f"PolarWatch-WebMonitor-v{a.version}-{tag}-{a.arch}"
    folder="PolarWatch-WebMonitor"
    notes=(
        f"PolarWatch Web Monitor v{a.version} — {tag} {a.arch}\n\n"
        "Free and open-source website monitor by PolarLabs.\n"
        "No account, database or license needed. Website checks run only while open.\n\n"
        + ("Extract this ZIP and launch PolarWatch-WebMonitor.exe.\n" if a.os=="windows"
           else "Extract this archive, then run:\n"
                "  chmod +x PolarWatch-WebMonitor\n"
                "  ./PolarWatch-WebMonitor\n"
                "A graphical Linux desktop (X11 or Wayland/XWayland) is required.\n")
        + "\nExecutables are not code-signed. Do not bypass OS security warnings.\n"
          "More information: https://github.com/PolarLabs-OSS/polarwatch-webmonitor\n"
    ).encode("utf-8")
    data={
        f"{folder}/{binary}":exe.read_bytes(),
        f"{folder}/README.txt":notes,
        f"{folder}/LICENSE":(ROOT/"LICENSE").read_bytes(),
    }
    out=ROOT/"out"
    out.mkdir(exist_ok=True)
    if a.os=="windows":
        archive=out/(basename+".zip")
        with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
            for name,body in data.items():
                z.writestr(name,body)
    else:
        archive=out/(basename+".tar.gz")
        with tarfile.open(archive,"w:gz") as z:
            for name,body in data.items():
                info=tarfile.TarInfo(name)
                info.size=len(body)
                info.mode=0o755 if name.endswith("/"+binary) else 0o644
                z.addfile(info,io.BytesIO(body))
    print("ARCHIVE_OK",archive.name,archive.stat().st_size)

if __name__=="__main__":
    main()
