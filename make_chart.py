"""수이 노래 → 4줄 리듬게임 채보 자동 생성 (PoC, 10/10 새벽)

곡 폴더의 스템(반주·보컬)을 쓴다:
  D 줄 = 킥(반주 타악 성분의 저음)   F 줄 = 스네어·클랩(중음)
  J 줄 = 하이햇·글리치(고음)         K 줄 = 보컬이 새로 시작하는 곳
박자 격자(16분음표)에 붙이고, 세기 순으로 솎아서 easy·normal·hard 세 판을 만든다.

사용: python make_chart.py "<곡 폴더>" <출력 폴더>
"""
import json
import os
import shutil
import subprocess
import sys

import librosa
import numpy as np

SR, HOP = 22050, 256
# 줄마다 (주파수 대역 Hz, 검출 민감도 delta, 같은 줄 최소 간격 초)
LANES = [
    {"name": "kick", "band": (20, 150), "delta": 0.10, "gap": 0.16},
    {"name": "snare", "band": (150, 3000), "delta": 0.12, "gap": 0.16},
    {"name": "hat", "band": (5000, 11000), "delta": 0.16, "gap": 0.20},
    {"name": "vocal", "band": None, "delta": 0.10, "gap": 0.24},
]
NPS = {"easy": 1.6, "normal": 3.0, "hard": 5.0}   # 초당 노트 수 목표
SNAP_SEC = 0.07                                    # 격자에서 이만큼 안이면 붙인다
MP3_KBPS = 128                                     # 게임용은 낮춰서 — 제대로 들으려면 스트리밍으로 (여보 10/10 "128k 좋네")
LINKS = {   # 끝나면 "전체 듣기" — docs/music/links.md 아티스트 링크 (곡별 링크가 생기면 바꾸기)
    "YouTube Music": "https://music.youtube.com/channel/UCh6IQqJHm0Dk79bjjbhGGqA",
    "Spotify": "https://open.spotify.com/artist/7BVjFakbaPAKmnCxJuItkU",
    "Apple Music": "https://music.apple.com/kr/artist/sui/1887834805",
}


def find_stems(song_dir):
    """stems_c → b → a 폴더, 없으면 곡 폴더에 바로 있는 '0 Lead Vocals…'·'1 Instrumental…' (같은 꼬리 (2) 짝 우선)"""
    for sub in ("stems_c", "stems_b", "stems_a", "."):
        d = os.path.join(song_dir, sub)
        if not os.path.isdir(d):
            continue
        files = sorted(os.listdir(d), reverse=True)          # '(2)'가 앞으로
        vocs = [f for f in files if "lead vocals" in f.lower() and f.lower().endswith(".wav")]
        insts = [f for f in files if f.lower().startswith("1 instrumental") and f.lower().endswith(".wav")] if sub == "." else \
                [f for f in files if "instrumental" in f.lower()]
        for v in vocs:
            tail = v.lower().split("vocals", 1)[1]
            inst = next((i for i in insts if i.lower().split("instrumental", 1)[1] == tail), insts[0] if insts else None)
            if inst:
                return os.path.join(d, inst), os.path.join(d, v)
    return None, None      # 연주곡(보컬 없음) — 원곡 하나로, K줄은 멜로디(화성 성분)가 새로 나오는 곳


def find_mix(song_dir):
    """원곡 — '<폴더명>.wav|mp3', 없으면 폴더명으로 시작하는 wav·mp3 중 반주·마스터링·보컬 아닌 것 (가만히 안아줘 (Hold Me Quietly).wav 같은)"""
    title = os.path.basename(os.path.normpath(song_dir))
    for name in (f"{title}.wav", f"{title}.mp3"):
        p = os.path.join(song_dir, name)
        if os.path.exists(p):
            return p
    skip = ("instrumental", "remaster", "master", "vocals")
    for f in sorted(os.listdir(song_dir)):
        lf = f.lower()
        if f.startswith(title) and lf.endswith((".wav", ".mp3")) and not any(k in lf for k in skip):
            return os.path.join(song_dir, f)
    raise SystemExit(f"원곡이 없어: {song_dir}")


