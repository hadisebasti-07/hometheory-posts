# HomeTheory SG: automatic Reel posting

A public GitHub repo holds a queue of finished Reels. **Every day at 20:00 SGT**, cron-job.org starts a GitHub Actions job. The job publishes the next approved Reel through the Instagram API, but **only if the last post was 2 or more days ago**. That gives one Reel every 2 days with no server and no paid service.

```
ig-queue/
├── .github/workflows/publish.yml   # runs publish.py, commits post.json back
├── .nojekyll / .gitignore
├── publish.py                      # Python 3 standard library only
├── queue_add.sh                    # run on your Mac to queue a finished reel
└── queue/
    ├── 01-002-hdb-layout-review/   # reel.mp4 · cover.jpg · caption.txt · post.json
    ├── 02-003-layout-review-02-flexi/
    └── 03-004-sale-desk-1111-measure/
```

The lowest-numbered folder that is approved and not yet posted goes out next. After posting, the workflow writes `posted_at`, `media_id` and `permalink` into that folder's `post.json`.

## Day to day

| Task | How |
|---|---|
| Add a Reel | `./queue_add.sh ../content/reels/<folder> [cover-second]`, then `git add -A && git commit -m "queue <name>" && git push` |
| See the queue | `python3 publish.py status` (also shows when the next post is due) |
| Check what posts next | `MEDIA_BASE=https://<owner>.github.io/<repo> IG_ACCESS_TOKEN=x python3 publish.py next --dry-run` |
| Hold a Reel back | Set `"approved": false` in its `post.json`, then push |
| Reorder | Rename the `NN-` folders |
| Post now (ignore the 2-day gap) | GitHub → Actions → *Publish next reel* → Run workflow → tick **force** |
| Refresh the Instagram token (every < 60 days) | `IG_ACCESS_TOKEN=… python3 publish.py refresh-token`, then paste it into the repo secret |

Always `git pull` before editing the queue: the workflow pushes a commit after every post.

## One-time setup

**Instagram**
- [ ] Switch @hometheory.sg (or your handle) to a **Business or Creator** account.
- [ ] In Meta for Developers, create an app with **Instagram API (Instagram Login)** and add the account as a tester.
- [ ] Generate a token with `instagram_business_basic` + `instagram_business_content_publish` (valid 60 days; note the expiry).

**GitHub**
- [ ] Create a **public** repo (e.g. `hometheory-posts`) and push this folder.
- [ ] Settings → Pages → Deploy from branch `main`, `/ (root)`. Check that `https://<owner>.github.io/<repo>/queue/01-002-hdb-layout-review/reel.mp4` plays.
- [ ] Settings → Secrets and variables → Actions → new secret `IG_ACCESS_TOKEN`.
- [ ] Fine-grained personal access token for cron-job.org: only this repo, **Actions: Read and write**.

**cron-job.org**
- [ ] URL `https://api.github.com/repos/<owner>/<repo>/actions/workflows/publish.yml/dispatches`, method **POST**, body `{"ref":"main"}`.
- [ ] Headers: `Authorization: Bearer github_pat_…`, `Accept: application/vnd.github+json`, `X-GitHub-Api-Version: 2022-11-28`.
- [ ] Schedule: **every day**, minute `0`, hour `20`, time zone Asia/Singapore. `publish.py` skips the days in between. Check that the preview shows one time per day.
- [ ] Notify on failure. Test only at 20:00–22:59 SGT on a day a post is due, because the test posts for real.

GitHub's own schedule (hourly 20:00–22:00 SGT) is a backup. It only posts inside that window, and only when a post is due.

## Reel rules
- MP4 H.264 + AAC, 1080×1920, 30 fps (our renders already meet this). `queue_add.sh` remuxes with `faststart` and grabs `cover.jpg` from the hook frame.
- Captions: hook line, 2–4 value lines, a send + follow CTA, "illustration only" and **"AI voiceover"** disclosure, and up to 5 hashtags.
- Turn on the AI label manually in the app if Instagram asks; the caption line covers the disclosure in the meantime.
