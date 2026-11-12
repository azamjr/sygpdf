#!/usr/bin/env python3
"""Launch the local Docker app using only Python's standard library."""
import os
from pathlib import Path
import platform
import shutil
import subprocess
import time
import webbrowser


ROOT = Path(__file__).resolve().parent
URL = "http://127.0.0.1:8765"


def find_docker():
    executable = shutil.which("docker")
    if executable:
        return executable
    candidates = [
        Path("/usr/local/bin/docker"),
        Path("/Applications/Docker.app/Contents/Resources/bin/docker"),
    ]
    if platform.system() == "Windows":
        candidates = [
            Path(os.environ.get("ProgramFiles", "C:/Program Files"))
            / "Docker/Docker/resources/bin/docker.exe",
            Path(os.environ.get("LOCALAPPDATA", ""))
            / "Programs/DockerDesktop/resources/bin/docker.exe",
        ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    raise RuntimeError("Install Docker first. See the local setup instructions in README.md.")


def run_docker(docker, *arguments, quiet=False, timeout=None):
    return subprocess.run(
        [docker, *arguments],
        cwd=ROOT,
        stdout=subprocess.DEVNULL if quiet else None,
        stderr=subprocess.DEVNULL if quiet else None,
        timeout=timeout,
        check=False,
    ).returncode == 0


def ready(docker, *arguments):
    try:
        return run_docker(docker, *arguments, quiet=True, timeout=5)
    except subprocess.TimeoutExpired:
        return False


def wait_until(check, seconds, message):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if check():
            return
        time.sleep(2)
    raise RuntimeError(message)


def open_docker_desktop():
    system = platform.system()
    if system == "Darwin":
        subprocess.Popen(["open", "-a", "Docker"])
        return
    if system == "Windows":
        locations = [
            Path(os.environ.get("ProgramFiles", "C:/Program Files"))
            / "Docker/Docker/Docker Desktop.exe",
            Path(os.environ.get("LOCALAPPDATA", ""))
            / "Programs/DockerDesktop/Docker Desktop.exe",
        ]
        for location in locations:
            if location.is_file():
                subprocess.Popen([str(location)])
                return
    if system == "Linux" and shutil.which("systemctl"):
        for command in (
            ["systemctl", "--user", "start", "docker"],
            ["systemctl", "--user", "start", "docker-desktop"],
            ["systemctl", "start", "docker"],
        ):
            try:
                result = subprocess.run(
                    command, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, timeout=30, check=False,
                )
                if result.returncode == 0:
                    return
            except subprocess.TimeoutExpired:
                continue
    raise RuntimeError(
        "Start Docker and ensure your user can run it, then launch this file again."
    )


def main():
    if not (ROOT / "compose.yaml").is_file():
        raise RuntimeError("Extract the entire project and keep this launcher beside compose.yaml.")
    docker = find_docker()
    if not ready(docker, "info"):
        print("Starting Docker...", flush=True)
        open_docker_desktop()
        wait_until(
            lambda: ready(docker, "info"),
            120,
            "Docker did not become ready. Open Docker Desktop and try again.",
        )
    if not ready(docker, "compose", "version"):
        raise RuntimeError("Install the Docker Compose plugin or update Docker Desktop.")
    print("Starting sygpdf. The first build can take several minutes.", flush=True)
    if not run_docker(docker, "compose", "up", "--build", "-d"):
        raise RuntimeError("Docker startup failed. Review the output above.")
    probe = (
        "import urllib.request; "
        "urllib.request.urlopen('http://127.0.0.1:8765/healthz', timeout=2)"
    )
    try:
        wait_until(
            lambda: ready(docker, "compose", "exec", "-T", "sygpdf", "python", "-c", probe),
            60,
            "The app did not become ready. Review the logs above.",
        )
    except RuntimeError:
        run_docker(docker, "compose", "logs", "--tail=50", "sygpdf", timeout=15)
        raise
    print("sygpdf is ready at " + URL, flush=True)
    if not webbrowser.open(URL):
        print("Open that address in your browser.", flush=True)
    print("The app runs in the background. Stop it with docker compose stop.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.SubprocessError) as error:
        print("\nUnable to start sygpdf. " + str(error), flush=True)
        try:
            input("Press Enter to close...")
        except EOFError:
            pass
        raise SystemExit(1)

