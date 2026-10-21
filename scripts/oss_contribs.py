#!/usr/bin/env python3
"""Draw a card for each merged PR in other people's repos and list them in README.md."""
import base64
import html
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime

USER = "masonliiu"
MIN_STARS = 500  # skip small/private-collaboration repos
EXCLUDE_OWNERS = {"multimodal-interaction-lab", "danielhonrales"}
START, END = "<!-- oss:start -->", "<!-- oss:end -->"
OUT = "oss"

# GitHub's own language colours for the languages likely to show up
LANG_COLORS = {
    "Python": "#3572A5", "C++": "#f34b7d", "C": "#555555", "C#": "#178600", "TypeScript": "#3178c6",
    "JavaScript": "#f1e05a", "Rust": "#dea584", "Go": "#00ADD8", "Lua": "#000080", "GDScript": "#355570",
    "Java": "#b07219", "Kotlin": "#A97BFF", "Swift": "#F05138", "Shell": "#89e051",
}
STAR = "M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z"
FORK = "M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z"
MERGED = "M5.45 5.154A4.25 4.25 0 0 0 9.25 7.5h1.378a2.251 2.251 0 1 1 0 1.5H9.25A5.734 5.734 0 0 1 5 7.123v3.505a2.25 2.25 0 1 1-1.5 0V5.372a2.25 2.25 0 1 1 1.95-.218ZM4.25 13.5a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm8.5-4.5a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5ZM5 3.25a.75.75 0 1 0 0 .005V3.25Z"


def fetch(url, raw=False):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com"):
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as r:
        return r.read() if raw else json.load(r)


def count(n):
    return f"{n / 1000:.1f}k".replace(".0k", "k") if n >= 1000 else str(n)


def clip(text, n):
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


# Rough widths (px) of 14px system-ui glyphs, so stats sit right after their text
NARROW, WIDE = set("ijlrtf.,:;!|' "), set("mwMW@%")


def text_width(text, size=14):
    w = sum(0.32 if c in NARROW else 0.9 if c in WIDE else 0.62 if c.isupper() or c.isdigit() else 0.55 for c in text)
    return w * size


STYLE = """<style>
.c{fill:#ffffff;stroke:#d0d7de} .f{fill:#ffffff} .s{stroke:#d0d7de} text{font:14px -apple-system,"Segoe UI",Helvetica,Arial,sans-serif;fill:#59636e}
.n{font-weight:600;fill:#0969da} path{fill:#59636e} .m{fill:#8250df} .t{fill:#1f2328}
@media (prefers-color-scheme: dark){.c{fill:#0d1117;stroke:#3d444d} .f{fill:#0d1117} .s{stroke:#3d444d} text{fill:#9198a1} path{fill:#9198a1} .n{fill:#4493f8} .m{fill:#ab7df8} .t{fill:#f0f6fc}}
</style>"""
W = 440


def outline(h, top, bottom):
    """Card edge for one stacked piece: round only the outer corners, and leave the seam open."""
    r = 6
    x0, x1, y1 = 0.5, W - 0.5, h - 0.5
    left = f"M{x0},{y1 if bottom else h}"
    up = f"L{x0},{r + 0.5} Q{x0},0.5 {x0 + r},0.5 L{x1 - r},0.5 Q{x1},0.5 {x1},{r + 0.5}" if top else f"L{x0},0 M{x1},0"
    down = f"L{x1},{y1 - r} Q{x1},{y1} {x1 - r},{y1} L{x0 + r},{y1} Q{x0},{y1} {x0},{y1 - r} Z" if bottom else f"L{x1},{h}"
    if top and bottom:
        return f'<path class="c" d="M{x0},{y1 - r} {up[1:]} {down}"/>'
    if top:
        return f'<path class="c" d="M{x0},{h} {up[1:]} L{x1},{h}"/><rect class="f" x="1" y="{h - 2}" width="{W - 2}" height="2"/>'
    if bottom:
        return f'<path class="c" d="M{x0},0 L{x0},{y1 - r} Q{x0},{y1} {x0 + r},{y1} L{x1 - r},{y1} Q{x1},{y1} {x1},{y1 - r} L{x1},0"/>'
    return f'<path class="c" d="M{x0},0 L{x0},{h} M{x1},0 L{x1},{h}"/><rect class="f" x="1" y="0" width="{W - 2}" height="{h}"/>'


