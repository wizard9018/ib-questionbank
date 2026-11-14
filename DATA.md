# 数据存储说明

给接手做界面的人看的。文字在 **Supabase Postgres**，图片在 **Supabase Storage**，本地 `questions/` 是原始源文件。

```
                    ┌─────────────────────────────┐
本地源文件           │  Supabase Postgres           │
questions/    ──导──▶  subjects / topics /          │
  *.md              │  subtopics / questions       │
  images/     ──传──▶  Supabase Storage            │
                    │  bucket: questions (public)  │
                    └─────────────────────────────┘
                                  │
                            前端 fetch
```

---

## 1. 本地源文件

```
questions/
└── IB Physics HL/                    ← 科目目录名（原始，带空格）
    └── Wave Behaviour/               ← topic
        └── Simple Harmonic Motion/   ← subtopic
            ├── PH0113.md             ← 一道题一个文件
            ├── PH0114.md
            └── images/               ← 该小节的配图
                └── PH0113.JPEG
```

### md 文件格式

```markdown
---
reference: PH0113
topic: Wave Behaviour
subtopic: Simple Harmonic Motion
paper: Paper 2
marks: 4
difficulty: medium
type: RCQ
---

题面正文（Markdown + LaTeX）

![](images/PH0113.JPEG)

## 评分标准 / Mark scheme

$1.$ $\hspace{1em}$ $\textrm{C}$   [1 mark]

- C. 因为...
```

关键点：

- **frontmatter 里没有 `subject`** —— 科目从目录层级推导
- **评分标准的分隔行**是 `## 评分标准 / Mark scheme`，也可能是 `## 评分标准`，正则用 `^##\s*评分标准.*$`
- **难度三档**：`easy` / `medium` / `hard`
- **带空格的图片路径用尖括号包**：`![](<images/AA1169_a (2).JPEG>)`，否则 Markdown 解析会截断
- 数学题的 LaTeX 大量使用 `\begin{aligned}`（原始数据是裸 `\begin`，已批量修正，别改回去）

---

## 2. Supabase Postgres

项目 URL：`https://fclcyabifwllunfossid.supabase.co`

### `subjects` — 26 行

| 字段 | 类型 | 说明 |
|---|---|---|
| `slug` | text PK | `ib-physics-hl`，前端拿它去请求 |
| `group_key` | text | `ib-physics`，HL/SL 合并用的 key |
| `name` | text | `IB Physics HL`，**也是 Storage 的目录名** |
| `level` | text | `HL` / `SL` / `null` |
| `position` | int | 排序 |
| `question_count` | int | 该科目题目数 |

### `topics` / `subtopics`

| 表 | 字段 |
|---|---|
| `topics` | `id` bigserial PK, `subject_slug` FK→subjects.slug, `name`, `position` |
| `subtopics` | `id` bigserial PK, `topic_id` FK→topics.id, `name`, `position` |

### `questions` — 10812 行

| 字段 | 类型 | 说明 |
|---|---|---|
| `ref` | text | 题号 `PH0113`，和 `subject_slug` 组成主键 |
| `subject_slug` | text | `ib-physics-hl` |
| `subject_key` | text | `ib-physics`，**按学科查题用这个** |
| `topic` | text | `Wave Behaviour` |
| `subtopic` | text | `Simple Harmonic Motion` |
| `body` | text | 题面 Markdown |
| `mark_scheme` | text | 评分标准 Markdown，可能为 null |
| `difficulty` | text | `easy` / `medium` / `hard` |
| `marks` | int | 分值 |
| `paper` | text | `Paper 1` / `Paper 2` … |
| `calculator` | bool | 是否允许计算器 |
| `images` | jsonb | **一直是空数组 `[]`，别用它**（历史字段，图片靠前端拼 URL） |

主键：`(subject_slug, ref)`。索引：`subject_key`、`(subject_key, topic, subtopic)`、`ref`。

### `progress` — 目前空表

存多端同步进度用，现在前端走的是 localStorage 没启用。

| 字段 | 说明 |
|---|---|
| `user_id` uuid | 对应 `auth.uid()` |
| `subject_key`, `topic`, `subtopic` | 定位章节 |
| `done_refs` jsonb | `{"PH0113": 1}` 已看答案的题 |
| `flagged_refs` jsonb | `{"PH0114": 1}` 标记复习的题 |
| `updated_at` timestamptz | |

RLS：只能读写 `auth.uid() = user_id` 的行。要用它得先接 Supabase Auth。

### 权限（RLS）

| 表 | 读 | 写 |
|---|---|---|
| 前 4 张 | 所有人 | 只有 service_role |
| `progress` | 只能看自己的 | 只能写自己的 |

