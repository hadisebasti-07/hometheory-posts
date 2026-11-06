#!/usr/bin/env python3
"""HomeTheory SG - publish the next queued Instagram Reel.

Standard library only. Environment:
  IG_ACCESS_TOKEN  Instagram API (Instagram Login) token with instagram_business_basic
                   + instagram_business_content_publish
  MEDIA_BASE       public base URL of this repo on GitHub Pages, e.g.
                   https://<owner>.github.io/<repo>

Commands:
  next [--dry-run] [--window] [--once] [--gap N]   publish the first approved, unposted item
  check <item>                                      create the upload container only (no publish)
  status                                            list the queue
  refresh-token                                     print a refreshed 60-day token

Queue item = queue/NN-name/ with reel.mp4, cover.jpg (optional), caption.txt, post.json.
"""
import datetime as dt
import json, os, sys, time, urllib.error, urllib.parse, urllib.request

API = "https://graph.instagram.com/v21.0"
ROOT = os.path.dirname(os.path.abspath(__file__))
QUEUE = os.path.join(ROOT, "queue")
SGT = dt.timezone(dt.timedelta(hours=8))
WINDOW = (20, 23)          # post only 20:00-22:59 SGT when --window is set
DEFAULT_GAP_DAYS = 2       # one Reel every two days
START_DATE = dt.date(2026, 11, 7)   # scheduled runs never post before this (SGT); a forced run ignores it


def http(method, path, params=None):
    params = dict(params or {})
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}" if not path.startswith("http") else path
    if method == "GET":
        req = urllib.request.Request(f"{url}?{data.decode()}")
    else:
        req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"API error {e.code} on {path}: {e.read().decode()[:500]}")


def items():
    out = []
    for name in sorted(os.listdir(QUEUE)) if os.path.isdir(QUEUE) else []:
        d = os.path.join(QUEUE, name)
        pj = os.path.join(d, "post.json")
        if os.path.isdir(d) and os.path.exists(pj):
            out.append((name, d, json.load(open(pj))))
    return out


def last_posted_sgt_date():
    dates = [dt.datetime.fromisoformat(m["posted_at"].replace("Z", "+00:00")).astimezone(SGT).date()
             for _, _, m in items() if m.get("posted_at")]
    return max(dates) if dates else None


def media_url(name, fname):
    base = os.environ.get("MEDIA_BASE", "").rstrip("/")
    if not base:
        raise SystemExit("MEDIA_BASE is not set")
    return f"{base}/queue/{urllib.parse.quote(name)}/{urllib.parse.quote(fname)}"


def create_container(name, d):
    caption = open(os.path.join(d, "caption.txt"), encoding="utf-8").read().strip()
    params = {"media_type": "REELS", "video_url": media_url(name, "reel.mp4"),
              "caption": caption, "share_to_feed": "true"}
    if os.path.exists(os.path.join(d, "cover.jpg")):
        params["cover_url"] = media_url(name, "cover.jpg")
    cid = http("POST", "me/media", params)["id"]
    print(f"  container {cid}, waiting for Instagram to process the video…")
    for _ in range(60):                       # up to 10 minutes
        st = http("GET", cid, {"fields": "status_code,status"})
        code = st.get("status_code")
        if code == "FINISHED":
            return cid
        if code in ("ERROR", "EXPIRED"):
            raise SystemExit(f"  container {code}: {st.get('status')}")
        time.sleep(10)
    raise SystemExit("  timed out waiting for the video to process")


def cmd_next(args):
    now = dt.datetime.now(SGT)
    gap = DEFAULT_GAP_DAYS
    if "--gap" in args:
        gap = int(args[args.index("--gap") + 1])
    if "--window" in args and not (WINDOW[0] <= now.hour < WINDOW[1]):
        print(f"Outside posting window ({now:%H:%M} SGT); nothing to do."); return
    if ("--window" in args or "--once" in args) and now.date() < START_DATE:
        print(f"Posting starts {START_DATE}; nothing to do."); return
    last = last_posted_sgt_date()
    if "--once" in args and last == now.date():
        print("Already posted today (SGT); nothing to do."); return
    if ("--gap" in args or "--window" in args) and last and (now.date() - last).days < gap:
        print(f"Last post was {last}; next is due {last + dt.timedelta(days=gap)} (every {gap} days)."); return
    nxt = next(((n, d, m) for n, d, m in items() if m.get("approved") and not m.get("posted_at")), None)
    if not nxt:
        raise SystemExit("Nothing approved in the queue - add a post with queue_add.sh")
    name, d, meta = nxt
    print(f"Next: {name}")
    if "--dry-run" in args:
        print("  video:", media_url(name, "reel.mp4"))
        if os.path.exists(os.path.join(d, "cover.jpg")): print("  cover:", media_url(name, "cover.jpg"))
        print("  caption:\n" + open(os.path.join(d, "caption.txt"), encoding="utf-8").read()); return
    cid = create_container(name, d)
    media_id = http("POST", "me/media_publish", {"creation_id": cid})["id"]
    link = http("GET", media_id, {"fields": "permalink"}).get("permalink", "")
    meta.update(posted_at=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), media_id=media_id, permalink=link)
    json.dump(meta, open(os.path.join(d, "post.json"), "w"), indent=2)
    print(f"Posted: {link}")


def cmd_check(args):
    name = args[0]
    create_container(name, os.path.join(QUEUE, name))
    print("Container FINISHED - media is valid (not published).")


def cmd_status(_):
    last = last_posted_sgt_date()
    for n, _, m in items():
        state = f"posted {m['posted_at']}  {m.get('permalink', '')}" if m.get("posted_at") else ("approved" if m.get("approved") else "awaiting approval")
        print(f"{n:42s} {state}")
    if last:
        print(f"\nLast post: {last} SGT · next due: {last + dt.timedelta(days=DEFAULT_GAP_DAYS)}")


def cmd_refresh(_):
    r = http("GET", "https://graph.instagram.com/refresh_access_token", {"grant_type": "ig_refresh_token"})
    print(r.get("access_token"), "expires in", r.get("expires_in"), "s")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    {"next": cmd_next, "check": cmd_check, "status": cmd_status, "refresh-token": cmd_refresh}[sys.argv[1]](sys.argv[2:])
