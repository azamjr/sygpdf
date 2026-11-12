#!/bin/sh
# Start the local app from its own folder, including paths containing spaces.
cd "$(dirname "$0")" || exit 1

fail() {
    printf '\n%s\n' "$1"
    printf 'Press Enter to close...'
    read -r answer
    exit 1
}

command -v docker >/dev/null 2>&1 || fail "Install Docker first. See README.md."
if ! docker info >/dev/null 2>&1; then
    if [ "$(uname -s)" = Darwin ]; then
        open -a Docker || fail "Open Docker Desktop, then try again."
    else
        fail "Start Docker first and ensure your user can run Docker. See README.md."
    fi
fi

attempt=0
until docker info >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    [ "$attempt" -lt 60 ] || fail "Docker did not become ready. Open Docker Desktop and retry."
    sleep 2
done
docker compose version >/dev/null 2>&1 || fail "Install the Docker Compose plugin. See README.md."
printf 'Starting sygpdf. The first build can take several minutes.\n'
docker compose up --build -d || fail "Startup failed. Review the Docker output above."

attempt=0
until docker compose exec -T sygpdf python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8765/healthz", timeout=2)' >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 30 ]; then
        docker compose logs --tail=50 sygpdf
        fail "The app did not become ready. Review the logs above."
    fi
    sleep 2
done
printf 'sygpdf is ready at http://127.0.0.1:8765\n'
case "$(uname -s)" in
    Darwin) open http://127.0.0.1:8765 ;;
    *) if command -v xdg-open >/dev/null 2>&1; then
           xdg-open http://127.0.0.1:8765
       fi ;;
esac
printf 'The app runs in the background. Stop it with docker compose stop.\n'
