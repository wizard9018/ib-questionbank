/* 分章练习 —— 按学科合并 HL/SL，逐题练，答案默认收起，进度存本机 */
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

  /* ---------- 科目分组（HL/SL 合并） ---------- */
  function groupIndex() {
    const map = new Map();
    INDEX.forEach((sub) => {
      const m = sub.slug.match(/^(.+?)-(hl|sl)$/);
      const key = m ? m[1] : sub.slug;
      if (!map.has(key)) {
        map.set(key, { key, name: sub.name.replace(/\s+(HL|SL)$/, ""), slugs: [], count: 0 });
      }
      const g = map.get(key);
      g.slugs.push(sub.slug);
      g.count += sub.count;
    });
    return [...map.values()];
  }
  const GROUPS = groupIndex();
  const shortName = (n) => n.replace(/^IB Mathematics\s+/, "Math ").replace(/^IB\s+/, "");
  // Storage 里的路径用的是原始目录名（IB Physics HL），不是 slug
  const storageDir = (slug) => {
    const s = INDEX.find((x) => x.slug === slug);
    return s ? s.name : slug;
  };

  /* ---------- 进度存储 ---------- */
  const STORE_KEY = "ib-practice-v2";
  let store = { chapters: {}, last: null };
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (raw) store = Object.assign(store, JSON.parse(raw));
  } catch (e) {}
  const save = () => { try { localStorage.setItem(STORE_KEY, JSON.stringify(store)); } catch (e) {} };
  const ckey = (g, topic, sub) => g + "||" + topic + "||" + sub;
  const chapterState = (g, topic, sub) => {
    const k = ckey(g, topic, sub);
    if (!store.chapters[k]) store.chapters[k] = { done: {}, flagged: {} };
    return store.chapters[k];
  };
  const isDone = (st, ref) => !!st.done[ref];
  const isFlagged = (st, ref) => !!st.flagged[ref];

  /* ---------- 元素 ---------- */
  const $ = (id) => document.getElementById(id);
  const viewHome = $("viewHome"), viewPractice = $("viewPractice"), viewDone = $("viewDone");
  const subjectBar = $("subjectBar"), chapterList = $("chapterList"), subjectName = $("subjectName");

  function showView(v) {
    [viewHome, viewPractice, viewDone].forEach((x) => (x.hidden = x !== v));
    window.scrollTo(0, 0);
  }

  /* ---------- 数据加载与合并 ---------- */
  let activeKey = GROUPS.length ? GROUPS[0].key : null;
  let activeSubject = null;   // {name, topics: [...]}
  let session = null;

  function loadLocalBundle(slug) {
    return new Promise((res, rej) => {
      const s = document.createElement("script");
      s.src = "data/" + slug + ".js";
      s.onload = () => res(window.RV_LOADED[slug]);
      s.onerror = () => rej(new Error("加载失败：" + slug));
      document.head.appendChild(s);
    });
  }

  /* 从 Supabase 拉一个科目的全部题目，转成本地 bundle 的结构 */
  async function loadFromSupabase(slug) {
    const cfg = window.IB_CONFIG;
    const base = cfg.supabaseUrl.replace(/\/$/, "");
    const headers = { apikey: cfg.supabaseKey, Authorization: "Bearer " + cfg.supabaseKey };
    const sel = "ref,topic,subtopic,body,mark_scheme,difficulty,marks,paper,calculator";
    const url = base + "/rest/v1/questions?subject_slug=eq." +
      encodeURIComponent(slug) + "&select=" + sel + "&order=topic,subtopic,ref";

    const resp = await fetch(url, { headers });
    if (!resp.ok) throw new Error("Supabase " + resp.status + " " + (await resp.text()).slice(0, 120));
    const rows = await resp.json();

    const tMap = new Map();
    rows.forEach((r) => {
      if (!tMap.has(r.topic)) tMap.set(r.topic, new Map());
      const sMap = tMap.get(r.topic);
      if (!sMap.has(r.subtopic)) sMap.set(r.subtopic, []);
      sMap.get(r.subtopic).push({
        ref: r.ref,
        body: withImageUrls(r.body, storageDir(slug), r.topic, r.subtopic),
        markScheme: r.mark_scheme ? withImageUrls(r.mark_scheme, storageDir(slug), r.topic, r.subtopic) : "",
        difficulty: r.difficulty || "",
        marks: r.marks || "",
        paper: r.paper || "",
        calculator: !!r.calculator,
      });
    });

    return {
      slug,
      name: slug,
      topics: [...tMap.entries()].map(([name, sMap]) => ({
        name,
        subtopics: [...sMap.entries()].map(([n, questions]) => ({ name: n, questions })),
      })),
    };
  }

  /* 把 markdown 里的 images/xxx.png 换成 Storage 公网 URL */
  function withImageUrls(md, slug, topic, subtopic) {
    const cfg = window.IB_CONFIG;
    if (!cfg || !cfg.supabaseUrl) return md;
    const base = cfg.supabaseUrl.replace(/\/$/, "") + "/storage/v1/object/public/" +
      cfg.imageBucket + "/";
    const dir = slug + "/" + topic + "/" + subtopic + "/";
    return md.replace(/\]\(images\//g, "](" + base + encodeURI(dir) + "images/");
  }

  function loadSubject(slug) {
    if (window.RV_LOADED[slug]) return Promise.resolve(window.RV_LOADED[slug]);
    const cfg = window.IB_CONFIG;
    if (cfg && cfg.supabaseUrl && cfg.supabaseKey) {
      return loadFromSupabase(slug).then((b) => {
        window.RV_LOADED[slug] = b;
        return b;
      });
    }
    return loadLocalBundle(slug);
  }

  function mergeSubjects(subs) {
    // 按 topic 名合并，题目按 ref 去重（SL 是 HL 子集，重复的只留一份）
    const topicMap = new Map();
    subs.forEach((s) => {
      s.topics.forEach((t) => {
        if (!topicMap.has(t.name)) topicMap.set(t.name, new Map());
        const stMap = topicMap.get(t.name);
        t.subtopics.forEach((st) => {
          if (!stMap.has(st.name)) stMap.set(st.name, []);
          const seen = new Set(stMap.get(st.name).map((q) => q.ref));
          st.questions.forEach((q) => {
            if (!seen.has(q.ref)) { stMap.get(st.name).push(q); seen.add(q.ref); }
          });
        });
      });
    });
    // 去重后可能出现 0 题的章节，直接剔掉
    const topics = [...topicMap.entries()]
      .map(([name, stMap]) => ({
        name,
        subtopics: [...stMap.entries()]
          .filter(([, qs]) => qs.length > 0)
          .map(([n, qs]) => ({ name: n, questions: qs })),
      }))
      .filter((t) => t.subtopics.length > 0);
    return { name: subs.length === 1 ? subs[0].name : subs[0].name.replace(/\s+(HL|SL)$/, ""), topics };
  }

  function openSubject(key) {
    activeKey = key;
    renderSubjectBar();
    subjectName.textContent = "加载中…";
    chapterList.innerHTML = "";
    const g = GROUPS.find((x) => x.key === key);
    Promise.all(g.slugs.map(loadSubject)).then((subs) => {
      activeSubject = mergeSubjects(subs);
      subjectName.textContent = g.name;
      renderChapters();
      updateContinueBtn();
    }).catch((e) => {
      subjectName.textContent = "加载失败";
      chapterList.innerHTML = '<p style="color:#a33">' + esc(e.message) + "</p>";
    });
  }

  /* ---------- 章节列表 ---------- */
  function renderSubjectBar() {
    subjectBar.innerHTML = "";
    GROUPS.forEach((g) => {
      const b = document.createElement("button");
      b.textContent = shortName(g.name);
      b.className = g.key === activeKey ? "active" : "";
      b.onclick = () => openSubject(g.key);
      subjectBar.appendChild(b);
    });
  }

  function diffBadges(qs) {
    const c = { easy: 0, medium: 0, hard: 0 };
    qs.forEach((q) => { if (c[q.difficulty] !== undefined) c[q.difficulty]++; });
    return ['<span class="d easy">e' + c.easy + "</span>",
      '<span class="d medium">m' + c.medium + "</span>",
      '<span class="d hard">h' + c.hard + "</span>"].join("");
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
        const state = chapterState(activeKey, topic.name, st.name);
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
              '<span class="diffrow">' + diffBadges(st.questions) + "</span>" +
            "</div>" +
          "</div>" +
          '<span class="ring" style="--p:' + pct + '"><span>' + Math.round(pct) + "%</span></span>";
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
    if (!last || last.g !== activeKey) { btn.hidden = true; return; }
    const topic = activeSubject.topics.find((t) => t.name === last.topic);
    const st = topic && topic.subtopics.find((s) => s.name === last.sub);
    if (!st) { btn.hidden = true; return; }
    btn.hidden = false;
    btn.textContent = "继续：" + last.sub + "（第 " + (last.idx + 1) + " 题）";
    btn.onclick = () => startChapter(last.topic, last.sub, st.questions, last.idx);
  }

  /* ---------- 练习 ---------- */
  function startChapter(topicName, subName, allQuestions, startIdx) {
    const state = chapterState(activeKey, topicName, subName);
    session = { topic: topicName, sub: subName, questions: allQuestions.slice(), idx: startIdx || 0, state };
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
      questions: picked.map((p) => p.q), idx: 0,
      state: { done: {}, flagged: {} }, random: true,
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

    if (!session.random) {
      store.last = { g: activeKey, topic: session.topic, sub: session.sub, idx: session.idx };
      save();
    }
  }

  function reveal() {
    const q = session.questions[session.idx];
    $("answerCard").hidden = false;
    $("btnReveal").hidden = true;
    if (q && !session.random) { session.state.done[q.ref] = 1; save(); }
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
    $("btnFlag").textContent = flagged ? "已标记复习" : "标记复习";
  }

  function finishChapter() {
    if (session.random) { showView(viewHome); renderChapters(); return; }
    const total = session.questions.length;
    const doneN = session.questions.filter((q) => isDone(session.state, q.ref)).length;
    const flaggedN = session.questions.filter((q) => isFlagged(session.state, q.ref)).length;

    $("doneTitle").textContent = session.sub;
    $("doneStat").textContent = "本章 " + total + " 题，已看答案 " + doneN + " 题" +
      (flaggedN ? "，标记复习 " + flaggedN + " 题" : "");
    $("flaggedCount").textContent = flaggedN ? "(" + flaggedN + ")" : "";
    $("btnRedoFlagged").hidden = flaggedN === 0;
    showView(viewDone);
    confetti();
    renderChapters();
    updateContinueBtn();
  }

  /* ---------- 撒花 ---------- */
  function confetti(n) {
    const colors = ["#58cc02", "#1cb0f6", "#ffc800", "#ff4b4b", "#ce82ff", "#89e219"];
    for (let i = 0; i < (n || 44); i++) {
      const el = document.createElement("i");
      el.className = "confetti";
      el.style.left = Math.random() * 100 + "vw";
      el.style.background = colors[Math.floor(Math.random() * colors.length)];
      el.style.animationDuration = (1.6 + Math.random() * 1.2) + "s";
      el.style.animationDelay = (Math.random() * 0.35) + "s";
      el.style.width = (6 + Math.random() * 6) + "px";
      document.body.appendChild(el);
      setTimeout(() => el.remove(), 3200);
    }
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
    const st = chapterState(activeKey, session.topic, session.sub);
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
  const totalQ = GROUPS.reduce((a, b) => a + b.count, 0);
  $("totalInfo").textContent = GROUPS.length + " 个学科 · 按章节逐题练习，答案默认收起（同一题多处归档的已去重）";
  openSubject(activeKey);
})();
