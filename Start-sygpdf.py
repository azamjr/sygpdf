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
    system = platform.system()
    candidates = [
        Path.home() / ".docker/bin/docker",
        Path.home() / ".local/bin/docker",
        Path("/usr/local/bin/docker"),
        Path("/usr/bin/docker"),
        Path("/snap/bin/docker"),
    ]
    if system == "Darwin":
        candidates.append(Path("/Applications/Docker.app/Contents/Resources/bin/docker"))
        candidates.append(Path.home() / "Applications/Docker.app/Contents/Resources/bin/docker")
    if system == "Windows":
        installations = [
            Path(os.environ.get("ProgramFiles", "C:/Program Files"))
            / "Docker/Docker",
            Path(os.environ.get("LOCALAPPDATA", ""))
            / "Programs/DockerDesktop",
        ]
        candidates = [
            installation / relative
            for installation in installations
            for relative in ("resources/bin/docker.exe", "bin/docker.exe")
        ]
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    instructions = {
        "Windows": (
            "Install Docker Desktop with the WSL 2 backend and Linux containers.\n"
            "https://docs.docker.com/desktop/setup/install/windows-install/"
        ),
        "Darwin": (
            "Install Docker Desktop for your Mac's Apple silicon or Intel processor.\n"
            "https://docs.docker.com/desktop/setup/install/mac-install/"
        ),
        "Linux": (
            "Install Docker Engine and the Docker Compose plugin for your distribution.\n"
            "https://docs.docker.com/engine/install/"
        ),
    }
    raise RuntimeError(
        "Docker CLI was not found on PATH or in common installation folders.\n"
        + instructions.get(system, "See README.md for supported operating systems.")
        + "\nAfter installation, start Docker and launch sygpdf again."
        + "\nIf Docker is already installed, run docker version in a terminal."
        + "\nA custom Docker installation must make its docker command available on PATH."
    )


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


def docker_info_error(docker):
    try:
        result = subprocess.run(
            [docker, "info"], cwd=ROOT, capture_output=True,
            text=True, timeout=5, check=False,
        )
    except subprocess.TimeoutExpired:
        return "Docker did not respond within five seconds."
    return (result.stderr or result.stdout).strip()[-1200:]


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
        error = docker_info_error(docker)
        if platform.system() == "Linux" and "permission denied" in error.lower():
            raise RuntimeError(
                "Your Ubuntu account cannot access Docker. Log out and back in "
                "after joining the docker group, then retry.\n" + error
            )
        print("Starting Docker...", flush=True)
        open_docker_desktop()
        try:
            wait_until(
                lambda: ready(docker, "info"),
                120,
                "Docker did not become ready.",
            )
        except RuntimeError as exc:
            raise RuntimeError(str(exc) + "\n" + docker_info_error(docker)) from exc
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

