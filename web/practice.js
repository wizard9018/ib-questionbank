/* 分章练习 —— 逐题过，答案默认收起，进度存本机 */
(function () {
  "use strict";

  const INDEX = window.RV_INDEX || [];
  window.RV_LOADED = window.RV_LOADED || {};

  /* ---------- Markdown + KaTeX ---------- */
  const inlineMath = {
    name: "inlineMath", level: "inline",
    start(src) { const i = src.indexOf("$"); return i < 0 ? undefined : i; },
    tokenizer(src) {
      const m = /^\$((?:\\.|[^$\\\n])+?)\$/.exec(src);
      if (m) return { type: "inlineMath", raw: m[0], text: m[1] };
      return undefined;
    },
    renderer(t) {
      try { return katex.renderToString(t.text, { throwOnError: false, displayMode: false }); }
      catch (e) { return '<code class="katex-err">' + esc(t.text) + "</code>"; }
    },
  };
  const blockMath = {
    name: "blockMath", level: "block",
    start(src) { const i = src.indexOf("$$"); return i < 0 ? undefined : i; },
    tokenizer(src) {
      const m = /^\$\$([\s\S]+?)\$\$[ \t]*(\n|$)/.exec(src);
      if (m) return { type: "blockMath", raw: m[0], text: m[1].trim() };
      return undefined;
    },
    renderer(t) {
      try {
        return '<div class="math-block">' +
          katex.renderToString(t.text, { throwOnError: false, displayMode: true }) + "</div>";
      } catch (e) { return "<pre>" + esc(t.text) + "</pre>"; }
    },
  };
  if (window.marked && window.katex) {
    marked.use({ extensions: [blockMath, inlineMath], gfm: true, breaks: false });
  }
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const md = (s) => (s ? marked.parse(s) : "");

  /* ---------- 进度存储 ---------- */
  const STORE_KEY = "ib-practice-v1";
  let store = { chapters: {}, last: null };
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (raw) store = Object.assign(store, JSON.parse(raw));
  } catch (e) { /* 忽略损坏数据 */ }

  function save() {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(store)); } catch (e) {}
  }
  const ckey = (slug, topic, sub) => slug + "||" + topic + "||" + sub;
  function chapterState(slug, topic, sub) {
    const k = ckey(slug, topic, sub);
    if (!store.chapters[k]) store.chapters[k] = { done: {}, flagged: {} };
    return store.chapters[k];
  }
  const isDone = (st, ref) => !!st.done[ref];
  const isFlagged = (st, ref) => !!st.flagged[ref];

  /* ---------- 元素 ---------- */
  const $ = (id) => document.getElementById(id);
  const viewHome = $("viewHome"), viewPractice = $("viewPractice"), viewDone = $("viewDone");
  const subjectBar = $("subjectBar"), chapterList = $("chapterList"), subjectName = $("subjectName");

  /* ---------- 视图切换 ---------- */
  function showView(v) {
    [viewHome, viewPractice, viewDone].forEach((x) => (x.hidden = x !== v));
    window.scrollTo(0, 0);
  }

  /* ---------- 科目 / 章节 ---------- */
  let activeSlug = INDEX.length ? INDEX[0].slug : null;
  let activeSubject = null;
  let session = null;   // {slug, subjectName, topic, sub, questions, idx, done[], flagged}

  function loadSubject(slug) {
    if (window.RV_LOADED[slug]) return Promise.resolve(window.RV_LOADED[slug]);
    return new Promise((res, rej) => {
      const s = document.createElement("script");
      s.src = "data/" + slug + ".js";
      s.onload = () => res(window.RV_LOADED[slug]);
      s.onerror = () => rej(new Error("加载失败：" + slug));
      document.head.appendChild(s);
    });
  }

  function renderSubjectBar() {
    subjectBar.innerHTML = "";
    INDEX.forEach((sub) => {
      const b = document.createElement("button");
      b.textContent = sub.name.replace(/^IB Mathematics\s+/, "Math ").replace(/^IB\s+/, "");
      b.className = sub.slug === activeSlug ? "active" : "";
      b.onclick = () => openSubject(sub.slug);
      subjectBar.appendChild(b);
    });
  }

  function openSubject(slug) {
    activeSlug = slug;
    renderSubjectBar();
    subjectName.textContent = "加载中…";
    chapterList.innerHTML = "";
    loadSubject(slug).then((subject) => {
      activeSubject = subject;
      subjectName.textContent = subject.name;
      renderChapters();
      updateContinueBtn();
    }).catch((e) => {
      subjectName.textContent = "加载失败";
      chapterList.innerHTML = '<p style="color:#a33">' + esc(e.message) + "</p>";
    });
  }

  function renderChapters() {
    chapterList.innerHTML = "";
    activeSubject.topics.forEach((topic) => {
      const block = document.createElement("div");
      block.className = "topic-block";
      const h = document.createElement("h3");
      h.textContent = topic.name;
      block.appendChild(h);

      const grid = document.createElement("div");
      grid.className = "chapters";
      topic.subtopics.forEach((st) => {
        const state = chapterState(activeSlug, topic.name, st.name);
        const total = st.questions.length;
        const doneN = st.questions.filter((q) => isDone(state, q.ref)).length;
        const pct = total ? (doneN / total) * 100 : 0;

        const btn = document.createElement("button");
        btn.className = "chapter" + (doneN === total && total > 0 ? " done" : "");
        btn.innerHTML =
          '<div class="chapter-main">' +
            '<div class="chapter-name">' + esc(st.name) + "</div>" +
            '<div class="chapter-meta">' +
              "<span>" + total + " 题</span>" +
              "<span>" + doneN + "/" + total + "</span>" +
              '<span class="mini-bar"><span class="mini-fill" style="width:' + pct + '%"></span></span>' +
            "</div>" +
          "</div>";
        btn.onclick = () => startChapter(topic.name, st.name, st.questions);
        grid.appendChild(btn);
      });
      block.appendChild(grid);
      chapterList.appendChild(block);
    });
  }

  function updateContinueBtn() {
    const btn = $("btnContinue");
    const last = store.last;
    if (!last || last.slug !== activeSlug) { btn.hidden = true; return; }
    const topic = activeSubject.topics.find((t) => t.name === last.topic);
    const st = topic && topic.subtopics.find((s) => s.name === last.sub);
    if (!st) { btn.hidden = true; return; }
    btn.hidden = false;
    btn.textContent = "继续：" + last.sub + "（第 " + (last.idx + 1) + " 题）";
    btn.onclick = () => startChapter(last.topic, last.sub, st.questions, last.idx);
  }

  /* ---------- 练习 ---------- */
  function startChapter(topicName, subName, allQuestions, startIdx) {
    const state = chapterState(activeSlug, topicName, subName);
    session = {
      topic: topicName, sub: subName,
      questions: allQuestions.slice(),
      idx: startIdx || 0,
      state,
    };
    $("chapterTitle").textContent = subName;
    $("chapterSub").textContent = activeSubject.name + " · " + topicName;
    showView(viewPractice);
    renderQuestion();
  }

  function startRandom(n) {
    const pool = [];
    activeSubject.topics.forEach((t) =>
      t.subtopics.forEach((s) => s.questions.forEach((q) =>
        pool.push({ q, topic: t.name, sub: s.name }))));
    for (let i = pool.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [pool[i], pool[j]] = [pool[j], pool[i]];
    }
    const picked = pool.slice(0, Math.min(n, pool.length));
    session = {
      topic: picked[0] ? picked[0].topic : "",
      sub: "随机 " + picked.length + " 题",
      questions: picked.map((p) => p.q),
      idx: 0,
      state: { done: {}, flagged: {} },
      random: true,
    };
    $("chapterTitle").textContent = session.sub;
    $("chapterSub").textContent = activeSubject.name + " · 混合练习";
    showView(viewPractice);
    renderQuestion();
  }

  function renderQuestion() {
    const q = session.questions[session.idx];
    if (!q) return finishChapter();

    $("qref").textContent = q.ref;
    const chips = [];
    if (q.marks) chips.push('<span class="chip marks">' + esc(q.marks) + " marks</span>");
    if (q.difficulty) chips.push('<span class="chip ' + esc(q.difficulty) + '">' + esc(q.difficulty) + "</span>");
    if (q.paper) chips.push('<span class="chip">' + esc(q.paper) + "</span>");
    if (q.calculator) chips.push('<span class="chip">GDC</span>');
    $("qchips").innerHTML = chips.join("");

    $("qbody").innerHTML = md(q.body);
    $("abody").innerHTML = q.markScheme ? md(q.markScheme) : '<p style="color:#888">这题没有评分标准</p>';

    // 答案默认收起
    $("answerCard").hidden = true;
    $("btnReveal").hidden = false;

    const n = session.questions.length;
    $("counter").textContent = (session.idx + 1) + " / " + n;
    $("progressFill").style.width = ((session.idx + 1) / n * 100) + "%";
    $("btnPrev").disabled = session.idx === 0;
    $("btnNext").textContent = session.idx === n - 1 ? "完成本章" : "下一题";

    const flagged = isFlagged(session.state, q.ref);
    $("btnFlag").classList.toggle("on", flagged);
    $("btnFlag").textContent = flagged ? "已标记复习" : "标记复习";

    // 记录位置
    if (!session.random) {
      store.last = { slug: activeSlug, topic: session.topic, sub: session.sub, idx: session.idx };
      save();
    }
  }

  function reveal() {
    const q = session.questions[session.idx];
    $("answerCard").hidden = false;
    $("btnReveal").hidden = true;
    if (q && !session.random) {
      session.state.done[q.ref] = 1;   // 看过答案就算做过
      save();
    }
  }

  function go(delta) {
    const next = session.idx + delta;
    if (next < 0) return;
    if (next >= session.questions.length) return finishChapter();
    session.idx = next;
    renderQuestion();
  }

  function toggleFlag() {
    const q = session.questions[session.idx];
    if (!q) return;
    if (isFlagged(session.state, q.ref)) delete session.state.flagged[q.ref];
    else session.state.flagged[q.ref] = 1;
    if (!session.random) save();
    const flagged = isFlagged(session.state, q.ref);
    $("btnFlag").classList.toggle("on", flagged);
    $("btnFlag").textContent = flagged ? "标记复习" : "标记复习";
    $("btnFlag").textContent = flagged ? "已标记复习" : "标记复习";
  }

  function finishChapter() {
    if (session.random) { showView(viewHome); renderChapters(); return; }
    const total = session.questions.length;
    const doneN = session.questions.filter((q) => isDone(session.state, q.ref)).length;
    const flaggedN = session.questions.filter((q) => isFlagged(session.state, q.ref)).length;

    $("doneTitle").textContent = session.sub;
    $("doneStat").textContent =
      "本章 " + total + " 题，已看答案 " + doneN + " 题" +
      (flaggedN ? "，标记复习 " + flaggedN + " 题" : "");
    $("flaggedCount").textContent = flaggedN ? "(" + flaggedN + ")" : "";
    $("btnRedoFlagged").hidden = flaggedN === 0;
    showView(viewDone);
    renderChapters();
    updateContinueBtn();
  }

  /* ---------- 事件 ---------- */
  $("btnBack").onclick = () => { showView(viewHome); renderChapters(); updateContinueBtn(); };
  $("btnPrev").onclick = () => go(-1);
  $("btnNext").onclick = () => go(1);
  $("btnReveal").onclick = reveal;
  $("btnFlag").onclick = toggleFlag;
  $("btnRandom").onclick = () => startRandom(20);
  $("btnDoneBack").onclick = () => { showView(viewHome); renderChapters(); updateContinueBtn(); };

  $("btnRestart").onclick = () => {
    const st = chapterState(activeSlug, session.topic, session.sub);
    st.done = {}; st.flagged = {};
    save();
    startChapter(session.topic, session.sub, session.questions);
  };

  $("btnRedoFlagged").onclick = () => {
    const flagged = session.questions.filter((q) => isFlagged(session.state, q.ref));
    if (!flagged.length) return;
    startChapter(session.topic, session.sub, flagged);
  };

  $("btnReset").onclick = () => {
    if (!confirm("清除所有章节的练习进度？")) return;
    store = { chapters: {}, last: null };
    save();
    renderChapters();
    updateContinueBtn();
  };

  document.addEventListener("keydown", (e) => {
    if (viewPractice.hidden) return;
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
    if (e.key === " ") { e.preventDefault(); if ($("answerCard").hidden) reveal(); }
    else if (e.key === "ArrowRight") { e.preventDefault(); go(1); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); go(-1); }
    else if (e.key.toLowerCase() === "f") { e.preventDefault(); toggleFlag(); }
    else if (e.key === "Escape") { $("btnBack").click(); }
  });

  /* ---------- 启动 ---------- */
  if (!INDEX.length) {
    document.body.innerHTML = '<p style="padding:40px;font-family:sans-serif">没有数据，先运行 <code>gen_web_split.py</code></p>';
    return;
  }
  const totalQ = INDEX.reduce((a, b) => a + b.count, 0);
  $("totalInfo").textContent = INDEX.length + " 个科目 · " + totalQ + " 题 · 按章节逐题练习，答案默认收起";
  openSubject(activeSlug);
})();