def band_envelope(S, freqs, band):
    lo, hi = band
    rows = (freqs >= lo) & (freqs < hi)
    return librosa.onset.onset_strength(S=librosa.power_to_db(S[rows]), sr=SR, hop_length=HOP)


def detect(env, delta, gap):
    frames = librosa.onset.onset_detect(onset_envelope=env, sr=SR, hop_length=HOP, delta=delta,
                                        wait=max(1, int(gap * SR / HOP)), units="frames")
    norm = env / (env.max() or 1)
    return [(float(librosa.frames_to_time(f, sr=SR, hop_length=HOP)), float(norm[f])) for f in frames]


def grid_from_beats(beats, duration):
    """박자 사이를 4등분한 16분음표 격자 (첫 박 앞·끝 박 뒤는 중간 간격으로 늘림)"""
    step = float(np.median(np.diff(beats))) if len(beats) > 1 else 0.5
    pts = []
    t = beats[0]
    while t > 0:
        t -= step
    t += step
    allb = list(np.arange(t, beats[0], step)) + list(beats)
    last = allb[-1]
    while last + step < duration:
        last += step
        allb.append(last)
    for a, b in zip(allb, allb[1:]):
        pts.extend(a + (b - a) * k / 4 for k in range(4))
    return np.array(pts), 60.0 / step


def snap(t, grid):
    i = int(np.argmin(np.abs(grid - t)))
    return float(grid[i]) if abs(grid[i] - t) <= SNAP_SEC else t


def thin(notes, nps, duration):
    """세기 순으로 목표 개수만 남기되, 같은 순간 3개 이상·너무 붙은 연타는 뺀다"""
    keep_n = int(nps * duration)
    chosen, per_time, last_any = [], {}, []
    for t, lane, s in sorted(notes, key=lambda n: -n[2]):
        if len(chosen) >= keep_n:
            break
        key = round(t, 3)
        if per_time.get(key, 0) >= 2:
            continue
        # 다른 순간과 0.09초 안이면(동시 아닌데 너무 붙음) 건너뜀
        if any(0 < abs(t - u) < 0.09 for u in last_any):
            continue
        chosen.append((t, lane))
        per_time[key] = per_time.get(key, 0) + 1
        last_any.append(t)
    return sorted([round(t, 3), lane] for t, lane in chosen)


