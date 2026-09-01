/* People's Slicer Studio — thin client over local forge APIs */
(function () {
  const state = {
    step: 1,
    file: null,
    fileName: "",
    gcodePath: "",
    printers: [],
  };

  const $ = (id) => document.getElementById(id);
  const logEl = (id, msg) => {
    const el = $(id);
    if (!el) return;
    const t = new Date().toLocaleTimeString();
    el.textContent += (el.textContent ? "\n" : "") + `[${t}] ${msg}`;
    el.scrollTop = el.scrollHeight;
  };

  function go(step) {
    state.step = step;
    document.querySelectorAll(".panel").forEach((p) => {
      p.hidden = String(p.dataset.panel) !== String(step);
    });
    document.querySelectorAll(".step").forEach((b) => {
      const n = Number(b.dataset.step);
      b.classList.toggle("is-active", n === step);
      b.classList.toggle("is-done", n < step);
    });
  }

  async function loadHealth() {
    try {
      const r = await fetch("/api/health");
      const d = await r.json();
      $("health").textContent = d.ok ? `${d.product} v${d.version}` : "offline";
      $("footVer").textContent = d.version ? `v${d.version}` : "";
    } catch {
      $("health").textContent = "studio offline";
    }
  }

  async function loadPrinters() {
    const r = await fetch("/api/printers");
    const d = await r.json();
    state.printers = d.printers || [];
    const sel = $("printer");
    const options = state.printers.map((p) => {
      const option = document.createElement("option");
      option.value = String(p.key || "");
      option.textContent = `${p.display_name} · ${p.bed_xy_mm}×${p.bed_z_mm} mm · ${p.backend}`;
      return option;
    });
    sel.replaceChildren(...options);
  }

  async function loadCheat() {
    try {
      const r = await fetch("/api/cheatsheet");
      const d = await r.json();
      $("cheatsheet").textContent = (d.commands || []).join("\n");
    } catch {
      $("cheatsheet").textContent = "forge slice model.stl --printer a1mini --dry-run";
    }
  }

  function setFile(file) {
    if (!file) return;
    state.file = file;
    state.fileName = file.name;
    const chip = $("fileChip");
    chip.hidden = false;
    chip.textContent = `Selected · ${file.name} · ${(file.size / 1024).toFixed(1)} KB`;
    $("btnHuman").disabled = false;
  }

  function wireDrop() {
    const zone = $("dropzone");
    const input = $("fileInput");
    zone.addEventListener("click", () => input.click());
    zone.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        input.click();
      }
    });
    input.addEventListener("change", () => setFile(input.files && input.files[0]));
    ["dragenter", "dragover"].forEach((ev) => {
      zone.addEventListener(ev, (e) => {
        e.preventDefault();
        zone.classList.add("is-hot");
      });
    });
    ["dragleave", "drop"].forEach((ev) => {
      zone.addEventListener(ev, (e) => {
        e.preventDefault();
        zone.classList.remove("is-hot");
      });
    });
    zone.addEventListener("drop", (e) => {
      const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      setFile(f);
    });
  }

  async function doSlice() {
    if (!state.file) {
      alert("Choose a model first.");
      go(1);
      return;
    }
    $("sliceLog").textContent = "";
    $("sliceResult").hidden = true;
    logEl("sliceLog", `Uploading ${state.fileName}…`);
    const fd = new FormData();
    fd.append("file", state.file, state.fileName);
    fd.append("filename", state.fileName);
    fd.append("printer", $("printer").value);
    fd.append("dry_run", $("dryRun").checked ? "true" : "false");
    fd.append("auto_refit", $("autoRefit").checked ? "true" : "false");

    logEl("sliceLog", "Slicing (this can take a minute)…");
    let d;
    try {
      const r = await fetch("/api/upload-slice", { method: "POST", body: fd });
      d = await r.json();
    } catch (e) {
      logEl("sliceLog", `Network error: ${e.message || e}`);
      return;
    }
    if (!d.ok) {
      logEl("sliceLog", `FAILED: ${d.error || "unknown"}`);
      const box = $("sliceResult");
      box.hidden = false;
      box.className = "result is-bad";
      box.innerHTML = `<h3>Slice failed</h3><p>${esc(d.error || "error")}</p>
        <p>Check BambuStudio/Orca profiles (BAMBU_PROFILES / ORCA_PROFILES) and xvfb.</p>`;
      return;
    }
    logEl("sliceLog", `OK · printer=${d.printer} backend=${d.backend}`);
    if (d.output) {
      state.gcodePath = d.output;
      $("gcodePath").value = d.output;
      logEl("sliceLog", `output: ${d.output}`);
    }
    if (d.detail) logEl("sliceLog", `detail: ${d.detail}`);
    if (d.scale != null) logEl("sliceLog", `scale: ${d.scale}`);
    const box = $("sliceResult");
    box.hidden = false;
    box.className = "result is-ok";
    box.innerHTML = `<h3>${d.dry_run ? "Dry-run OK" : "Sliced"}</h3>
      <p><code>${esc(d.output || "(no output path — dry-run)")}</code></p>
      <p>${d.dry_run ? "Profiles + fit check passed. Uncheck dry-run to write gcode." : "Ready for review &amp; send."}</p>
      <button type="button" class="btn btn--primary" id="btnToSend">Continue to send →</button>`;
    $("btnToSend").onclick = () => go(3);
  }

  async function doReview() {
    const path = $("gcodePath").value.trim();
    if (!path) {
      alert("Need a sliced file path.");
      return;
    }
    $("sendLog").textContent = "";
    logEl("sendLog", `Reviewing ${path}…`);
    const r = await fetch("/api/review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, printer: $("printer").value }),
    });
    const d = await r.json();
    const box = $("reviewResult");
    box.hidden = false;
    if (!d.ok && d.blocking) {
      box.className = "result is-bad";
      logEl("sendLog", "Review BLOCKING issues found.");
    } else {
      box.className = "result is-ok";
      logEl("sendLog", "Review complete.");
    }
    const rep = d.report || d;
    box.innerHTML = `<h3>${d.blocking ? "Needs attention" : "Looks good"}</h3>
      <pre style="font-family:var(--font-mono);font-size:0.75rem;white-space:pre-wrap;margin:0">${esc(
        JSON.stringify(rep, null, 2)
      )}</pre>`;
  }

  async function doSend(dry) {
    const path = $("gcodePath").value.trim();
    if (!path) {
      alert("Need a sliced file path.");
      return;
    }
    if (!dry && !$("bedClear").checked) {
      alert("Confirm the bed is clear first.");
      return;
    }
    logEl("sendLog", dry ? "Dry-run send…" : "Live send…");
    const r = await fetch("/api/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        path,
        dry_run: dry,
        bed_confirmed: !dry && $("bedClear").checked,
      }),
    });
    const d = await r.json();
    logEl("sendLog", d.ok ? `OK: ${JSON.stringify(d.result || d)}` : `FAILED: ${d.error || JSON.stringify(d)}`);
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function wire() {
    document.querySelectorAll(".step").forEach((b) => {
      b.addEventListener("click", () => go(Number(b.dataset.step)));
    });
    document.querySelectorAll("[data-goto]").forEach((b) => {
      b.addEventListener("click", () => go(Number(b.getAttribute("data-goto"))));
    });
    $("btnHuman").addEventListener("click", () => go(2));
    $("btnSlice").addEventListener("click", doSlice);
    $("btnReview").addEventListener("click", doReview);
    $("btnSendDry").addEventListener("click", () => doSend(true));
    $("btnSendLive").addEventListener("click", () => doSend(false));
    $("bedClear").addEventListener("change", () => {
      $("btnSendLive").disabled = !$("bedClear").checked;
    });
    wireDrop();
  }

  document.addEventListener("DOMContentLoaded", () => {
    wire();
    loadHealth();
    loadPrinters().catch((e) => logEl("sliceLog", String(e)));
    loadCheat();
    go(1);
  });
})();
