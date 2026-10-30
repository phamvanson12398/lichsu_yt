"use strict";
// Giao diện web cho tool video lịch sử. Không dùng thư viện ngoài.

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const view = $("#view");

const LANGS = { vi: "Tiếng Việt", en: "English", ko: "한국어", ja: "日本語" };
const QUALITIES = [
  ["chuan", "Chuẩn 1080p", "Khuyên dùng"],
  ["cao", "Cao 1440p", "Nét hơn, dựng lâu ~2×"],
  ["4k", "4K", "Nét nhất, rất lâu"],
  ["nhap", "Nháp 540p", "Xem thử nhanh"],
];
const STEPS = [
  ["parsed", "Chủ đề", "Phân tích đầu vào"],
  ["script", "Kịch bản", "AI viết + ghi chú nguồn"],
  ["plan", "Kế hoạch dựng", "Chia cảnh, chọn hình"],
  ["voice", "Giọng đọc", "OmniVoice"],
  ["render", "Video", "Dựng hình + âm thanh"],
];
const COUNTRY = { vietnam: "Việt Nam", korea: "Hàn Quốc", japan: "Nhật Bản", england: "Anh" };

// ------------------------------------------------------------------ gọi máy chủ
async function api(path, opts = {}) {
  const o = { ...opts, headers: { ...(opts.headers || {}) } };
  if (o.json !== undefined) {
    o.body = JSON.stringify(o.json);
    o.headers["Content-Type"] = "application/json";
    delete o.json;
  }
  const r = await fetch(path, o);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || `Lỗi ${r.status}`);
  return data;
}

function toast(msg, isErr = false) {
  const t = document.createElement("div");
  t.className = "toast" + (isErr ? " err" : "");
  t.textContent = msg;
  $("#toasts").appendChild(t);
  setTimeout(() => t.remove(), isErr ? 7000 : 3500);
}

async function act(fn, okMsg) {
  try {
    const r = await fn();
    if (okMsg) toast(okMsg);
    return r;
  } catch (e) {
    toast(e.message, true);
  }
}

// ------------------------------------------------------------------ bảng nhật ký (việc đang chạy)
const dock = { job: null, since: 0, timer: null, onDone: null };

function watchJob(id, title, onDone) {
  clearTimeout(dock.timer);
  dock.job = id;
  dock.since = 0;
  dock.onDone = onDone;
  const d = $("#dock");
  d.classList.remove("hidden", "finished", "failed", "min");
  $("#dock-title").textContent = title || "Đang chạy";
  $("#dock-log").textContent = "";
  $("#dock-stop").disabled = false;
  pollJob();
}

async function pollJob() {
  if (!dock.job) return;
  let j;
  try {
    j = await api(`/api/jobs/${dock.job}?since=${dock.since}`);
  } catch (e) {
    dock.timer = setTimeout(pollJob, 2000);
    return;
  }
  const log = $("#dock-log");
  const atBottom = log.scrollTop + log.clientHeight >= log.scrollHeight - 30;
  if (j.lines.length) {
    log.textContent += j.lines.join("\n") + "\n";
    dock.since = j.total;
    if (atBottom) log.scrollTop = log.scrollHeight;
  }
  if (j.running) {
    dock.timer = setTimeout(pollJob, 800);
  } else {
    const ok = j.rc === 0;
    $("#dock").classList.add(ok ? "finished" : "failed");
    $("#dock-title").textContent = (ok ? "✔ Xong: " : "✖ Lỗi: ") + j.title;
    $("#dock-stop").disabled = true;
    toast(ok ? `Xong: ${j.title}` : `Có lỗi: ${j.title} — xem nhật ký`, !ok);
    if (ok) setTimeout(() => { if (!dock.job) { $("#dock").classList.add("min"); $("#dock-toggle").textContent = "Mở rộng"; } }, 4000);
    const cb = dock.onDone;
    dock.job = null;
    if (cb) cb(ok);
    else if (location.hash === "" || location.hash === "#/") route();
  }
}

