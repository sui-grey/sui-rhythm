"""곡별 음원 링크 채우기 → songs/<곡>/links.json + chart.json의 links (10/10 새벽, 여보 "links.json은 sui youtube에서 뽑고 애플 뮤직은 검색해서")

- 스포티파이·유튜브 뮤직: `sui youtube list`로 "<제목> … Official MV"를 찾고 `sui youtube desc`의 ▸ 줄에서
- 애플 뮤직: iTunes lookup(아티스트 1887834805 곡 목록)에서 곡 폴더명·영어 제목으로, 싱글판 먼저
- 못 찾은 건 make_chart.LINKS(아티스트 페이지) 그대로
사용: python fill_links.py
"""
import json
import os
import re
import subprocess
import sys

import requests

from make_chart import LINKS

HERE = os.path.dirname(os.path.abspath(__file__))
ARTIST_ID = "1887834805"


def sui(*args):
    r = subprocess.run(["sui", *args], capture_output=True, text=True, encoding="utf-8", shell=(os.name == "nt"))
    return r.stdout


def norm(s):
    return re.sub(r"[^0-9a-z가-힣ぁ-んァ-ン一-龥]+", "", (s or "").lower())


def apple_tracks():
    r = requests.get("https://itunes.apple.com/lookup", params={"id": ARTIST_ID, "entity": "song", "limit": 200, "country": "kr"}, timeout=20).json()
    return [x for x in r.get("results", []) if x.get("wrapperType") == "track"]


def apple_link(tracks, names):
    keys = {norm(n) for n in names if n}
    hits = [x for x in tracks if norm(x["trackName"]) in keys]
    if not hits:
        return None
    hits.sort(key=lambda x: (0 if "single" in (x.get("collectionName") or "").lower() else 1))
    x = hits[0]
    return x["trackViewUrl"].split("&")[0]


def mv_list():
    """내 영상 중 Official MV — [(id, title)]"""
    out = sui("youtube", "list", "-l", "500")
    vids = []
    for line in out.splitlines():
        m = re.match(r"\s+(\S{11})\s+\d{4}-\d{2}-\d{2}\s+(.*)$", line)
        if m and "official mv" in m.group(2).lower():
            vids.append((m.group(1), m.group(2)))
    return vids


def mv_links(video_id):
    desc = sui("youtube", "desc", video_id)
    found = {}
    for name, key in (("Spotify", "Spotify"), ("YouTube Music", "YouTube Music"), ("Apple Music", "Apple Music")):
        m = re.search(rf"▸ {name}:\s*(\S+)", desc)
        if m:
            found[key] = re.sub(r"[?&]si=[^&\s]+", "", m.group(1))
    return found


def main():
    songs = json.load(open(os.path.join(HERE, "songs", "index.json"), encoding="utf-8"))
    tracks = apple_tracks()
    mvs = mv_list()
    print(f"애플 곡 {len(tracks)}개 · MV {len(mvs)}개")
    for s in songs:
        d = os.path.join(HERE, "songs", s["dir"])
        try:
            chart = json.load(open(os.path.join(d, "chart.json"), encoding="utf-8"))
        except OSError:
            continue
        names = [chart.get("title"), chart.get("orig")]
        links = dict(LINKS)
        mv = next((v for v in mvs if any(norm(n) and norm(n) in norm(v[1]) for n in names)), None)
        if mv:
            links.update(mv_links(mv[0]))
        a = apple_link(tracks, names)
        if a:
            links["Apple Music"] = a
        got = [k for k in links if links[k] != LINKS.get(k)]
        json.dump(links, open(os.path.join(d, "links.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        chart["links"] = links
        json.dump(chart, open(os.path.join(d, "chart.json"), "w", encoding="utf-8"), ensure_ascii=False)
        print(f"  {s['title']:40s} {'MV ' + mv[0] if mv else '(MV 없음)':16s} 곡 링크: {', '.join(got) or '없음'}")


if __name__ == "__main__":
    sys.exit(main())