def main(song_dir, out_dir, display_title=None):
    inst_path, voc_path = find_stems(song_dir)
    if inst_path:
        print("스템:", os.path.relpath(inst_path, song_dir), "/", os.path.basename(voc_path))
        y_inst, _ = librosa.load(inst_path, sr=SR, mono=True)
        y_voc, _ = librosa.load(voc_path, sr=SR, mono=True)
        _, y_perc = librosa.effects.hpss(y_inst)
    else:
        print("스템 없음 — 연주곡으로: 원곡 하나에서 타악·멜로디를 나눔")
        y_inst, _ = librosa.load(find_mix(song_dir), sr=SR, mono=True)
        y_voc, y_perc = librosa.effects.hpss(y_inst)          # 화성(멜로디) 성분이 K줄 자리
    duration = len(y_inst) / SR
    _, beats = librosa.beat.beat_track(y=y_inst, sr=SR, hop_length=HOP, units="time")
    grid, bpm = grid_from_beats(beats, duration)
    print(f"길이 {duration:.1f}초 · BPM {bpm:.1f} · 격자 {len(grid)}칸")

    S = np.abs(librosa.stft(y_perc, hop_length=HOP)) ** 2
    freqs = librosa.fft_frequencies(sr=SR)
    raw = []
    for i, ln in enumerate(LANES):
        if ln["band"]:
            env = band_envelope(S, freqs, ln["band"])
        else:
            env = librosa.onset.onset_strength(y=y_voc, sr=SR, hop_length=HOP)
        hits = detect(env, ln["delta"], ln["gap"])
        print(f"  {ln['name']:6s} {len(hits)}개")
        raw.extend((snap(t, grid), i, s) for t, s in hits if t > 0.5)

    # 같은 줄·같은 칸 중복 제거(센 쪽)
    best = {}
    for t, lane, s in raw:
        k = (round(t, 3), lane)
        if s > best.get(k, (0, 0, -1))[2]:
            best[k] = (t, lane, s)
    notes = list(best.values())

    charts = {lv: thin(notes, nps, duration) for lv, nps in NPS.items()}
    for lv, c in charts.items():
        print(f"  {lv:6s} {len(c)}노트 ({len(c) / duration:.1f}/초)")

    os.makedirs(out_dir, exist_ok=True)
    links = dict(LINKS)
    try:   # 곡별 링크(유튜브 MV 설명에서 찾은 것)가 있으면 그걸로 — songs/<곡>/links.json
        links.update(json.load(open(os.path.join(out_dir, "links.json"), encoding="utf-8")))
    except (OSError, ValueError):
        pass
    title = os.path.basename(os.path.normpath(song_dir))       # 폴더명 = 파일 이름 열쇠
    with open(os.path.join(out_dir, "chart.json"), "w", encoding="utf-8") as f:
        json.dump({"title": display_title or title, "orig": title if display_title and display_title != title else "", "artist": "Sui", "bpm": round(bpm, 1), "duration": round(duration, 2),
                   "beats": [round(float(b), 3) for b in beats],      # 배경 하트비트용
                   "links": links, "lanes": [l["name"] for l in LANES], "charts": charts}, f, ensure_ascii=False)
    # 재생용 mp3 — 원본 wav에서 128k로 (원본·스템·Remastered는 안 내보냄)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", find_mix(song_dir), "-vn", "-b:a", f"{MP3_KBPS}k",
                    os.path.join(out_dir, "song.mp3")], check=True)
    # 배경(1920 이하)·커버(512)는 줄여서 JPEG로 — 원본은 안 내보냄. 영어 가사는 그대로
    from PIL import Image
    bg_src = next((f for f in ("wallpaper.png", "wallpaper.jpeg", "wallpaper.jpg") if os.path.exists(os.path.join(song_dir, f))), "cover.jpg")   # 월페이퍼 없는 곡은 커버로
    for src, dst, size in ((bg_src, "bg.jpg", 1920), ("cover.jpg", "cover.jpg", 512)):
        p = os.path.join(song_dir, src)
        if os.path.exists(p):
            im = Image.open(p).convert("RGB")
            im.thumbnail((size, size), Image.LANCZOS)
            im.save(os.path.join(out_dir, dst), "JPEG", quality=85, optimize=True)
    for old in ("bg.png",):
        if os.path.exists(os.path.join(out_dir, old)):
            os.remove(os.path.join(out_dir, old))
    p = os.path.join(song_dir, "lyrics_en.srt")
    if os.path.exists(p):
        shutil.copyfile(p, os.path.join(out_dir, "lyrics.srt"))
    print("저장:", out_dir)
    # 곡 목록(songs/index.json)에 이 곡을 넣거나 갱신
    idx_path = os.path.join(os.path.dirname(os.path.normpath(out_dir)), "index.json")
    try:
        songs = json.load(open(idx_path, encoding="utf-8"))
    except (OSError, ValueError):
        songs = []
    entry = {"dir": os.path.basename(os.path.normpath(out_dir)), "title": display_title or title}
    songs = [s for s in songs if s["dir"] != entry["dir"]] + [entry]
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(songs, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    # python make_chart.py "<곡 폴더>" songs/<이름> ["보일 영어 제목"]
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