$("#dock-stop").onclick = () => dock.job && act(() => api(`/api/jobs/${dock.job}/stop`, { method: "POST" }), "Đã gửi lệnh dừng");
$("#dock-toggle").onclick = () => {
  $("#dock").classList.toggle("min");
  $("#dock-toggle").textContent = $("#dock").classList.contains("min") ? "Mở rộng" : "Thu gọn";
};
$("#dock-close").onclick = () => $("#dock").classList.add("hidden");
$("#btn-demo").onclick = async () => {
  const r = await act(() => api("/api/demo", { method: "POST" }));
  if (r) watchJob(r.job, "Video mẫu Bạch Đằng 938", () => (location.hash = "#/p/demo_bach_dang_938"));
};
$("#btn-check").onclick = async () => {
  const r = await act(() => api("/api/check", { method: "POST" }));
  if (r) watchJob(r.job, "Kiểm tra máy");
};

function lightbox(src) {
  const lb = document.createElement("div");
  lb.className = "lightbox";
  lb.innerHTML = `<img src="${esc(src)}">`;
  lb.onclick = () => lb.remove();
  document.body.appendChild(lb);
}

function choiceGroup(el, items, value, onChange) {
  el.innerHTML = items.map(([v, t, s]) => `<div class="choice${v === value ? " on" : ""}" data-v="${esc(v)}"><b>${esc(t)}</b>${s ? `<small>${esc(s)}</small>` : ""}</div>`).join("");
  $$(".choice", el).forEach((c) =>
    (c.onclick = () => {
      $$(".choice", el).forEach((x) => x.classList.remove("on"));
      c.classList.add("on");
      onChange(c.dataset.v);
    }));
}

// ------------------------------------------------------------------ trang: danh sách dự án
async function pageHome() {
  view.innerHTML = `
    <section class="hero">
      <h1>Xưởng video lịch sử</h1>
      <p>Gõ một dòng chủ đề — AI viết kịch bản kèm nguồn, tool tự vẽ cảnh, bản đồ động, nhạc nền và dựng thành video cho YouTube.</p>
      <div class="row"><a href="#/new"><button>＋ Tạo video mới</button></a>
      <button class="ghost" id="h-demo">▶ Xem thử video mẫu</button></div>
    </section>
    <div class="head"><h2>Dự án của bạn</h2><span class="grow"></span><button class="ghost small" id="refresh">↻ Làm mới</button></div>
    <div class="projects" id="plist"><div class="muted">Đang tải…</div></div>`;
  $("#h-demo").onclick = () => $("#btn-demo").click();
  $("#refresh").onclick = pageHome;
  const ps = await act(() => api("/api/projects"));
  if (!ps) return;
  const el = $("#plist");
  if (!ps.length) {
    el.innerHTML = `<div class="card empty-state" style="grid-column:1/-1"><b>Chưa có dự án nào</b>Bấm "Tạo video mới" để bắt đầu, hoặc làm video mẫu 30 giây để thử máy.</div>`;
    return;
  }
  el.innerHTML = ps.map((p) => {
    const thumb = p.preview ? `style="background-image:url('/files/projects/${encodeURIComponent(p.name)}/output/preview.jpg?t=${p.mtime}')"` : "";
    const nDone = STEPS.filter(([k]) => p.done.includes(k)).length;
    const status = p.busy ? `<span class="chip gold pulse">Đang chạy</span>`
      : p.videos.includes("video_final.mp4") ? `<span class="chip green">Có video</span>`
      : `<span class="chip">Bước ${Math.min(nDone + 1, 5)}/5</span>`;
    return `<a class="pcard" href="#/p/${encodeURIComponent(p.name)}">
      <div class="thumb ${p.preview ? "poster" : "empty"}" ${thumb}>${p.preview ? "" : "史"}<span class="badge">${status}</span></div>
      <div class="body">
        <h3>${esc(p.title)}</h3>
        <div class="row">
          <span class="chip">${esc(LANGS[p.language] || p.language)}</span>
          ${p.minutes ? `<span class="chip">${esc(p.minutes)} phút</span>` : ""}
          ${p.country ? `<span class="chip">${esc(COUNTRY[p.country] || p.country)}</span>` : ""}
          ${p.scenes ? `<span class="chip">${p.scenes} cảnh</span>` : ""}
        </div>
        <div class="dots">${STEPS.map(([k]) => `<span class="${p.done.includes(k) ? "on" : ""}"></span>`).join("")}</div>
      </div></a>`;
  }).join("");
}

