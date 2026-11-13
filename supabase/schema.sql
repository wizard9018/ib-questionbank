-- IB 题库 · Supabase schema
-- 在 Supabase Dashboard → SQL Editor 里整段执行

-- ============ 科目 ============
create table if not exists subjects (
  slug        text primary key,          -- ib-physics-hl
  group_key   text not null,             -- ib-physics（HL/SL 合并用）
  name        text not null,             -- IB Physics HL
  level       text,                      -- HL / SL / null
  position    int  not null default 0,
  question_count int not null default 0
);

-- ============ 章节 ============
create table if not exists topics (
  id          bigserial primary key,
  subject_slug text not null references subjects(slug) on delete cascade,
  name        text not null,
  position    int  not null default 0,
  unique (subject_slug, name)
);

create table if not exists subtopics (
  id          bigserial primary key,
  topic_id    bigint not null references topics(id) on delete cascade,
  name        text not null,
  position    int  not null default 0,
  unique (topic_id, name)
);

-- ============ 题目 ============
create table if not exists questions (
  ref          text not null,            -- PH0001
  subject_slug text not null,            -- ib-physics-hl
  subject_key  text not null,            -- ib-physics（方便前端按学科取）
  topic       text not null,
  subtopic    text not null,
  body        text not null,             -- 题面 markdown
  mark_scheme text,                      -- 评分标准 markdown
  difficulty  text,                      -- easy / medium / hard
  marks       int,
  paper       text,
  calculator  boolean not null default false,
  images      jsonb not null default '[]'::jsonb,
  primary key (subject_slug, ref)
);

create index if not exists idx_q_subject_key on questions (subject_key);
create index if not exists idx_q_topic       on questions (subject_key, topic, subtopic);
create index if not exists idx_q_ref         on questions (ref);

-- ============ 练习进度（多端同步用，可不用） ============
create table if not exists progress (
  id           bigserial primary key,
  user_id      uuid not null,            -- auth.uid()，或前端生成的匿名 uuid
  subject_key  text not null,
  topic        text not null,
  subtopic     text not null,
  done_refs    jsonb not null default '{}'::jsonb,
  flagged_refs jsonb not null default '{}'::jsonb,
  updated_at   timestamptz not null default now(),
  unique (user_id, subject_key, topic, subtopic)
);

create index if not exists idx_progress_user on progress (user_id);

-- ============ 行级安全 ============
alter table subjects  enable row level security;
alter table topics    enable row level security;
alter table subtopics enable row level security;
alter table questions enable row level security;
alter table progress  enable row level security;

-- 题库：所有人可读，只有 service_role 能写
drop policy if exists "public read subjects"  on subjects;
drop policy if exists "public read topics"    on topics;
drop policy if exists "public read subtopics" on subtopics;
drop policy if exists "public read questions" on questions;
create policy "public read subjects"  on subjects  for select using (true);
create policy "public read topics"    on topics    for select using (true);
create policy "public read subtopics" on subtopics for select using (true);
create policy "public read questions" on questions for select using (true);

-- 进度：只能读写自己的行
drop policy if exists "own progress select" on progress;
drop policy if exists "own progress insert" on progress;
drop policy if exists "own progress update" on progress;
drop policy if exists "own progress delete" on progress;
create policy "own progress select" on progress for select using (auth.uid() = user_id);
create policy "own progress insert" on progress for insert with check (auth.uid() = user_id);
create policy "own progress update" on progress for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "own progress delete" on progress for delete using (auth.uid() = user_id);

-- ============ Storage：图片桶 ============
-- 先在 Dashboard → Storage 建一个公开桶叫 questions，然后执行下面的策略
insert into storage.buckets (id, name, public)
values ('questions', 'questions', true)
on conflict (id) do update set public = true;

drop policy if exists "public read question images" on storage.objects;
create policy "public read question images"
  on storage.objects for select
  using (bucket_id = 'questions');
