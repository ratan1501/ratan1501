#!/usr/bin/env python3
"""Generates assets/streak.svg (neon terminal theme) from your GitHub contributions."""
import json, os, sys, urllib.request
from datetime import date, datetime, timedelta

USER = os.environ.get("GH_USER", "ratan1501")
TOKEN = os.environ.get("GH_TOKEN", "")
OUT = os.environ.get("OUT", "assets/streak.svg")
FONT = "font-family=\"'Fira Code','JetBrains Mono',Consolas,'Courier New',monospace\""


def gql(query):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": "streak-gen"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        sys.exit(f"GraphQL error: {data['errors']}")
    return data["data"]


def fetch_days():
    created = gql('{ user(login: "%s") { createdAt } }' % USER)["user"]["createdAt"]
    start_year = int(created[:4])
    today = date.today()
    days = {}
    for y in range(start_year, today.year + 1):
        q = '''{ user(login: "%s") { contributionsCollection(from: "%d-01-01T00:00:00Z", to: "%d-12-31T23:59:59Z")
              { contributionCalendar { weeks { contributionDays { date contributionCount } } } } } }''' % (USER, y, y)
        weeks = gql(q)["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
        for w in weeks:
            for d in w["contributionDays"]:
                days[d["date"]] = d["contributionCount"]
    return days


def fmt(d):
    return f"{d:%b} {d.day}, {d.year}"


def compute(days):
    today = date.today()
    ds = sorted(datetime.strptime(k, "%Y-%m-%d").date() for k in days if datetime.strptime(k, "%Y-%m-%d").date() <= today)
    total = sum(days[d.isoformat()] for d in ds)
    # longest streak
    best = (0, None, None)
    run, rs = 0, None
    prev = None
    for d in ds:
        if days[d.isoformat()] > 0:
            if run > 0 and prev == d - timedelta(days=1):
                run += 1
            else:
                run, rs = 1, d
            if run > best[0]:
                best = (run, rs, d)
        else:
            run = 0
        prev = d
    # current streak (today may still be empty)
    cur_end = today if days.get(today.isoformat(), 0) > 0 else today - timedelta(days=1)
    cur, d = 0, cur_end
    while days.get(d.isoformat(), 0) > 0:
        cur += 1
        d -= timedelta(days=1)
    cur_start = cur_end - timedelta(days=cur - 1) if cur else None
    first = ds[0] if ds else today
    last30 = [days.get((today - timedelta(days=29 - i)).isoformat(), 0) for i in range(30)]
    return dict(total=total, first=first, today=today, cur=cur, cur_start=cur_start, cur_end=cur_end,
                best=best[0], best_start=best[1], best_end=best[2], last30=last30)


def render(s):
    C = 326.7
    prog = min(1.0, s["cur"] / max(s["best"], 1)) if s["cur"] else 0.02
    target = C * (1 - prog)
    mx = max(max(s["last30"]), 1)
    bars = ""
    for i, v in enumerate(s["last30"]):
        h = 3 if v == 0 else 6 + 44 * v / mx
        col = "#16283a" if v == 0 else ("#00f0ff" if i % 2 else "#8b5cf6")
        bars += (f'<rect class="b" x="{60 + i * 26}" y="{300 - h:.1f}" width="18" height="{h:.1f}" rx="3" '
                 f'fill="{col}" style="animation-delay:{1.0 + i * 0.04:.2f}s"/>\n')
    cur_rng = f'{fmt(s["cur_start"])} – {fmt(s["cur_end"])}' if s["cur"] else "no active streak — go commit!"
    best_rng = f'{fmt(s["best_start"])} – {fmt(s["best_end"])}' if s["best"] else "—"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="330" viewBox="0 0 900 330">
<defs>
<linearGradient id="g" x1="0" x2="1"><stop offset="0" stop-color="#00f0ff"/><stop offset="1" stop-color="#8b5cf6"/></linearGradient>
<pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse"><path d="M30 0H0V30" fill="none" stroke="#0f2433" stroke-width="1"/></pattern>
<style>
.f{{opacity:0;animation:fi .6s ease forwards}}
@keyframes fi{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:1;transform:none}}}}
.ring{{stroke-dasharray:{C};stroke-dashoffset:{C};animation:draw 1.6s .4s cubic-bezier(.3,.7,.2,1) forwards}}
@keyframes draw{{to{{stroke-dashoffset:{target:.1f}}}}}
.b{{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:grow .5s ease-out forwards}}
@keyframes grow{{to{{transform:scaleY(1)}}}}
</style>
</defs>
<rect width="900" height="330" rx="16" fill="#05070f"/>
<rect width="900" height="330" rx="16" fill="url(#grid)"/>
<rect x="1" y="1" width="898" height="328" rx="15" fill="none" stroke="url(#g)" stroke-opacity=".6" stroke-width="1.5"/>
<rect x="1" y="1" width="898" height="40" rx="15" fill="#0a1020"/>
<circle cx="26" cy="21" r="6" fill="#ff5f56"/><circle cx="46" cy="21" r="6" fill="#ffbd2e"/><circle cx="66" cy="21" r="6" fill="#27c93f"/>
<text x="450" y="26" text-anchor="middle" font-size="13" fill="#5b6b86" {FONT}>streak.sh --user {USER}</text>

<g class="f" style="animation-delay:.2s" {FONT} text-anchor="middle">
<text x="150" y="118" font-size="40" font-weight="700" fill="url(#g)">{s["total"]:,}</text>
<text x="150" y="150" font-size="13" fill="#e6edf7" letter-spacing="2">TOTAL CONTRIBUTIONS</text>
<text x="150" y="172" font-size="11" fill="#5b6b86">{fmt(s["first"])} – Present</text>
</g>

<g {FONT} text-anchor="middle">
<circle cx="450" cy="115" r="52" fill="none" stroke="#16283a" stroke-width="7"/>
<circle class="ring" cx="450" cy="115" r="52" fill="none" stroke="url(#g)" stroke-width="7" stroke-linecap="round" transform="rotate(-90 450 115)"/>
<g class="f" style="animation-delay:.5s">
<text x="450" y="127" font-size="36" font-weight="700" fill="#a3ff6b">{s["cur"]}</text>
<text x="450" y="184" font-size="13" fill="#e6edf7" letter-spacing="2">CURRENT STREAK</text>
<text x="450" y="205" font-size="11" fill="#5b6b86">{cur_rng}</text>
</g>
</g>

<g class="f" style="animation-delay:.8s" {FONT} text-anchor="middle">
<text x="750" y="118" font-size="40" font-weight="700" fill="url(#g)">{s["best"]}</text>
<text x="750" y="150" font-size="13" fill="#e6edf7" letter-spacing="2">LONGEST STREAK</text>
<text x="750" y="172" font-size="11" fill="#5b6b86">{best_rng}</text>
</g>

<line x1="300" y1="70" x2="300" y2="190" stroke="#16283a"/><line x1="600" y1="70" x2="600" y2="190" stroke="#16283a"/>
<text x="60" y="232" font-size="12" fill="#5b6b86" {FONT} letter-spacing="3">// LAST 30 DAYS</text>
{bars}<rect x="60" y="302" width="780" height="1" fill="url(#g)" opacity=".5"/>
</svg>'''


if __name__ == "__main__":
    if not TOKEN:
        sys.exit("GH_TOKEN is required")
    stats = compute(fetch_days())
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(render(stats))
    print("wrote", OUT, {k: v for k, v in stats.items() if k != "last30"})