// ------------------------------------------------------------------ trang: tạo video mới
function pageNew() {
  const st = { lang: "vi", quality: "chuan", review: "1" };
  view.innerHTML = `
    <div class="head"><div><h1>Tạo video mới</h1><small>Một dòng chủ đề là đủ. Tool tự nhận nước, thời kỳ.</small></div></div>
    <div class="card">
      <div class="field"><label>Chủ đề</label>
        <input id="topic" placeholder="vd: Trận Bạch Đằng năm 938 · Trận Hansan năm 1592 · Trận Hastings năm 1066" autofocus></div>
      <div class="grid2">
        <div class="field"><label>Thời lượng (phút)</label><input id="minutes" type="number" min="1" max="60" value="10"></div>
        <div class="field"><label>Khi AI hết lượt / không có AI</label>
          <select id="offline"><option value="">Dùng AI (claude / agy)</option><option value="1">Không dùng AI để lập plan (cần tự có script.md)</option></select></div>
      </div>
      <div class="field"><label>Ngôn ngữ lời kể</label><div class="choices" id="c-lang"></div></div>
      <div class="field"><label>Độ nét video</label><div class="choices" id="c-q"></div></div>
      <div class="field"><label>Cách chạy</label><div class="choices" id="c-review"></div></div>
      <div class="row"><button id="go">✦ Bắt đầu</button><small class="muted">Video 10 phút: viết kịch bản vài phút, dựng hình khoảng 30 phút (1080p).</small></div>
    </div>`;
  choiceGroup($("#c-lang"), Object.entries(LANGS).map(([k, v]) => [k, v, k === "vi" ? "Mặc định" : ""]), st.lang, (v) => (st.lang = v));
  choiceGroup($("#c-q"), QUALITIES, st.quality, (v) => (st.quality = v));
  choiceGroup($("#c-review"), [["1", "Dừng để duyệt", "Xem / sửa kịch bản và kế hoạch trước"], ["0", "Chạy hết một mạch", "Không dừng"]], st.review, (v) => (st.review = v));
  $("#topic").onkeydown = (e) => e.key === "Enter" && $("#go").click();
  $("#go").onclick = async () => {
    const topic = $("#topic").value.trim();
    if (!topic) return toast("Nhập chủ đề trước đã", true);
    const r = await act(() => api("/api/projects", { method: "POST", json: {
      topic, minutes: $("#minutes").value, lang: st.lang, quality: st.quality, auto: st.review === "0", offline: !!$("#offline").value } }));
    if (!r) return;
    watchJob(r.job, `Tạo video: ${topic}`, () => location.hash === `#/p/${r.project}` && route());
    setTimeout(() => (location.hash = `#/p/${encodeURIComponent(r.project)}`), 1200);
  };
}

// ------------------------------------------------------------------ trang: chi tiết dự án
let projTab = "overview";

