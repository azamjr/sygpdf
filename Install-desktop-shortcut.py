#!/usr/bin/env python3
"""Create a desktop shortcut to this copy of sygpdf."""
import base64
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent


def powershell(script):
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-EncodedCommand", encoded],
        check=True, capture_output=True, encoding="utf-8",
    )
    return result.stdout.strip()


def ps_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def desktop_folder(system):
    if system == "Windows":
        folder = powershell(
            "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
            "[Environment]::GetFolderPath('Desktop')"
        )
        if not folder:
            raise RuntimeError("Windows did not return a Desktop folder.")
        return Path(folder)
    if system == "Linux" and shutil.which("xdg-user-dir"):
        result = subprocess.run(
            ["xdg-user-dir", "DESKTOP"], check=True,
            capture_output=True, text=True,
        )
        folder = Path(result.stdout.strip())
        if not folder.is_absolute() or folder == Path.home():
            raise RuntimeError("Enable a Desktop folder in your Linux desktop settings first.")
        return folder
    return Path.home() / "Desktop"


def desktop_text(value):
    # Desktop Entry string values are decoded before Exec argument parsing.
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")


def exec_argument(value):
    # Quote one argument, escape shell-reserved characters, then encode the value.
    value = str(value).replace("%", "%%")
    for character in ("\\", '"', "`", "$"):
        value = value.replace(character, "\\" + character)
    return desktop_text('"' + value + '"')


def install():
    launcher = ROOT / "Start-sygpdf.py"
    if not launcher.is_file() or not (ROOT / "compose.yaml").is_file():
        raise RuntimeError("Extract the entire project and run this installer from that folder.")
    system = platform.system()
    if system not in {"Windows", "Darwin", "Linux"}:
        raise RuntimeError("Supported desktop systems are Windows, macOS and Linux.")
    desktop = desktop_folder(system)
    desktop.mkdir(parents=True, exist_ok=True)
    python = Path(sys.executable)
    if system == "Windows" and python.name.lower() == "pythonw.exe":
        python = python.with_name("python.exe")
    if system == "Windows":
        shortcut = desktop / "sygpdf.lnk"
        arguments = subprocess.list2cmdline([str(launcher)])
        powershell(
            "$ErrorActionPreference = 'Stop'; "
            "$shell = New-Object -ComObject WScript.Shell; "
            "$link = $shell.CreateShortcut(" + ps_literal(shortcut) + "); "
            "$link.TargetPath = " + ps_literal(python) + "; "
            "$link.Arguments = " + ps_literal(arguments) + "; "
            "$link.WorkingDirectory = " + ps_literal(ROOT) + "; "
            "$link.Description = 'Start local sygpdf and open the browser'; "
            "$link.Save()"
        )
    elif system == "Darwin":
        shortcut = desktop / "sygpdf.command"
        shortcut.write_text(
            "#!/bin/sh\nexec " + shlex.quote(str(python)) + " "
            + shlex.quote(str(launcher)) + "\n",
            encoding="utf-8",
        )
        shortcut.chmod(0o755)
    else:
        shortcut = desktop / "sygpdf.desktop"
        shortcut.write_text(
            "[Desktop Entry]\nType=Application\nName=sygpdf\n"
            "Comment=Start local sygpdf and open the browser\n"
            "Exec=" + exec_argument(python) + " " + exec_argument(launcher) + "\n"
            "Path=" + desktop_text(ROOT) + "\n"
            "Terminal=true\nIcon=applications-office\nCategories=Office;\n",
            encoding="utf-8",
        )
        shortcut.chmod(0o755)
        if shutil.which("gio"):
            # Some desktops require an additional Allow Launching action.
            subprocess.run(
                ["gio", "set", str(shortcut), "metadata::trusted", "true"],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
    print("Created desktop shortcut: " + str(shortcut), flush=True)
    print("Double-click it to start Docker and open the local app.", flush=True)
    if system == "Linux":
        print("If prompted, right-click the shortcut and choose Allow Launching.", flush=True)
    print("Keep the project folder in this location. Reinstall the shortcut if you move it.", flush=True)
    return shortcut


if __name__ == "__main__":
    status = 0
    try:
        install()
    except (RuntimeError, OSError, subprocess.SubprocessError) as error:
        print("Shortcut installation failed. " + str(error), flush=True)
        status = 1
    try:
        input("Press Enter to close...")
    except EOFError:
        pass
    raise SystemExit(status)