---

## 3. Supabase Storage

- Bucket：`questions`，**公开可读**
- 路径就是本地相对路径，**一一对应**

```
questions/<科目目录名>/<topic>/<subtopic>/images/<文件名>
```

例：
```
questions/IB Physics HL/Wave Behaviour/Simple Harmonic Motion/images/PH0113.JPEG
```

### 路径规则（踩过坑，很关键）

| 字符 | 能不能用 | 处理 |
|---|---|---|
| 空格 | ✅ 可以 | URL 里编码成 `%20` |
| `(` `)` `&` `,` | ✅ 可以 | — |
| `^` `%` `=` `'` `’` | ❌ 拒收 | 已改成 `_` 或 `pct` |
| 拉丁重音 `é` `è` `ó` | ❌ 拒收 | 已 NFKD 转 ASCII（`Expériences`→`Experiences`） |
| 窄空格 U+202F | ❌ 拒收 | macOS 截图文件名带的，已换成普通空格 |
| 中文 | ❓ 未验证 | 当前数据里没有（题库本身是英文） |

**所以 `subjects.name`（`IB Physics HL`）和数据库里存的 `topic`/`subtopic` 就是真实路径的一部分。**

---

## 4. 前端怎么读

### 拉题目

```
GET {SUPABASE_URL}/rest/v1/questions
    ?subject_slug=eq.ib-physics-hl
    &select=ref,topic,subtopic,body,mark_scheme,difficulty,marks,paper,calculator
    &order=topic,subtopic,ref
Header: apikey: <publishable key>
        Authorization: Bearer <publishable key>
```

返回扁平数组，前端自己按 `topic` → `subtopic` 分组。

### 拼图片 URL

图片在 md 里写的是相对路径 `images/PH0113.JPEG`，渲染前替换：

```js
const base = SUPABASE_URL + "/storage/v1/object/public/questions/";
const dir  = subjectName + "/" + topic + "/" + subtopic + "/";  // 注意是 name 不是 slug
body = body.replace(/\]\(images\//g, "](" + base + encodeURI(dir) + "images/");
```

`encodeURI` 负责把空格变成 `%20`（`encodeURIComponent` 会把 `/` 也编码，不行）。

### 当前实现

`web/app.js` 里：

- `loadFromSupabase(slug)` — 拉数据 + 分组 + 替换图片 URL
- `storageDir(slug)` — slug → 原始科目名（**图片路径必须用这个名字**）
- `withImageUrls()` — 相对路径 → Storage 公网 URL
- `mergeSubjects()` — HL/SL 合并、按 `ref` 去重、剔掉 0 题章节

`web/config.js` 留空就退回读本地 `web/data/*.js`，纯静态也能跑（离线用）。

---

## 5. 数据特征（做界面要注意）

**去重**：本地 11344 个 md，入库 10812 题。差的 532 条是同一道题被同时归档到「具体章节」和兜底分类 `Scientific Skills & Tools / Unassigned`，去重时保留具体章节。

**HL/SL 的关系**：AA/AI 的 SL 100% 是 HL 子集（0 独有）；Physics 有 15 道、Chemistry/Biology 各有 1 道 SL 独有题，合并时别丢。

**一道题可能出现在多个章节**：前端 `mergeSubjects` 按 `ref` 去重，同一题只显示一次。

**选择题答案在 body 里**，形如 `**答案：D**`（物理/化学/生物的选择题都有）。

**分值标记**：`[1 mark]` / `[2 marks]`，从内容里的 `:marks[n]` 语法转换来的。

**4 处坏引用**：`HI0124.md` 里两个 `question:uuid` 的图，源站本来就没返回文件，约占 0.05%，可忽略。

---

## 6. 换账号要改什么

| 文件 | 改什么 | 能不能公开 |
|---|---|---|
| `web/config.js` | `supabaseUrl`、`supabaseKey` | ✅ publishable key 可以公开，设计如此 |
| `supabase/.env` | `SUPABASE_URL`、`SUPABASE_SERVICE_KEY` | ❌ **绝对不要提交**，已在 `.gitignore` |

换 Supabase 项目后要重跑：

```bash
# 1. 新项目 SQL Editor 执行 supabase/schema.sql
python supabase/import.py              # 2. 导 10812 题
python supabase/upload_images.py       # 3. 传 11921 张图（约 3 分钟）
```

`import.py` 会自动去重、自动建 subjects/topics/subtopics。`upload_images.py` 用 `x-upsert: true`，重复跑安全。

换完记得同步改 `web/config.js` 的 URL 和 key，否则前端还在读旧项目。
