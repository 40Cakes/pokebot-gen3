const LANGUAGES = { DEU: "German", ESP: "Spanish", FRA: "French", ITA: "Italian", JPN: "Japanese", USA_EUR: "English" };
const STATUS = { queued: "Waiting", running: "Running", passed: "Passed", failed: "Failed", lost: "Lost", stopped: "Stopped", cancelled: "Cancelled" };
const state = { run: null, job: null, runs: [], meta: { modules: [], languages: [], max_processes: 8 }, formReady: false };

const escape = (text) => String(text ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const languageName = (code) => LANGUAGES[code] || code;
const testName = (module) => {
  const name = module.replace(/^test_(mode_)?/, "").replaceAll("_", " ");
  return name.charAt(0).toUpperCase() + name.slice(1);
};
const duration = (seconds) => {
  seconds = Math.max(0, Math.round(seconds || 0));
  const minutes = Math.floor(seconds / 60);
  return minutes ? `${minutes} min ${String(seconds % 60).padStart(2, "0")} s` : `${seconds} s`;
};
const when = (timestamp) => new Date(timestamp * 1000).toLocaleString([], { dateStyle: "short", timeStyle: "short" });
const defaultName = (prefix) => `${prefix}-${new Date().toISOString().slice(5, 16).replace(/[-:T]/g, "")}`;
const getJson = async (url) => (await fetch(url)).json();
const remember = (key, value) => { try { localStorage.setItem(key, value); } catch (error) {} };
const recall = (key) => { try { return localStorage.getItem(key); } catch (error) { return null; } };

/* Theme */
document.getElementById("theme").addEventListener("click", () => {
  const current = document.documentElement.dataset.theme
    || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  const next = current === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  remember("theme", next);
});

/* Processes: automatic (from this machine's CPU and free memory) until changed by hand */
const processes = document.getElementById("processes");
function showProcesses(value, automatic) {
  processes.value = Math.max(1, Math.min(64, value));
  document.getElementById("processes-label").textContent = automatic ? "Processes (auto)" : "Processes";
  document.getElementById("auto-processes").hidden = automatic;
}
function setProcesses(value) {
  showProcesses(value, false);
  remember("processes", processes.value);
}
document.getElementById("fewer").addEventListener("click", () => setProcesses(Number(processes.value) - 1));
document.getElementById("more").addEventListener("click", () => setProcesses(Number(processes.value) + 1));
document.getElementById("auto-processes").addEventListener("click", () => {
  try { localStorage.removeItem("processes"); } catch (error) {}
  showProcesses(state.meta.max_processes, true);
});

async function startRun(body) {
  const result = await (await fetch("/api/start", { method: "POST", body: JSON.stringify(body) })).json();
  if (result.error) return result.error;
  state.run = body.name;
  state.job = null;
  setTimeout(refresh, 800);
  return null;
}

document.getElementById("run-all").addEventListener("click", async () => {
  const error = await startRun({
    name: defaultName("all"),
    modules: state.meta.modules,
    languages: state.meta.languages,
    max_processes: Number(processes.value),
  });
  if (error) alert(error);
});

/* New run form */
function fillForm(fromRun) {
  const modules = new Set(fromRun ? fromRun.modules : []);
  const languages = new Set(fromRun ? fromRun.languages : state.meta.languages);
  document.getElementById("module-choices").innerHTML = state.meta.modules.map((m) =>
    `<label class="choice"><input type="checkbox" name="module" value="${escape(m)}" ${modules.has(m) ? "checked" : ""}><span>${escape(testName(m))}</span></label>`).join("");
  document.getElementById("language-choices").innerHTML = state.meta.languages.map((l) =>
    `<label class="choice"><input type="checkbox" name="language" value="${escape(l)}" ${languages.has(l) ? "checked" : ""}><span>${escape(languageName(l))}</span></label>`).join("");
  document.getElementById("run-name").value = fromRun ? fromRun.name : "";
  document.getElementById("run-name").placeholder = defaultName("run");
  document.getElementById("form-error").textContent = "";
}
function toggleAll(name) {
  const boxes = [...document.querySelectorAll(`input[name="${name}"]`)];
  const check = boxes.some((box) => !box.checked);
  boxes.forEach((box) => (box.checked = check));
}
document.getElementById("toggle-modules").addEventListener("click", () => toggleAll("module"));
document.getElementById("toggle-languages").addEventListener("click", () => toggleAll("language"));
document.getElementById("new-run").addEventListener("submit", async (event) => {
  event.preventDefault();
  const nameInput = document.getElementById("run-name");
  const error = await startRun({
    name: nameInput.value.trim() || nameInput.placeholder,
    modules: [...document.querySelectorAll('input[name="module"]:checked')].map((box) => box.value),
    languages: [...document.querySelectorAll('input[name="language"]:checked')].map((box) => box.value),
    max_processes: Number(processes.value),
  });
  document.getElementById("form-error").textContent = error || "";
  if (!error) nameInput.placeholder = defaultName("run");
});

/* Runs and the selected run */
function balls(job) {
  const done = job.progress.states;
  const queued = Math.max(0, job.progress.total - done.length);
  const html = done.map((s) => `<span class="ball ${s.status === "ok" ? "" : s.status}" title="${escape(s.name)}"></span>`);
  for (let i = 0; i < queued; i++) html.push('<span class="ball queued"></span>');
  if (!done.length && !queued && job.status === "running") html.push('<span class="ball running"></span>');
  return html.join("");
}

function counts(jobs) {
  const all = jobs.flatMap((job) => job.progress.states);
  return {
    pass: all.filter((s) => s.status === "ok").length,
    fail: all.filter((s) => s.status === "fail").length,
    skip: all.filter((s) => s.status === "skip").length,
  };
}

async function refreshRuns() {
  const data = await getJson("/api/runs");
  state.runs = data.runs;
  state.meta = data;
  const manual = Number(recall("processes"));
  showProcesses(manual || data.max_processes, !manual);
  if (!state.formReady) {
    fillForm(null);
    state.formReady = true;
  }
  const notice = document.getElementById("notice");
  notice.hidden = !data.error;
  notice.textContent = data.error || "";
  if (!state.run && data.runs.length) state.run = data.runs[0].name;
  document.getElementById("runs").innerHTML = data.runs.length
    ? data.runs.map((run) => {
        const total = Object.values(run.counts).reduce((a, b) => a + b, 0) || 1;
        const part = (status, color) => run.counts[status] ? `<span style="width:${(100 * run.counts[status]) / total}%;background:var(${color})"></span>` : "";
        return `<button class="run-item" data-run="${escape(run.name)}" aria-current="${run.name === state.run}">
          <span class="name">${escape(run.name)}</span>
          <span class="when">${run.done ? when(run.started) : "Running now"}</span>
          <span class="tally">${part("passed", "--pass")}${part("failed", "--fail")}${part("lost", "--fail")}${part("running", "--run")}</span>
        </button>`;
      }).join("")
    : '<div class="empty">No runs yet.</div>';
}

async function refreshRun() {
  if (!state.run) return;
  const run = await getJson(`/api/run?name=${encodeURIComponent(state.run)}`);
  if (run.error) {
    document.getElementById("run").innerHTML = `<div class="box empty">${escape(run.error)}</div>`;
    return;
  }
  const jobs = Object.fromEntries(run.jobs.map((job) => [job.id, job]));
  const tally = counts(run.jobs);
  const running = run.jobs.filter((job) => job.status === "running").length;
  const elapsed = (run.ended || run.now) - run.started;
  const status = run.done ? `Finished in ${duration(elapsed)}` : `${running} running, ${duration(elapsed)} so far`;

  let grid = `<table class="grid" style="min-width:${150 + run.languages.length * 130}px"><colgroup><col class="name">${run.languages.map(() => "<col>").join("")}</colgroup>`;
  grid += `<thead><tr><th></th>${run.languages.map((l) => `<th scope="col">${escape(languageName(l))}</th>`).join("")}</tr></thead><tbody>`;
  for (const module of run.modules) {
    grid += `<tr><th scope="row" title="${escape(module)}">${escape(testName(module))}</th>`;
    for (const language of run.languages) {
      const job = jobs[`${module}.${language}`];
      if (!job) {
        grid += '<td class="cell same"><div class="meta"><span>Runs once, no game state</span></div></td>';
        continue;
      }
      const p = job.progress;
      const finished = p.states.filter((s) => s.status !== "running").length;
      const current = p.states.find((s) => s.status === "running");
      grid += `<td class="cell ${job.status}" tabindex="0" data-job="${escape(job.id)}" aria-selected="${job.id === state.job}"
        title="${escape(current ? `Now: ${current.name}` : STATUS[job.status] || job.status)}">
        <div class="balls">${balls(job)}</div>
        <div class="meta"><span class="word">${STATUS[job.status] || job.status}</span><span>${p.total ? `${finished}/${p.total}` : ""}</span></div>
      </td>`;
    }
    grid += "</tr>";
  }
  grid += "</tbody></table>";

  const canStop = !run.done && run.supervisor_alive;
  document.getElementById("run").innerHTML = `
    <div class="run-head">
      <h2>${escape(run.name)}</h2>
      <span class="state">${status}</span>
      <span class="counts"><span class="pass">${tally.pass} passed</span><span class="fail">${tally.fail} failed</span><span class="skip">${tally.skip} skipped</span></span>
      <span class="actions">
        ${canStop ? '<button class="button danger" id="stop-run">Stop run</button>' : ""}
        <button class="button" id="run-again">Run again</button>
      </span>
    </div>
    <div class="box grid-wrap">${grid}</div>
    <div class="legend">
      <span><span class="ball"></span>Passed</span><span><span class="ball fail"></span>Failed</span>
      <span><span class="ball skip"></span>Skipped</span><span><span class="ball running"></span>Running</span>
      <span><span class="ball queued"></span>Waiting</span>
    </div>`;

  const failures = run.jobs.flatMap((job) => job.progress.failures.map((f) => ({ ...f, job: job.id })));
  document.getElementById("panels").hidden = false;
  document.getElementById("failures-title").textContent = failures.length ? `Failures (${failures.length})` : "Failures";
  document.getElementById("failures").innerHTML = failures.length
    ? failures.map((f) => `<button class="failure" data-job="${escape(f.job)}"><div class="state">${escape(f.state)}</div><div class="error">${escape(f.error)}</div></button>`).join("")
    : `<div class="empty">${run.done ? "Nothing failed." : "Nothing failed so far."}</div>`;
  await refreshOutput(state.job ? jobs[state.job] : null);
}

async function refreshOutput(job) {
  const log = document.getElementById("log");
  if (!job) {
    document.getElementById("output-title").textContent = "Output";
    document.getElementById("output-meta").textContent = "Pick a cell to see its output.";
    log.textContent = "";
    return;
  }
  const text = await (await fetch(`/api/log?run=${encodeURIComponent(state.run)}&job=${encodeURIComponent(job.id)}&lines=800`)).text();
  const atBottom = log.scrollTop + log.clientHeight >= log.scrollHeight - 30;
  const current = job.progress.states.find((s) => s.status === "running");
  document.getElementById("output-title").textContent = `${testName(job.module)}, ${languageName(job.language)}`;
  const parts = [STATUS[job.status] || job.status];
  if (job.started) parts.push(duration((job.ended || Date.now() / 1000) - job.started));
  if (current) parts.push(`now on ${current.name}`);
  document.getElementById("output-meta").textContent = parts.join(", ");
  if (log.dataset.job !== job.id || log.textContent !== text) {
    const switched = log.dataset.job !== job.id;
    log.dataset.job = job.id;
    log.textContent = text || "No output yet.";
    if (switched || (document.getElementById("follow").checked && atBottom)) log.scrollTop = log.scrollHeight;
  }
}

async function refresh() {
  try {
    await refreshRuns();
    await refreshRun();
  } catch (error) {
    const notice = document.getElementById("notice");
    notice.hidden = false;
    notice.textContent = `Can't reach the dashboard server (${error.message}). Is dashboard.py still running?`;
  }
}

document.addEventListener("click", async (event) => {
  const runButton = event.target.closest("[data-run]");
  if (runButton) { state.run = runButton.dataset.run; state.job = null; refresh(); return; }
  const jobElement = event.target.closest("[data-job]");
  if (jobElement) { state.job = jobElement.dataset.job; refresh(); return; }
  if (event.target.id === "stop-run" && confirm(`Stop ${state.run}? Its running processes will be killed.`)) {
    await fetch("/api/stop", { method: "POST", body: JSON.stringify({ name: state.run }) });
    refresh();
  }
  if (event.target.id === "run-again") {
    fillForm(await getJson(`/api/run?name=${encodeURIComponent(state.run)}`));
    document.getElementById("new-run").scrollIntoView({ behavior: "smooth" });
    document.getElementById("run-name").focus();
  }
});
document.addEventListener("keydown", (event) => {
  const cell = event.target.closest && event.target.closest("td.cell[data-job]");
  if (cell && (event.key === "Enter" || event.key === " ")) { event.preventDefault(); state.job = cell.dataset.job; refresh(); }
});

refresh();
setInterval(refresh, 2000);