async function pageProject(name) {
  const p = await act(() => api(`/api/projects/${encodeURIComponent(name)}`));
  if (!p) return (view.innerHTML = `<div class="card empty-state"><b>Chưa có dự án “${esc(name)}”</b>Nếu vừa bấm tạo, đợi vài giây rồi làm mới.</div>`);
  const base = `/files/projects/${encodeURIComponent(name)}`;
  const t = Date.now();
  const nextIdx = STEPS.findIndex(([k]) => !p.done.includes(k));
  const running = p.jobs.find((j) => j.running);
  const q = localStorage.getItem("hvt_quality") || "chuan";
  view.innerHTML = `
    <div class="head">
      <div><small><a href="#/">← Dự án</a></small><h1>${esc(p.title)}</h1>
        <div class="row">
          <span class="chip">${esc(LANGS[p.language] || p.language)}</span>
          ${p.minutes ? `<span class="chip">${esc(p.minutes)} phút</span>` : ""}
          ${p.country ? `<span class="chip">${esc(COUNTRY[p.country] || p.country)}</span>` : ""}
          ${p.scenes ? `<span class="chip">${p.scenes} cảnh</span>` : ""}
          ${p.voice ? `<span class="chip gold">Giọng: ${esc(p.voice)}</span>` : ""}
          ${running ? `<span class="chip gold pulse">${esc(running.title)}</span>` : ""}
        </div></div>
    </div>
    <div class="steps">${STEPS.map(([k, n, s], i) => `<div class="step ${p.done.includes(k) ? "done" : ""} ${i === nextIdx ? "next" : ""}">
      <span class="n">${p.done.includes(k) ? "✓" : i + 1}</span><b>${n}</b><small>${s}</small></div>`).join("")}</div>
    <div class="card">
      <div class="row">
        <button id="a-continue" ${running ? "disabled" : ""}>▶ Chạy tiếp</button>
        <select id="a-q" style="width:auto">${QUALITIES.map(([v, l]) => `<option value="${v}" ${v === q ? "selected" : ""}>${l}</option>`).join("")}</select>
        <button class="ghost" data-a="render" ${running ? "disabled" : ""}>🎞 Dựng video</button>
        <button class="ghost" data-a="preview" ${running ? "disabled" : ""}>🖼 Xem trước</button>
        <button class="ghost" data-a="voice-gen" ${running ? "disabled" : ""}>🎙 Tạo giọng</button>
        <span class="grow"></span>
        <button class="ghost small" data-a="diversify" title="Đổi góc nhìn các cảnh lặp nhau, không cần AI, không đổi lời đọc" ${running ? "disabled" : ""}>🎨 Đa dạng cảnh</button>
        <button class="ghost small" data-a="plan" ${running ? "disabled" : ""}>Lập lại kế hoạch</button>
        <button class="ghost small" data-a="script" ${running ? "disabled" : ""}>Viết lại kịch bản</button>
        ${running ? `<button class="danger small" id="a-stop">⏹ Dừng</button>` : ""}
      </div>
      <small class="muted" style="display:block;margin-top:10px">“Chạy tiếp” làm các bước còn thiếu và dừng lại ở bước duyệt. Sửa kịch bản xong → “Lập lại kế hoạch”. Sửa kế hoạch xong → “Dựng video” (cảnh không đổi được giữ nguyên, rất nhanh). Thấy cảnh lặp nhau → “🎨 Đa dạng cảnh” rồi “Dựng video”.</small>
    </div>
    <div class="tabs" style="margin-top:22px">
      ${[["overview", "Tổng quan"], ["script", "Kịch bản"], ["plan", "Kế hoạch dựng"], ["youtube", "YouTube"], ["check", "Kiểm tra sự kiện"]]
        .map(([k, l]) => `<button data-tab="${k}" class="${projTab === k ? "active" : ""}">${l}</button>`).join("")}
    </div>
    <div id="tab"></div>`;

  $("#a-q").onchange = (e) => localStorage.setItem("hvt_quality", e.target.value);
  const run = async (action) => {
    const r = await act(() => api(`/api/projects/${encodeURIComponent(name)}/run`, { method: "POST", json: { action, quality: $("#a-q").value } }));
    if (r) {
      watchJob(r.job, `${action}: ${name}`, () => location.hash === `#/p/${encodeURIComponent(name)}` && pageProject(name));
      setTimeout(() => pageProject(name), 400);
    }
  };
  $("#a-continue").onclick = () => run("continue");
  $$("[data-a]").forEach((b) => (b.onclick = () => {
    if (b.dataset.a === "script" && !confirm("Viết lại kịch bản sẽ ghi đè script.md hiện tại. Tiếp tục?")) return;
    run(b.dataset.a);
  }));
  if (running) {
    $("#a-stop").onclick = () => act(() => api(`/api/jobs/${running.id}/stop`, { method: "POST" }), "Đã gửi lệnh dừng");
    if (dock.job !== running.id) watchJob(running.id, running.title, () => pageProject(name));
  }
  $$("[data-tab]").forEach((b) => (b.onclick = () => { projTab = b.dataset.tab; pageProject(name); }));

  const tab = $("#tab");
  const f = p.files;
  if (projTab === "overview") {
    const vid = p.videos[0];
    tab.innerHTML = `<div class="grid2">
      <div class="card"><h3>Video</h3>${vid ? `<video controls preload="metadata" src="${base}/output/${vid}?t=${t}"></video>
        <div class="row" style="margin-top:10px"><a href="${base}/output/${vid}" download><button class="ghost small">⬇ Tải ${esc(vid)}</button></a>
        ${f["phu_de.srt"] ? `<a href="${base}/output/phu_de.srt" download><button class="ghost small">⬇ Phụ đề .srt</button></a>` : ""}</div>`
        : `<div class="empty-state"><b>Chưa có video</b>Bấm “Chạy tiếp” để làm các bước còn lại.</div>`}</div>
      <div class="card"><h3>Ảnh xem trước các cảnh</h3>${p.preview ? `<img class="preview" src="${base}/output/preview.jpg?t=${t}">`
        : `<div class="empty-state"><b>Chưa có ảnh xem trước</b>Bấm “Xem trước” sau khi có kế hoạch dựng.</div>`}</div>
    </div>
    ${p.flagged.length ? `<div class="card"><h3>Câu nên nghe lại</h3><small>Máy nhận dạng thấy giọng đọc khác văn bản nhiều:</small><ul>${p.flagged.map((s) => `<li>${esc(s)}</li>`).join("")}</ul></div>` : ""}
    ${p.report && (p.report.errors.length || p.report.warnings.length) ? `<div class="card"><h3>Kiểm tra kế hoạch dựng</h3>${reportHtml(p.report)}</div>` : ""}`;
    const img = $("img.preview", tab);
    if (img) img.onclick = () => lightbox(img.src);
  } else if (projTab === "script" || projTab === "plan") {
    const fname = projTab === "script" ? "script.md" : "plan.json";
    const text = f[fname];
    tab.innerHTML = text == null ? `<div class="card empty-state"><b>Chưa có ${fname}</b>Bấm “Chạy tiếp” để AI tạo.</div>` : `
      <div class="card">
        <div class="row" style="margin-bottom:12px"><h3 style="margin:0">${fname}</h3><span class="grow"></span>
          ${fname === "plan.json" ? `<button class="ghost small" id="fmt">Căn lề JSON</button>` : ""}
          <button id="save">💾 Lưu</button></div>
        ${fname === "script.md" ? `<small class="muted">Sửa lời kể thoải mái. Giữ các dòng “## ” và “&lt;!-- mood: … --&gt;”. Phần sau “GHI CHÚ NGUỒN” không được đọc.</small>`
          : `<small class="muted">Toạ độ 0–1 theo khung hình. Lưu xong bấm “Dựng video” — chỉ cảnh đổi mới phải dựng lại.</small>`}
        <textarea class="code" id="editor" spellcheck="false" style="margin-top:10px">${esc(text)}</textarea>
      </div>
      ${fname === "plan.json" && p.report ? `<div class="card"><h3>Kiểm tra</h3>${reportHtml(p.report)}</div>` : ""}`;
    if (text != null) {
      const ed = $("#editor");
      ed.onkeydown = (e) => {
        if (e.key === "Tab") { e.preventDefault(); document.execCommand("insertText", false, "  "); }
        if ((e.ctrlKey || e.metaKey) && e.key === "s") { e.preventDefault(); $("#save").click(); }
      };
      $("#save").onclick = async () => {
        const ok = await act(() => api(`/api/projects/${encodeURIComponent(name)}/files/${fname}`, { method: "PUT", json: { text: ed.value } }), `Đã lưu ${fname}`);
        if (ok && fname === "plan.json") pageProject(name);
      };
      const fmt = $("#fmt");
      if (fmt) fmt.onclick = () => {
        try { ed.value = JSON.stringify(JSON.parse(ed.value), null, 2); } catch (e) { toast("JSON sai cú pháp: " + e.message, true); }
      };
    }
  } else if (projTab === "youtube") {
    const yt = f["youtube.txt"];
    tab.innerHTML = yt == null ? `<div class="card empty-state"><b>Chưa có youtube.txt</b>Có sau khi dựng video.</div>`
      : `<div class="card"><div class="row" style="margin-bottom:10px"><h3 style="margin:0">Tiêu đề, mô tả, tag gợi ý</h3><span class="grow"></span>
         <button class="ghost small" id="copy">📋 Sao chép tất cả</button></div><pre class="text">${esc(yt)}</pre></div>`;
    if (yt != null) $("#copy").onclick = () => navigator.clipboard.writeText(yt).then(() => toast("Đã sao chép"));
  } else if (projTab === "check") {
    tab.innerHTML = `<div class="card"><div class="row" style="margin-bottom:10px"><h3 style="margin:0">AI kiểm tra lại sự kiện (tham khảo)</h3>
      <span class="grow"></span><button class="ghost small" data-a2="check-facts">Kiểm tra lại</button></div>
      ${f["script_check.md"] ? `<pre class="text">${esc(f["script_check.md"])}</pre>` : `<div class="empty-state">Chưa có. Có sau bước viết kịch bản.</div>`}</div>`;
    $("[data-a2]").onclick = () => run("check-facts");
  }
}

function reportHtml(r) {
  if (!r.errors.length && !r.warnings.length) return `<div class="ok">✔ Kế hoạch dựng hợp lệ.</div>`;
  return `<ul class="report">${r.errors.map((e) => `<li class="err">✖ ${esc(e)}</li>`).join("")}${r.warnings.map((w) => `<li class="warn">⚠ ${esc(w)}</li>`).join("")}</ul>`;
}

// ------------------------------------------------------------------ trang: giọng đọc
let recorded = null;

async function pageVoices() {
  view.innerHTML = `
    <div class="head"><div><h1>Giọng đọc</h1><small>OmniVoice chạy trên máy bạn. Giọng thật của bạn cho kết quả tốt nhất.</small></div></div>
    <div class="grid2">
      <div class="card">
        <h3>Thêm giọng của tôi</h3>
        <div class="drop" id="drop">Kéo thả file ghi âm vào đây hoặc bấm để chọn<br><small>mp3 / m4a / wav — đọc rõ 10–30 giây, phòng yên tĩnh</small></div>
        <input type="file" id="file" accept="audio/*" class="hidden">
        <div class="row" style="margin:12px 0"><span class="muted">hoặc</span>
          <button class="ghost" id="rec"><span class="rec"></span> Ghi âm trực tiếp</button><span id="rec-info" class="muted"></span></div>
        <audio id="rec-play" controls class="hidden"></audio>
        <div class="grid2" style="margin-top:12px">
          <div class="field"><label>Tên giọng (không dấu)</label><input id="v-name" value="giong_cua_toi"></div>
          <div class="field"><label>Giọng nói tiếng</label><select id="v-lang">${Object.entries(LANGS).map(([k, v]) => `<option value="${k}">${v}</option>`).join("")}</select></div>
        </div>
        <div class="field"><label>Lời đã đọc trong file (để trống = máy tự nghe)</label><textarea id="v-text" rows="2"></textarea></div>
        <label style="display:flex;gap:10px;align-items:center;color:var(--text)"><input type="checkbox" id="v-consent" style="width:auto">
          Đây là giọng của tôi hoặc tôi đã được người này đồng ý</label>
        <div class="row" style="margin-top:14px"><button id="v-add">＋ Thêm giọng</button><span id="v-file" class="muted"></span></div>
        <small class="muted" style="display:block;margin-top:10px">Không nhân bản giọng người nổi tiếng. Mô hình OmniVoice có giấy phép CC-BY-NC (phi thương mại).</small>
      </div>
      <div class="card">
        <h3>Để AI thiết kế giọng</h3>
        <small class="muted">AI đề xuất 3 kiểu giọng hợp chủ đề, tool tạo thử và tự chọn bản đọc rõ nhất. Tiếng Việt có thể kém ổn định hơn giọng thật.</small>
        <div class="field" style="margin-top:12px"><label>Chủ đề</label><input id="d-topic" placeholder="vd: Trận Hansan năm 1592"></div>
        <div class="grid2"><div class="field"><label>Ngôn ngữ</label><select id="d-lang">${Object.entries(LANGS).map(([k, v]) => `<option value="${k}">${v}</option>`).join("")}</select></div>
          <div class="field"><label>Tên giọng</label><input id="d-name" placeholder="vd: giong_tram"></div></div>
        <button class="ghost" id="d-go">✦ Thiết kế giọng</button>
      </div>
    </div>
    <div class="head" style="margin-top:28px"><h2>Thư viện giọng</h2></div>
    <div class="grid2" id="vlist"><div class="muted">Đang tải…</div></div>`;

  let file = null;
  const setFile = (f) => {
    file = f;
    recorded = null;
    $("#v-file").textContent = f ? `Đã chọn: ${f.name}` : "";
  };
  const drop = $("#drop");
  drop.onclick = () => $("#file").click();
  $("#file").onchange = (e) => setFile(e.target.files[0]);
  drop.ondragover = (e) => { e.preventDefault(); drop.classList.add("over"); };
  drop.ondragleave = () => drop.classList.remove("over");
  drop.ondrop = (e) => { e.preventDefault(); drop.classList.remove("over"); setFile(e.dataTransfer.files[0]); };

  let mr = null, chunks = [], t0 = 0, tick = null;
  $("#rec").onclick = async () => {
    if (mr && mr.state === "recording") { mr.stop(); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mr = new MediaRecorder(stream);
      chunks = [];
      mr.ondataavailable = (e) => chunks.push(e.data);
      mr.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        clearInterval(tick);
        $("#rec").classList.remove("recording");
        $("#rec").innerHTML = `<span class="rec"></span> Ghi âm lại`;
        const blob = new Blob(chunks, { type: mr.mimeType || "audio/webm" });
        file = new File([blob], "ghi_am.webm", { type: blob.type });
        recorded = blob;
        $("#rec-play").src = URL.createObjectURL(blob);
        $("#rec-play").classList.remove("hidden");
        $("#v-file").textContent = "Đã ghi âm — nghe lại ở trên";
      };
      mr.start();
      t0 = Date.now();
      $("#rec").classList.add("recording");
      $("#rec").innerHTML = `<span class="rec"></span> Dừng ghi`;
      tick = setInterval(() => ($("#rec-info").textContent = `${Math.round((Date.now() - t0) / 1000)} giây — đọc 10–30 giây`), 300);
    } catch (e) {
      toast("Không mở được micro: " + e.message, true);
    }
  };

  $("#v-add").onclick = async () => {
    if (!file) return toast("Chọn file hoặc ghi âm trước đã", true);
    if (!$("#v-consent").checked) return toast("Cần tick ô xác nhận đồng ý", true);
    const name = $("#v-name").value.trim();
    if (!/^[\w.-]+$/.test(name)) return toast("Tên giọng chỉ dùng chữ không dấu, số, dấu gạch dưới", true);
    const qs = new URLSearchParams({ name, lang: $("#v-lang").value, text: $("#v-text").value.trim(), consent: "1", filename: file.name });
    const r = await act(() => api(`/api/voices/upload?${qs}`, { method: "POST", body: file, headers: { "Content-Type": "application/octet-stream" } }));
    if (r) watchJob(r.job, `Thêm giọng: ${name}`, () => location.hash === "#/voices" && pageVoices());
  };
  $("#d-go").onclick = async () => {
    const r = await act(() => api("/api/voices/auto", { method: "POST", json: { topic: $("#d-topic").value, lang: $("#d-lang").value, name: $("#d-name").value.trim() } }));
    if (r) watchJob(r.job, "Thiết kế giọng", () => location.hash === "#/voices" && pageVoices());
  };

  const data = await act(() => api("/api/voices"));
  if (!data) return;
  const el = $("#vlist");
  const d = data.defaults || {};
  if (!data.voices.length) {
    el.innerHTML = `<div class="card empty-state" style="grid-column:1/-1"><b>Chưa có giọng nào</b>Thêm giọng của bạn ở trên. Chưa có giọng thì video vẫn dựng được, chỉ không có lời đọc.</div>`;
    return;
  }
  el.innerHTML = data.voices.map((v) => {
    const forLangs = Object.entries(d.by_language || {}).filter(([, n]) => n === v._name).map(([l]) => LANGS[l] || l);
    const isDef = d.default === v._name;
    return `<div class="card"><div class="voice">
      <div class="av">${esc((v._name[0] || "?").toUpperCase())}</div>
      <div class="grow"><b>${esc(v._name)}</b> ${isDef ? `<span class="chip gold">Mặc định</span>` : ""} ${forLangs.map((l) => `<span class="chip gold">Mặc định ${esc(l)}</span>`).join(" ")}
        <div><small>${v.loai === "clone" ? "Giọng nhân bản" : "Giọng thiết kế"} · ${esc(LANGS[v.ngon_ngu] || v.ngon_ngu || "vi")}${v.instruct ? " · " + esc(v.instruct) : ""}</small></div></div></div>
      ${v.sample ? `<audio controls preload="none" src="/files/voices/${encodeURIComponent(v._name)}/sample.wav" style="margin-top:12px"></audio>` : ""}
      <div class="row" style="margin-top:12px">
        <button class="ghost small" data-def="${esc(v._name)}" data-lang="${esc(v.ngon_ngu || "vi")}">★ Đặt mặc định cho ${esc(LANGS[v.ngon_ngu] || "Tiếng Việt")}</button>
        <span class="grow"></span><button class="danger small" data-del="${esc(v._name)}">Xoá</button></div></div>`;
  }).join("");
  $$("[data-def]").forEach((b) => (b.onclick = async () => {
    await act(() => api("/api/voices/default", { method: "POST", json: { name: b.dataset.def, lang: b.dataset.lang === "vi" ? "" : b.dataset.lang } }), "Đã đặt giọng mặc định");
    pageVoices();
  }));
  $$("[data-del]").forEach((b) => (b.onclick = async () => {
    if (!confirm(`Xoá giọng "${b.dataset.del}"? Không khôi phục được.`)) return;
    await act(() => api(`/api/voices/${encodeURIComponent(b.dataset.del)}`, { method: "DELETE" }), "Đã xoá");
    pageVoices();
  }));
}

// ------------------------------------------------------------------ trang: cài đặt
async function pageSettings() {
  const c = await act(() => api("/api/config"));
  view.innerHTML = `
    <div class="head"><div><h1>Cài đặt</h1><small>Sửa trực tiếp config.yaml — chọn AI cho từng việc, ngôn ngữ mặc định, độ nét, âm thanh…</small></div>
      <span class="grow"></span><button class="ghost" id="chk">✓ Kiểm tra máy</button><button id="save">💾 Lưu</button></div>
    <div class="card"><textarea class="code" id="cfg" spellcheck="false">${esc(c ? c.text : "")}</textarea></div>`;
  $("#chk").onclick = () => $("#btn-check").click();
  $("#save").onclick = () => act(() => api("/api/config", { method: "PUT", json: { text: $("#cfg").value } }), "Đã lưu config.yaml");
}

// ------------------------------------------------------------------ định tuyến
function route() {
  const h = decodeURIComponent(location.hash.slice(1) || "/");
  const nav = h.startsWith("/new") ? "new" : h.startsWith("/voices") ? "voices" : h.startsWith("/settings") ? "settings" : "home";
  $$("nav a").forEach((a) => a.classList.toggle("active", a.dataset.nav === nav));
  window.scrollTo(0, 0);
  if (h.startsWith("/p/")) return pageProject(h.slice(3));
  if (h === "/new") return pageNew();
  if (h === "/voices") return pageVoices();
  if (h === "/settings") return pageSettings();
  return pageHome();
}
window.addEventListener("hashchange", () => { projTab = "overview"; route(); });

(async function init() {
  route();
  // nối lại với việc đang chạy (khi tải lại trang)
  try {
    const jobs = await api("/api/jobs");
    const r = jobs.find((j) => j.running);
    if (r) watchJob(r.id, r.title);
  } catch (e) { /* bỏ qua */ }
})();
