"""
Runs test modules in parallel, one process per test module and Master Tests language.

    python tests/runner/run_parallel.py <run name> <test module>... [--languages DEU,FRA] [--max-processes 8]

By default it runs as many processes as the machine can take (see `recommended_processes()`).

It starts a supervisor in the background and returns at once. Results go to `tests/runner/logs/<run name>/`: one
log per process, `jobs.json` (read by `dashboard.py`), then `summary.txt` and a `done` file at the end.
Needs `POKEBOT_MASTER_TESTS` (see `tests/README.md`).
"""

import json
import os
import re
import subprocess
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[2]
LOGS = Path(__file__).resolve().parent / "logs"

# A test process (an emulator) uses about 300 MB
MEMORY_PER_PROCESS = 350 * 1024 * 1024

# Without a console (the supervisor runs in the background), Windows would open a window per process
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
DETACHED = NO_WINDOW | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

_lock = threading.Lock()


def recommended_processes() -> int:
    """As many processes as the machine can take: CPU threads minus 2, limited by free memory."""
    import psutil

    by_cpu = (os.cpu_count() or 2) - 2
    by_memory = int(psutil.virtual_memory().available * 0.8 // MEMORY_PER_PROCESS)
    return max(1, min(by_cpu, by_memory))


def master_tests_path() -> Path:
    value = os.environ.get("POKEBOT_MASTER_TESTS")
    if not value or not Path(value).is_dir():
        raise RuntimeError("Set POKEBOT_MASTER_TESTS to the 'Master Tests' directory (see tests/README.md).")
    return Path(value)


def available_languages() -> list[str]:
    return sorted(path.name for path in master_tests_path().iterdir() if path.is_dir())


def available_modules() -> list[str]:
    return sorted(path.stem for path in (REPOSITORY / "tests").glob("test_*.py"))


# Master Tests directory name -> language code used by `POKEBOT_TEST_LANGUAGE`
LANGUAGE_CODES = {"DEU": "D", "ESP": "S", "FRA": "F", "ITA": "I", "JPN": "J", "USA_EUR": "E"}


def uses_game_states(module: str) -> bool:
    """Test files without any save state (unit tests) don't depend on the language, so they run once."""
    source = (REPOSITORY / "tests" / f"{module}.py").read_text(encoding="utf-8")
    return "with_master_test_states" in source or "with_save_state" in source


def module_languages(module: str, languages: list[str]) -> list[str]:
    """
    The languages to run a test file in. A test file can list the only languages where its mode works in a
    `LANGUAGES = ("JPN", "USA_EUR")` line, and isn't run in the others.
    """
    if not uses_game_states(module):
        return languages[:1]
    source = (REPOSITORY / "tests" / f"{module}.py").read_text(encoding="utf-8")
    only = re.search(r"^LANGUAGES = \(([^)]*)\)", source, re.M)
    if only is None:
        return languages
    wanted = re.findall(r"[\"']([A-Z_]+)[\"']", only.group(1))
    return [language for language in languages if language in wanted]


def write_json(path: Path, data) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
    # On Windows, replacing a file fails while the dashboard has it open
    for _ in range(50):
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            time.sleep(0.05)
    os.replace(temporary, path)


class Run:
    def __init__(self, run_directory: Path, modules: list[str], languages: list[str]):
        self.run_directory = run_directory
        self.state = {
            "name": run_directory.name,
            "supervisor_pid": os.getpid(),
            "started": time.time(),
            "ended": None,
            "modules": modules,
            "languages": languages,
            "jobs": [
                {
                    "id": f"{module}.{language}",
                    "module": module,
                    "language": language,
                    "status": "queued",
                    "pid": None,
                    "started": None,
                    "ended": None,
                    "returncode": None,
                    "log": f"{module}.{language}.log",
                }
                for module in modules
                for language in module_languages(module, languages)
            ],
            # Test files that can't run in some languages, for the dashboard
            "not_in_languages": {
                module: [language for language in languages if language not in module_languages(module, languages)]
                for module in modules
                if uses_game_states(module) and module_languages(module, languages) != languages
            },
        }
        self.save()

    def save(self) -> None:
        with _lock:
            write_json(self.run_directory / "jobs.json", self.state)

    def update(self, job: dict, **changes) -> None:
        job.update(changes)
        self.save()

    def log_error(self, message: str) -> None:
        with _lock, open(self.run_directory / "supervisor.log", "a", encoding="utf-8") as handle:
            handle.write(f"[{time.strftime('%H:%M:%S')}] {message}\n")

    def run_job(self, job: dict) -> None:
        if (self.run_directory / "stop").exists():
            self.update(job, status="cancelled")
            return
        environment = dict(
            os.environ,
            POKEBOT_MASTER_TESTS_FILTER=f"{job['language']}/",
            # The English states of `tests/states/` are continued in this language
            POKEBOT_TEST_LANGUAGE=LANGUAGE_CODES.get(job["language"], "E"),
            POKEBOT_TEST_PROGRESS="1",
        )
        with open(self.run_directory / job["log"], "w", encoding="utf-8") as handle:
            process = subprocess.Popen(
                [sys.executable, "-m", "unittest", "-v", f"tests.{job['module']}"],
                cwd=REPOSITORY,
                env=environment,
                stdout=handle,
                stderr=subprocess.STDOUT,
                creationflags=NO_WINDOW,
            )
            self.update(job, status="running", pid=process.pid, started=time.time())
            returncode = process.wait()
        if (self.run_directory / "stop").exists():
            status = "stopped"
        else:
            status = "passed" if returncode == 0 else "failed"
        self.update(job, status=status, returncode=returncode, ended=time.time())

    def run_job_safely(self, job: dict) -> None:
        # One job's problem must not stop the whole run
        try:
            self.run_job(job)
        except Exception:
            self.log_error(f"Job {job['id']} failed in the supervisor:\n{traceback.format_exc()}")
            try:
                self.update(job, status="failed", ended=time.time())
            except Exception:
                self.log_error(traceback.format_exc())

    def run_all(self, max_processes: int) -> None:
        with ThreadPoolExecutor(max_processes) as pool:
            list(pool.map(self.run_job_safely, self.state["jobs"]))
        summary = []
        for job in self.state["jobs"]:
            log = self.run_directory / job["log"]
            if log.exists():
                summary.extend(summarise(log))
        (self.run_directory / "summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
        self.state["ended"] = time.time()
        self.save()
        (self.run_directory / "done").write_text("done", encoding="utf-8")


def failures(text: str) -> list[dict]:
    result = []
    for block in re.split(r"^={70}$", text, flags=re.M):
        # Master Tests states have absolute paths, the ones of `tests/states/` relative ones
        state = re.search(r"State File: (?:.*Master Tests[\\/])?(.*)$", block, re.M)
        errors = re.findall(r"^[A-Za-z_.]*(?:Error|Exception): .*$", block, re.M)
        if state:
            message = errors[-1] if errors else "?"
            message = re.sub(r"AssertionError: A timeout of \d+ frames has been reached\.", "Timeout", message)
            result.append({"state": state.group(1), "error": message})
    return result


def summarise(log: Path) -> list[str]:
    text = log.read_text(encoding="utf-8", errors="replace")
    ran = re.findall(r"^Ran .*$", text, re.M)
    result = [line for line in text.splitlines() if line.startswith(("OK", "FAILED"))]
    lines = [f"{log.stem}: {ran[-1] if ran else 'no result'} -> {result[-1] if result else 'did not finish'}"]
    lines.extend(f"  {failure['state']} => {failure['error']}" for failure in failures(text))
    skipped = {}
    # unittest quotes the reason with double quotes when it contains an apostrophe
    for _, reason in re.findall(r"skipped (['\"])(.*)\1$", text, re.M):
        skipped[reason] = skipped.get(reason, 0) + 1
    lines.extend(f"  skipped x{count}: {reason}" for reason, count in sorted(skipped.items()))
    return lines


def start(name: str, modules: list[str], languages: list[str], max_processes: int) -> Path:
    master_tests_path()
    run_directory = LOGS / name
    run_directory.mkdir(parents=True, exist_ok=True)
    for old_file in run_directory.glob("*"):
        old_file.unlink()
    subprocess.Popen(
        [
            sys.executable,
            __file__,
            "--supervise",
            str(run_directory),
            ",".join(languages),
            str(max_processes),
            *modules,
        ],
        creationflags=DETACHED,
        start_new_session=sys.platform != "win32",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )
    return run_directory


def main() -> None:
    arguments = sys.argv[1:]
    if arguments and arguments[0] == "--supervise":
        run_directory, languages, max_processes, *modules = arguments[1:]
        try:
            Run(Path(run_directory), modules, languages.split(",")).run_all(int(max_processes))
        except Exception:
            with open(Path(run_directory) / "supervisor.log", "a", encoding="utf-8") as handle:
                handle.write(f"[{time.strftime('%H:%M:%S')}] Supervisor crashed:\n{traceback.format_exc()}\n")
            raise
        return

    languages = None
    max_processes = recommended_processes()
    positional = []
    index = 0
    while index < len(arguments):
        if arguments[index] == "--languages":
            languages = arguments[index + 1].split(",")
            index += 2
        elif arguments[index] == "--max-processes":
            max_processes = int(arguments[index + 1])
            index += 2
        else:
            positional.append(arguments[index])
            index += 1
    if len(positional) < 2:
        print(__doc__)
        sys.exit(1)
    run_directory = start(positional[0], positional[1:], languages or available_languages(), max_processes)
    print(f"Started, results in {run_directory}")


if __name__ == "__main__":
    main()
