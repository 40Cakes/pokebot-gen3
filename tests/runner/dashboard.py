"""
Local web page to start parallel test runs and follow them (progress per state, failures, output).

    python tests/runner/dashboard.py [port]

Then open http://127.0.0.1:8765. It only listens on 127.0.0.1. Needs `POKEBOT_MASTER_TESTS` (see
`tests/README.md`).
"""

import json
import re
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import psutil

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_parallel  # noqa: E402

STATIC = Path(__file__).resolve().parent / "static"
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/theme.js": ("theme.js", "text/javascript; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}
SAFE_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")
PROGRESS_LINE = re.compile(r"\[progress\] (\w+) (\S+) (.*)$", re.M)


def is_alive(pid: int | None) -> bool:
    if pid is None:
        return False
    try:
        return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except psutil.Error:
        return False


def read_jobs(run_directory: Path) -> dict | None:
    try:
        return json.loads((run_directory / "jobs.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def short_state_name(path: str) -> str:
    return re.sub(r".*Master Tests[\\/]", "", path).replace("\\", "/")


def progress_of(log: Path) -> dict:
    """Each state's status, in order, from the progress lines that the tests print."""
    states, total = {}, 0
    if log.exists():
        text = log.read_text(encoding="utf-8", errors="replace")
        # Not anchored: `unittest -v` prints the test name without a line break before the first line
        for event, test, value in PROGRESS_LINE.findall(text):
            if event == "total":
                total += int(value)
            elif event == "start":
                states[(test, value)] = "running"
            elif event in ("ok", "fail", "skip"):
                states[(test, value)] = event
        failures = run_parallel.failures(text)
    else:
        failures = []
    return {
        "total": total,
        "states": [{"name": short_state_name(name), "status": status} for (_, name), status in states.items()],
        "failures": failures,
    }


def run_details(name: str) -> dict | None:
    run_directory = run_parallel.LOGS / name
    state = read_jobs(run_directory)
    if state is None:
        return None
    state["done"] = (run_directory / "done").exists()
    state["supervisor_alive"] = is_alive(state.get("supervisor_pid"))
    state["now"] = time.time()
    for job in state["jobs"]:
        job["progress"] = progress_of(run_directory / job["log"])
        # A job whose process just ended stays 'running' until the supervisor records it
        if job["status"] == "running" and not is_alive(job["pid"]) and not state["supervisor_alive"]:
            job["status"] = "lost"
    return state


def list_runs() -> list[dict]:
    runs = []
    if run_parallel.LOGS.exists():
        for run_directory in run_parallel.LOGS.iterdir():
            state = read_jobs(run_directory)
            if state is None:
                continue
            counts = {}
            for job in state["jobs"]:
                counts[job["status"]] = counts.get(job["status"], 0) + 1
            runs.append(
                {
                    "name": state["name"],
                    "started": state["started"],
                    "ended": state["ended"],
                    "done": (run_directory / "done").exists(),
                    "counts": counts,
                }
            )
    return sorted(runs, key=lambda run: run["started"], reverse=True)


def stop_run(name: str) -> None:
    run_directory = run_parallel.LOGS / name
    (run_directory / "stop").write_text("stop", encoding="utf-8")
    state = read_jobs(run_directory)
    if state is None:
        return
    for pid in [state.get("supervisor_pid")] + [job["pid"] for job in state["jobs"] if job["status"] == "running"]:
        try:
            process = psutil.Process(pid)
            for child in process.children(recursive=True):
                child.kill()
            process.kill()
        except (psutil.Error, TypeError, ValueError):
            pass
    for job in state["jobs"]:
        if job["status"] in ("queued", "running"):
            job["status"] = "stopped" if job["status"] == "running" else "cancelled"
            job["ended"] = time.time()
    state["ended"] = time.time()
    run_parallel.write_json(run_directory / "jobs.json", state)


def tail(path: Path, lines: int) -> str:
    if not path.exists():
        return ""
    return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:])


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, data, status: int = 200) -> None:
        self.send(status, json.dumps(data).encode("utf-8"), "application/json")

    def do_GET(self):
        url = urlparse(self.path)
        query = {key: values[0] for key, values in parse_qs(url.query).items()}
        if url.path in STATIC_FILES:
            file_name, content_type = STATIC_FILES[url.path]
            self.send(200, (STATIC / file_name).read_bytes(), content_type)
        elif url.path == "/api/runs":
            try:
                languages = run_parallel.available_languages()
                error = None
            except RuntimeError as exception:
                languages, error = [], str(exception)
            self.send_json(
                {
                    "runs": list_runs(),
                    "modules": run_parallel.available_modules(),
                    "languages": languages,
                    "max_processes": run_parallel.recommended_processes(),
                    "error": error,
                }
            )
        elif url.path == "/api/run":
            name = query.get("name", "")
            details = run_details(name) if SAFE_NAME.match(name) else None
            self.send_json(details or {"error": "Unknown run"}, 200 if details else 404)
        elif url.path == "/api/log":
            name, job = query.get("run", ""), query.get("job", "")
            if not (SAFE_NAME.match(name) and SAFE_NAME.match(job)):
                self.send_json({"error": "Invalid name"}, 400)
                return
            lines = min(int(query.get("lines", "400")), 5000)
            self.send(200, tail(run_parallel.LOGS / name / f"{job}.log", lines).encode("utf-8"), "text/plain")
        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        url = urlparse(self.path)
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))) or b"{}")
        except ValueError:
            self.send_json({"error": "Invalid JSON"}, 400)
            return
        if url.path == "/api/start":
            name = body.get("name", "")
            modules = [module for module in body.get("modules", []) if module in run_parallel.available_modules()]
            try:
                known_languages = run_parallel.available_languages()
            except RuntimeError as exception:
                self.send_json({"error": str(exception)}, 400)
                return
            languages = [language for language in body.get("languages", []) if language in known_languages]
            max_processes = max(1, min(int(body.get("max_processes") or run_parallel.recommended_processes()), 64))
            if not SAFE_NAME.match(name) or not modules or not languages:
                self.send_json({"error": "Give the run a name and pick at least one test file and language."}, 400)
                return
            existing = run_details(name)
            if existing and not existing["done"] and existing["supervisor_alive"]:
                self.send_json({"error": f"The run {name} is still going."}, 409)
                return
            run_parallel.start(name, modules, languages, max_processes)
            self.send_json({"started": name})
        elif url.path == "/api/stop":
            name = body.get("name", "")
            if not SAFE_NAME.match(name):
                self.send_json({"error": "Invalid name"}, 400)
                return
            stop_run(name)
            self.send_json({"stopped": name})
        else:
            self.send_json({"error": "Not found"}, 404)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Test runner dashboard on http://127.0.0.1:{port}")
    server.serve_forever()