def repo_card(repo):
    """The project, in the style of GitHub's pinned-repo cards. Links to the repo."""
    avatar = base64.b64encode(fetch(repo["owner"]["avatar_url"] + "&s=48", raw=True)).decode()
    lang = repo.get("language") or ""
    x, stats = 20, ""
    if lang:
        stats += f'<circle cx="{x + 6}" cy="85" r="6" fill="{LANG_COLORS.get(lang, "#8b949e")}"/><text x="{x + 17}" y="90">{html.escape(lang)}</text>'
        x += 17 + text_width(lang) + 18
    for icon, n in ((STAR, repo["stargazers_count"]), (FORK, repo["forks_count"])):
        label = count(n)
        stats += f'<path transform="translate({x:.0f},77)" d="{icon}"/><text x="{x + 21:.0f}" y="90">{label}</text>'
        x += 21 + text_width(label) + 18
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="104" viewBox="0 0 {W} 104">{STYLE}
{outline(104, True, False)}
<clipPath id="a"><rect x="20" y="16" width="20" height="20" rx="4"/></clipPath>
<image href="data:image/png;base64,{avatar}" x="20" y="16" width="20" height="20" clip-path="url(#a)"/>
<text class="n" x="48" y="31">{html.escape(repo["full_name"])}</text>
<text x="20" y="59" style="font-size:13px">{html.escape(clip(repo.get("description") or "", 60))}</text>
{stats}
</svg>"""


def pr_row(pr, merged, last):
    """One merged PR under its project card. Links to the PR."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="34" viewBox="0 0 {W} 34">{STYLE}
{outline(34, False, last)}
<line class="s" x1="1" y1="0.5" x2="{W - 1}" y2="0.5" stroke-opacity=".6"/>
<path class="m" transform="translate(16,9)" d="{MERGED}"/>
<text class="t" x="38" y="22" style="font-size:13px">{html.escape(clip(pr["title"], 50))}</text>
<text x="{W - 16}" y="22" text-anchor="end" style="font-size:12px">{merged}</text>
</svg>"""


def main():
    q = urllib.parse.quote(f"is:pr is:merged author:{USER} -user:{USER}")
    items = fetch(f"https://api.github.com/search/issues?q={q}&per_page=100")["items"]
    rows, repos = [], {}
    for pr in items:
        full = "/".join(pr["repository_url"].split("/")[-2:])
        if full.split("/")[0] in EXCLUDE_OWNERS:
            continue
        if full not in repos:
            repos[full] = fetch(f"https://api.github.com/repos/{full}")
        repo = repos[full]
        if repo["stargazers_count"] < MIN_STARS:
            continue
        merged = datetime.strptime(pr["pull_request"]["merged_at"][:10], "%Y-%m-%d").strftime("%b %Y")
        rows.append((repo, pr, merged))
    rows.sort(key=lambda r: r[0]["stargazers_count"], reverse=True)

    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    by_repo = {}
    for repo, pr, merged in rows:
        by_repo.setdefault(repo["full_name"], (repo, []))[1].append((pr, merged))
    blocks = []
    for full, (repo, prs) in by_repo.items():
        slug = full.replace("/", "-")
        with open(os.path.join(OUT, f"{slug}.svg"), "w") as fh:
            fh.write(repo_card(repo))
        lines = [f'<a href="{repo["html_url"]}"><img src="{OUT}/{slug}.svg" width="{W}" alt="{html.escape(full)}"></a>']
        for i, (pr, merged) in enumerate(prs):
            with open(os.path.join(OUT, f"{slug}-{pr['number']}.svg"), "w") as fh:
                fh.write(pr_row(pr, merged, i == len(prs) - 1))
            lines.append(f'<a href="{pr["html_url"]}"><img src="{OUT}/{slug}-{pr["number"]}.svg" width="{W}" alt="{html.escape(pr["title"])}"></a>')
        blocks.append("<br>\n".join(lines))
    body = "\n\n".join(f"<p>\n{b}\n</p>" for b in blocks) if blocks else "_Nothing merged yet._"

    text = open("README.md").read()
    text = re.sub(re.escape(START) + r".*?" + re.escape(END), f"{START}\n{body}\n{END}", text, flags=re.S)
    open("README.md", "w").write(text)


if __name__ == "__main__":
    main()
