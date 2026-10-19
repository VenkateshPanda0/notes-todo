# TaskFlow launch kit

A checklist and ready-to-edit copy for taking TaskFlow public. Nothing here is posted automatically; review and post it yourself.

## 1. One-time setup (≈30 min)

- [ ] **Enable GitHub Pages**: repo → Settings → Pages → Source: *Deploy from a branch* → `main` / `/docs`. The site will be at `https://venkateshpanda0.github.io/notes-todo/`.
- [ ] **Add repo topics**: `todo`, `notes`, `local-first`, `privacy`, `fastapi`, `react`, `typescript`, `sqlite`, `pywebview`, `desktop-app`.
- [ ] **Set the repo description + website URL** (the Pages link).
- [ ] **Upload the social preview image** (Settings → Social preview): use `docs/assets/social-preview.png` (1280×640, already generated).
- [ ] **Publish a release**: run *Actions → Release → Run workflow* once as a dry run, then `git tag v0.1.0 && git push origin v0.1.0`. The pipeline builds, smoke-tests and publishes `TaskFlow.exe` with a checksum. Without a downloadable binary most visitors bounce.
- [ ] **Record a 20–30 s demo GIF**: add a todo with a date → see it in Today → open Calendar → toggle dark mode. Put it at the top of the README.
- [ ] Create labels `good first issue`, `help wanted`, `roadmap`; open 5–8 small, well-described issues from the roadmap.
- [ ] Enable GitHub Discussions for ideas and Q&A.

## 2. Be honest about the lock

The App Lock now enforces access to the local API with session tokens, but the SQLite file is **not encrypted at rest** yet. Say so in launch posts (the README already does). Shipping database encryption is the best follow-up release and makes a good "v0.2" story.

## 3. Launch copy

### Hacker News (Show HN)

**Title:** `Show HN: TaskFlow – local-first todos and notes desktop app (FastAPI + React)`

**First comment:**
> Hi HN, I built TaskFlow because I wanted a todo/notes app that doesn't need an account or a server. It's a React UI served by a local FastAPI backend with SQLite, wrapped in a native window with pywebview and packaged as a single Windows exe.
>
> You explicitly choose Todo vs Note (no auto-classification), and there are Today / Upcoming / Calendar views, search, themes, and an optional app lock. Data lives in `%APPDATA%\TaskFlow\flow.db`.
>
> It also has linked Markdown notes with a graph view, and optional on-device AI (summaries, daily plan, related notes via Ollama; off by default, nothing leaves your machine). Next up: database encryption and chatting with your notes. Feedback on direction (and on the architecture) very welcome. MIT licensed.

### Reddit (r/selfhosted, r/opensource, r/productivity, r/ObsidianMD)

**Title:** `I built TaskFlow, a free local-first todo + notes app. No account, no cloud (open source)`

> Tired of todo apps that want an account and a subscription, I built one that keeps everything in a local SQLite file. Todos with priorities and due dates, a Notes view, Today/Upcoming/Calendar, light/dark themes, optional app lock. Windows .exe for now; macOS/Linux on the roadmap.
>
> Repo + screenshots: https://github.com/VenkateshPanda0/notes-todo
> Would love to hear which feature you'd want first: Markdown notes, recurring tasks, or sync?

(Check each subreddit's self-promotion rules before posting.)

### X / Bluesky / LinkedIn

> I just open-sourced TaskFlow: a local-first todo + notes desktop app. No account, no cloud, your data stays on your machine. React + FastAPI + SQLite, MIT licensed. Roadmap: encrypted DB, quick capture, Markdown notes, on-device AI. ⭐ https://github.com/VenkateshPanda0/notes-todo

## 4. After launch

- Reply to every issue and comment within a day for the first two weeks.
- Turn repeated requests into labelled roadmap issues.
- Ship small releases often (v0.1.1, v0.2.0) and write short release notes; momentum matters more than size.
- Later: Product Hunt launch once macOS/Linux builds and quick capture exist.

## 5. Suggested release order

1. **v0.1.0**: current feature set, binary release, landing page.
2. **v0.2.0**: enforced lock + encrypted DB, migrations, backup/restore.
3. **v0.3.0**: quick capture + natural-language dates, keyboard shortcuts.
4. **v0.4.0**: Markdown notes, tags, recurring tasks, reminders.
5. **v0.5.0**: macOS/Linux builds; then on-device AI and optional sync.
