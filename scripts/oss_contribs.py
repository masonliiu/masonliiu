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


def card(repo, pr, merged):
    """An SVG in the style of GitHub's pinned-repo cards, readable in light and dark themes."""
    avatar = base64.b64encode(fetch(repo["owner"]["avatar_url"] + "&s=48", raw=True)).decode()
    lang = repo.get("language") or ""
    color = LANG_COLORS.get(lang, "#8b949e")
    desc = html.escape(clip(repo.get("description") or "", 58))
    title = html.escape(clip(pr["title"], 50))
    x = 24
    stats = ""
    if lang:
        stats += f'<circle cx="{x + 6}" cy="113" r="6" fill="{color}"/><text x="{x + 18}" y="117">{html.escape(lang)}</text>'
        x += 30 + 7 * len(lang)
    stats += f'<path transform="translate({x},105)" d="{STAR}"/><text x="{x + 21}" y="117">{count(repo["stargazers_count"])}</text>'
    x += 70
    stats += f'<path transform="translate({x},105)" d="{FORK}"/><text x="{x + 21}" y="117">{count(repo["forks_count"])}</text>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="440" height="168" viewBox="0 0 440 168">
<style>
.c{{fill:#ffffff;stroke:#d0d7de}} text{{font:14px -apple-system,"Segoe UI",Helvetica,Arial,sans-serif;fill:#59636e}}
.n{{font-weight:600;fill:#0969da}} .d{{fill:#59636e}} path{{fill:#59636e}} .m{{fill:#8250df}} .t{{fill:#1f2328}}
@media (prefers-color-scheme: dark){{.c{{fill:#0d1117;stroke:#3d444d}} text,.d{{fill:#9198a1}} path{{fill:#9198a1}} .n{{fill:#4493f8}} .m{{fill:#ab7df8}} .t{{fill:#f0f6fc}}}}
</style>
<rect class="c" x="0.5" y="0.5" width="439" height="167" rx="6"/>
<clipPath id="a"><rect x="24" y="20" width="22" height="22" rx="5"/></clipPath>
<image href="data:image/png;base64,{avatar}" x="24" y="20" width="22" height="22" clip-path="url(#a)"/>
<text class="n" x="56" y="36">{html.escape(repo["full_name"])}</text>
<text class="d" x="24" y="72" style="font-size:13px">{desc}</text>
{stats}
<line x1="0" y1="134" x2="440" y2="134" stroke="#8b949e" stroke-opacity=".25"/>
<path class="m" transform="translate(24,144)" d="{MERGED}"/>
<text class="t" x="46" y="156" style="font-size:13px">{title}</text>
<text x="416" y="156" text-anchor="end" style="font-size:12px">{merged}</text>
</svg>'''


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
    links = []
    for repo, pr, merged in rows:
        name = f'{repo["full_name"].replace("/", "-")}-{pr["number"]}.svg'
        with open(os.path.join(OUT, name), "w") as fh:
            fh.write(card(repo, pr, merged))
        links.append(f'<a href="{pr["html_url"]}"><img src="{OUT}/{name}" width="49%" alt="{html.escape(repo["full_name"])}: {html.escape(pr["title"])}"></a>')
    body = "\n".join(" ".join(links[i:i + 2]) for i in range(0, len(links), 2)) if links else "_Nothing merged yet._"

    text = open("README.md").read()
    text = re.sub(re.escape(START) + r".*?" + re.escape(END), f"{START}\n{body}\n{END}", text, flags=re.S)
    open("README.md", "w").write(text)


if __name__ == "__main__":
    main()
