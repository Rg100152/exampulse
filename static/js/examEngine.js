/* ExamPulse 1000 - Live CBT engine
 * Timer, answer state, palette, review marks, keyboard shortcuts, auto-submit.
 */
(function () {
  "use strict";

  const boot = window.EXAM_BOOT;
  const shell = document.getElementById("examShell");
  if (!boot || !shell) return;

  const questions = boot.questions || [];
  const total = questions.length;
  const code = shell.dataset.code;
  const submitUrl = shell.dataset.submitUrl;
  const storageKey = "exampulse:attempt:" + code;
  const deadline = new Date(boot.deadline_at).getTime();
  const startedAt = new Date(boot.started_at).getTime();
  const durationMs = Math.max(1, (boot.duration_minutes || 15) * 60 * 1000);

  const $ = function (id) { return document.getElementById(id); };
  const difficultyClass = function (d) {
    return "d-" + String(d || "easy").toLowerCase();
  };

  function loadState() {
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey) || "null");
      if (saved && typeof saved === "object") {
        return {
          answers: saved.answers && typeof saved.answers === "object" ? saved.answers : {},
          marked: saved.marked && typeof saved.marked === "object" ? saved.marked : {},
          current: Number.isInteger(saved.current) ? Math.min(Math.max(saved.current, 0), Math.max(total - 1, 0)) : 0
        };
      }
    } catch (_err) { /* ignore corrupt local state */ }
    return { answers: {}, marked: {}, current: 0 };
  }

  const state = loadState();
  let submitting = false;
  let timerId = null;

  function persist() {
    try { localStorage.setItem(storageKey, JSON.stringify(state)); } catch (_err) { /* private mode */ }
  }

  function makeText(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function renderQuestion() {
    const q = questions[state.current];
    if (!q) return;

    $("qNumber").textContent = String(state.current + 1);
    $("qOutOf").textContent = "/ " + total;
    $("qText").textContent = q.question;

    const difficulty = $("qDifficulty");
    difficulty.textContent = q.difficulty;
    difficulty.className = "tag tag-difficulty " + difficultyClass(q.difficulty);
    $("qTopic").textContent = q.topic;
    $("qMarkedTag").hidden = !state.marked[q.id];

    const list = $("optionsList");
    list.innerHTML = "";
    ["A", "B", "C", "D"].forEach(function (letter) {
      const selected = state.answers[q.id] === letter;
      const button = makeText("button", "option-card" + (selected ? " selected" : ""));
      button.type = "button";
      button.setAttribute("role", "radio");
      button.setAttribute("aria-checked", selected ? "true" : "false");
      button.dataset.option = letter;

      button.appendChild(makeText("span", "option-letter", letter));
      button.appendChild(makeText("span", "option-radio"));
      button.appendChild(makeText("span", "option-text", q.options[letter]));
      button.appendChild(makeText("span", "option-check", "✓"));
      button.addEventListener("click", function () { choose(letter); });
      list.appendChild(button);
    });

    $("prevBtn").disabled = state.current === 0;
    $("saveNextBtn").textContent = state.current === total - 1 ? "Save & Submit →" : "Save & Next →";
    const mark = $("markBtn");
    mark.textContent = state.marked[q.id] ? "Remove Mark" : "Mark for Review";
    mark.classList.toggle("marked-active", !!state.marked[q.id]);
    renderPalette();
  }

  function renderPalette() {
    const grid = $("paletteGrid");
    grid.innerHTML = "";
    let answered = 0;
    let marked = 0;

    questions.forEach(function (q, index) {
      const isAnswered = !!state.answers[q.id];
      const isMarked = !!state.marked[q.id];
      if (isAnswered) answered += 1;
      if (isMarked) marked += 1;
      const classes = ["palette-btn"];
      classes.push(isAnswered ? "answered" : "unanswered");
      if (isMarked) classes.push("marked");
      if (index === state.current) classes.push("current");
      const button = makeText("button", classes.join(" "), String(index + 1));
      button.type = "button";
      button.title = "Question " + (index + 1) + (isMarked ? " - marked for review" : "");
      button.setAttribute("aria-label", button.title);
      button.addEventListener("click", function () { goto(index); });
      grid.appendChild(button);
    });

    $("statAnswered").textContent = String(answered);
    $("statMarked").textContent = String(marked);
    $("statLeft").textContent = String(total - answered);
    $("paletteProgress").textContent = answered + "/" + total;
  }

  function goto(index) {
    if (index < 0 || index >= total) return;
    state.current = index;
    persist();
    renderQuestion();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function choose(letter) {
    const q = questions[state.current];
    if (!q) return;
    state.answers[q.id] = letter;
    persist();
    renderQuestion();
  }

  function clearResponse() {
    const q = questions[state.current];
    if (!q) return;
    delete state.answers[q.id];
    persist();
    renderQuestion();
  }

  function toggleMark() {
    const q = questions[state.current];
    if (!q) return;
    if (state.marked[q.id]) delete state.marked[q.id];
    else state.marked[q.id] = true;
    persist();
    renderQuestion();
  }

  function saveAndNext() {
    if (state.current === total - 1) openConfirm();
    else goto(state.current + 1);
  }

  function elapsedSeconds() {
    const value = Math.floor((Date.now() - startedAt) / 1000);
    return Math.max(0, Math.min(value, Math.floor(durationMs / 1000)));
  }

  function formatTime(ms) {
    const seconds = Math.max(0, Math.floor(ms / 1000));
    const h = String(Math.floor(seconds / 3600)).padStart(2, "0");
    const m = String(Math.floor((seconds % 3600) / 60)).padStart(2, "0");
    const s = String(seconds % 60).padStart(2, "0");
    return h + ":" + m + ":" + s;
  }

  function tick() {
    const remaining = deadline - Date.now();
    $("timerValue").textContent = formatTime(remaining);
    $("timerBarFill").style.width = Math.max(0, Math.min(100, remaining / durationMs * 100)) + "%";
    $("timerCard").classList.toggle("urgent", remaining <= 60000);
    if (remaining <= 0) {
      if (timerId) window.clearInterval(timerId);
      hideConfirm();
      submitExam(true);
    }
  }

  function openConfirm() {
    const unanswered = total - Object.keys(state.answers).length;
    $("confirmText").textContent = unanswered
      ? "You have " + unanswered + " unanswered question(s). Your responses are graded instantly and the analytics report will open."
      : "All questions answered. Your responses are graded instantly and the analytics report will open.";
    $("confirmOverlay").hidden = false;
  }

  function hideConfirm() { $("confirmOverlay").hidden = true; }

  async function submitExam(automatic) {
    if (submitting) return;
    submitting = true;
    const buttons = document.querySelectorAll(".action-bar button, .btn-submit");
    buttons.forEach(function (b) { b.disabled = true; });
    const submitButton = $("confirmSubmit");
    if (submitButton) submitButton.textContent = "Grading…";

    try {
      const response = await fetch(submitUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "application/json" },
        body: JSON.stringify({
          answers: state.answers,
          elapsed_seconds: elapsedSeconds(),
          auto_submitted: !!automatic
        })
      });
      const result = await response.json();
      if (!response.ok || !result.success) throw new Error(result.error || "Submission failed");
      localStorage.removeItem(storageKey);
      window.location.href = result.result_url;
    } catch (error) {
      submitting = false;
      buttons.forEach(function (b) { b.disabled = false; });
      if (submitButton) submitButton.textContent = "Yes, submit exam";
      window.alert("Could not submit the exam: " + (error.message || "network error"));
    }
  }

  $("prevBtn").addEventListener("click", function () { goto(state.current - 1); });
  $("saveNextBtn").addEventListener("click", saveAndNext);
  $("clearBtn").addEventListener("click", clearResponse);
  $("markBtn").addEventListener("click", toggleMark);
  $("submitBtn").addEventListener("click", openConfirm);
  $("cancelSubmit").addEventListener("click", hideConfirm);
  $("confirmSubmit").addEventListener("click", function () { submitExam(false); });
  $("confirmOverlay").addEventListener("click", function (event) {
    if (event.target === $("confirmOverlay")) hideConfirm();
  });

  document.addEventListener("keydown", function (event) {
    if (submitting || !$("confirmOverlay").hidden) return;
    const tag = (event.target && event.target.tagName) || "";
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    const key = event.key;
    if (["1", "2", "3", "4"].indexOf(key) !== -1) {
      event.preventDefault();
      choose(["A", "B", "C", "D"][Number(key) - 1]);
    } else if (key === "ArrowRight") {
      event.preventDefault(); goto(state.current + 1);
    } else if (key === "ArrowLeft") {
      event.preventDefault(); goto(state.current - 1);
    } else if (key.toLowerCase() === "m") {
      event.preventDefault(); toggleMark();
    }
  });

  renderQuestion();
  tick();
  timerId = window.setInterval(tick, 1000);
})();
