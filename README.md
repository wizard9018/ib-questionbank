# IB 题库 · 分章练习

IB 全科题库，10812 道题（本地 11344 个文件，同一题多处归档的已去重），按章节组织，逐题练习——答案默认收起，自己先做，再对评分标准。

界面是 Duolingo 风格：绿色圆角大按钮、进度环、完成章节撒花。

## 规模

| 科目 | 题目数 |
|---|---|
| Mathematics AA | 2922 |
| Mathematics AI | 2714 |
| Physics | 1089 |
| Chemistry | 1654 |
| Biology | 1484 |
| History | 804 |
| Spanish B | 600 |
| French B | 318 |
| Psychology | 315 |
| Economics | 250 |
| Business Mgmt | 222 |
| English B | 87 |
| Ab Initio French / Spanish | 90 |
| **合计** | **10812**（26 个科目，14 个学科；去重后） |

每道题包含：题面（Markdown + LaTeX）、评分标准（A1/M1 给分点）、难度（easy/medium/hard）、分值、配图。

HL/SL 在网页上合并成学科，题目按题号去重——SL 是 HL 的子集，但 Physics 有 15 道、Chemistry/Biology 各有 1 道 SL 独有题，都保留。

## 网页用法

打开 `web/index.html` 即可用（双击就能跑，不需要服务器）。

**操作**

| 键 | 作用 |
|---|---|
| `空格` | 看答案 |
| `→` / `←` | 下一题 / 上一题 |
| `F` | 标记需要复习 |
| `Esc` | 返回章节列表 |

练习进度存在浏览器本地（localStorage），关掉再开会接着上次。

## Supabase（可选，多端同步）

题库和图片可以迁到 Supabase，前端就能在任意设备用同一份数据。

```bash
# 1. 在 Supabase SQL Editor 执行建表
supabase/schema.sql

# 2. 填凭证
cp .env.example supabase/.env   # 填 URL / service_role key

# 3. 导入题目（约 10812 行）
python supabase/import.py

# 4. 上传配图到 Storage 的 questions 桶（约 609 MB）
python supabase/upload_images.py --dry-run
python supabase/upload_images.py
```

`anon key` 只够读；导入和上传需要 `service_role key`，别把后者放进前端代码。

## 目录

```
web/            前端（index.html / app.js / style.css / vendor / data）
questions/      11344 个 Markdown（去重后入库 10812 题），一题一个文件，按 科目/topic/小节/ 分层
supabase/       建表 SQL、导入脚本、图片上传脚本
```

图片不进仓库（609 MB），由 Supabase Storage 提供；`questions/` 里的引用是相对路径 `images/xxx.png`。

## 说明

题目内容版权归原作者/出版方所有，这里仅作个人学习归档。数学题的原始 LaTeX 用了裸 `\begin`/`\end`（非标准），已批量修成 `\begin{aligned}` 才能正常渲染。
