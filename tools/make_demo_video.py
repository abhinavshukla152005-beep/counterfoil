"""Build the Round 1 demo video from real command output.

Every frame is a replay of output captured in outputs/demo_capture/, so the
video shows the commands actually running, not a mock. Narration is
text-to-speech; there is no camera and no edited claims.

    python tools/make_demo_video.py
    -> outputs/demo/counterfoil-demo.mp4   (1920x1080, 30 fps, < 3 min)
"""
from __future__ import annotations

import asyncio
import hashlib
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
CAP = ROOT / "outputs" / "demo_capture"
OUT = ROOT / "outputs" / "demo"
BUILD = OUT / "_build"

W, H, FPS = 1920, 1080, 30
VOICE = "en-IN-PrabhatNeural"
PAD = 0.55

BG = (13, 17, 23)
PANEL = (22, 27, 34)
BAR = (33, 38, 45)
LINE = (48, 54, 61)
TEXT = (201, 209, 217)
DIM = (139, 148, 158)
GREEN = (126, 231, 135)
PURPLE = (210, 168, 255)
ORANGE = (255, 166, 87)
BLUE = (88, 166, 255)
GOLD = (240, 183, 47)

BODY = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 24)
BODY_B = ImageFont.truetype(r"C:\Windows\Fonts\consolab.ttf", 24)
BAR_F = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 18)
SB = r"C:\Windows\Fonts\seguisb.ttf"
CARD_T = ImageFont.truetype(SB, 92)
CARD_S = ImageFont.truetype(SB, 34)
CARD_B = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 26)
CARD_M = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 28)

SANTISE = (
    r"C:\Users\Abhinav Shukla\Documents\Qoder\2026-11-21\5722a3d6\agentx" + "\\",
    r"C:\Users\Abhinav Shukla\Documents\Qoder\2026-11-21\5722a3d6\agentx",
)

SEGMENTS = [
    {
        "kind": "card", "secs": 4.0, "say": None,
        "title": "COUNTERFOIL", "sub": "A seller agent whose free text never reaches a price",
        "foot": "AgentX · Challenge 2, Selling to Machines · Techfest IIT Bombay × Rezolve Labs",
    },
    {
        "cmd": "python -m src.demo --list", "out": "01_list.txt",
        "say": "Counterfoil is a seller agent for machine buyers. The buyer is a bot that will "
               "say anything for a better price, so the seller never reads the text. "
               "It prices from a ledger, and every number is checked against that "
               "ledger before the offer goes out. Six buyer policies, including a "
               "manipulator and a fuzzer.",    },
    {
        "cmd": "python run_official.py", "out": "02_official.txt",
        "say": "This is the judges' starter kit, running unchanged. My seller implements the "
               "Seller class their evaluate expects: two hundred and ten negotiations "
               "across three buyer types, scored with their code, then their example "
               "seller on the same baskets. Score fifty one point six, against forty "
               "eight point five. Zero policy violations, zero unprovable claims, zero "
               "deadlocks. Their example seller deadlocks twenty one times.",    },
    {
        "cmd": "python -m src.demo --bot manipulator --seed 3", "out": "03_manipulator.txt",
        "say": "Here is the adversarial buyer. It claims a competitor quoted thirty four fifty "
               "five, that a manager already approved a price, that the order expires in "
               "ninety seconds, then it tries a system override. The seller's offers "
               "never leave their own schedule, and every claim is verified eight out of "
               "eight against the ledger. The lies cost nothing, because they never "
               "enter the decision.",    },
    {
        "cmd": "python -m src.demo --parity --seed 3", "out": "04_parity.txt", "head": 99, "tail": 99,
        "say": "Same seed, same basket: honest buyer on the left, manipulator on the right. "
               "Identical on every offer, and an identical final price, because the text "
               "is never parsed.",    },
    {
        "cmd": "python -m src.demo --bot lowballer --seed 2", "out": "05_lowballer.txt",
        "head": 6, "tail": 7,
        "say": "Below the floor, the answer is no deal. The buyer anchors forty five percent off "
               "and never moves. The seller holds at eleven thousand eight hundred, and "
               "walks at round ten, because the floor was ten thousand five hundred and "
               "ninety six.",    },
    {
        "cmd": "python -m src.demo --bot cooperative --seed 5", "out": "06_cooperative.txt",
        "say": "When the deal is real it closes above the floor, not at it: four thousand two "
               "hundred and sixty nine, against a floor of three thousand six hundred "
               "and fifty five.",    },
    {
        "cmd": "python tests/test_official_seller.py", "out": "07_tests.txt",
        "say": "Eleven invariant tests on the official interface: floor absolute, text never "
               "read, extra lines never accepted, stock clamped, and the final round "
               "either closes or walks.",    },
    {
        "cmd": "python run_all.py", "out": "08_runall.txt", "head": 0, "tail": 12,
        "say": "The stress harness: sixteen properties, all passing. Malformed counters are "
               "rejected with typed errors, and the negotiation stays alive.",    },
    {
        "kind": "card", "secs": 13.0,
        "say": "No model on the decision path, so zero inference cost per turn, and the official "
               "run finishes in under two seconds. Every number is regenerated by one "
               "command from the transcripts.",        "title": "51.6", "sub": "official kit score, example seller 48.5",
        "foot": "policy violations 0 · truth violations 0 · deadlocks 0\n"
                "github.com/abhinavshukla152005-beep/counterfoil",
    },
]


def sanitise(text: str) -> str:
    for s in SANTISE:
        text = text.replace(s, "")
    return text


def load_out(name: str, head: int, tail: int) -> list[str]:
    raw = (CAP / name).read_text(encoding="utf-8", errors="replace").splitlines()
    lines = [sanitise(l.rstrip()) for l in raw]
    while lines and not lines[-1].strip():
        lines.pop()
    while lines and not lines[0].strip():
        lines.pop(0)
    if head or tail:
        if head == 0:
            lines = ["   … (earlier output omitted for length) …"] + lines[-tail:]
        elif len(lines) > head + tail:
            lines = lines[:head] + ["   … (rounds omitted, pattern identical) …"] + lines[-tail:]
    return lines


def colour(line: str) -> tuple:
    s = line.strip()
    if s.startswith('"'):
        return PURPLE, BODY
    if "SELLER offers" in line or "claims verified" in line:
        return GREEN, BODY
    if "BUYER" in line:
        return ORANGE, BODY
    if s.startswith("ok "):
        return GREEN, BODY
    if s.startswith("…") or s.startswith("   …"):
        return DIM, BODY
    if "unavailable" in line:
        return DIM, BODY
    if any(k in line for k in ("IDENTICAL", "DEAL at", "NO DEAL", "SCORE", "11/11", "16/16", "All steps passed")):
        return GOLD, BODY_B
    if any(k in line for k in ("violations", "deadlocks", "deal rate", "margin kept", "negotiations")):
        return TEXT, BODY_B
    if "wrote" in line:
        return DIM, BODY
    if s.startswith(("buyer policy", "verifier", "basket", "seed", "final")):
        return BLUE, BODY
    return TEXT, BODY


def wrap(text: str, font, width: int) -> list[str]:
    if not text:
        return [""]
    out, cur = [], ""
    for ch in text:
        if font.getlength(cur + ch) > width and cur:
            out.append(cur)
            cur = " " + ch if ch != " " else ""
        else:
            cur += ch
    out.append(cur)
    return out


def terminal(lines: list[str], prompt: str = "", typed: str = "", cursor: bool = False) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((40, 28, W - 40, H - 28), 14, fill=PANEL, outline=LINE, width=2)
    d.rounded_rectangle((40, 28, W - 40, 82), 14, fill=BAR)
    d.rectangle((40, 68, W - 40, 82), fill=BAR)
    for i, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        d.ellipse((68 + i * 26, 46, 82 + i * 26, 60), fill=c)
    d.text((W // 2, 55), "counterfoil  —  AgentX Round 1", font=BAR_F, fill=DIM, anchor="mm")

    x, y, maxw = 74, 118, W - 40 - 74 - 30
    rows = 0
    if prompt:
        d.text((x, y), prompt, font=BODY_B, fill=BLUE)
        px = x + BODY_B.getlength(prompt)
        d.text((px, y), typed, font=BODY_B, fill=(240, 246, 252))
        cx = px + BODY_B.getlength(typed)
        if cursor:
            d.rectangle((cx + 2, y + 1, cx + 14, y + 27), fill=TEXT)
        y += 34
        rows += 1
    for line in lines:
        col, font = colour(line)
        for piece in wrap(line, font, maxw):
            if y > H - 76:
                break
            d.text((x, y), piece, font=font, fill=col)
            y += 30
            rows += 1
    return img


def card(title: str, sub: str, foot: str) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W, 6), fill=GOLD)
    d.text((W // 2, 300), title, font=CARD_T, fill=(240, 246, 252), anchor="mm")
    d.text((W // 2, 420), sub, font=CARD_S, fill=GOLD, anchor="mm")
    y = 520
    for ln in foot.split("\n"):
        d.text((W // 2, y), ln, font=CARD_B, fill=DIM, anchor="mm")
        y += 46
    d.text((W // 2, H - 90), "built solo · standard library only · no model on the decision path",
           font=CARD_B, fill=(90, 98, 108), anchor="mm")
    return img


def audio(text: str, tag: str) -> Path:
    key = hashlib.sha1((VOICE + text).encode()).hexdigest()[:12]
    mp3 = BUILD / f"say_{tag}_{key}.mp3"
    if mp3.exists() and mp3.stat().st_size > 1000:
        return mp3
    import edge_tts

    async def go():
        await edge_tts.Communicate(text, VOICE, rate="+4%").save(str(mp3))

    asyncio.run(go())
    return mp3


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def main() -> int:
    BUILD.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    plan: list[dict] = []
    wavs: list[Path] = []
    total = 0.0

    for i, seg in enumerate(SEGMENTS):
        tag = f"{i:02d}"
        if seg.get("kind") == "card":
            if seg.get("say"):
                mp3 = audio(seg["say"], tag)
                length = duration(mp3) + 1.0
                wav = BUILD / f"seg_{tag}.wav"
                subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(mp3), "-af",
                                f"apad=whole_dur={length}", "-ar", "48000", "-ac", "1",
                                str(wav)], check=True)
                wavs.append(wav)
            else:
                length = float(seg["secs"])
                wav = BUILD / f"seg_{tag}.wav"
                subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                                "anullsrc=r=48000:cl=mono", "-t", f"{length}",
                                str(wav)], check=True)
                wavs.append(wav)
            plan.append({"kind": "card", "secs": length, "seg": seg, "start": total})
            total += length
            continue

        mp3 = audio(seg["say"], tag)
        spoken = duration(mp3)
        length = spoken + PAD
        wav = BUILD / f"seg_{tag}.wav"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(mp3), "-af",
                        f"apad=whole_dur={length}", "-ar", "48000", "-ac", "1",
                        str(wav)], check=True)
        wavs.append(wav)
        lines = load_out(seg["out"], seg.get("head", 99), seg.get("tail", 99))
        plan.append({"kind": "term", "secs": length, "seg": seg, "lines": lines, "start": total})
        total += length

    print(f"narration total {total:.1f}s across {len(plan)} segments")
    if total >= 180:
        print("ERROR: over three minutes", file=sys.stderr)
        return 1

    listing = BUILD / "audio_list.txt"
    listing.write_text("".join(f"file '{w.as_posix()}'\n" for w in wavs), encoding="utf-8")
    narration = BUILD / "narration.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                    "-i", str(listing), "-c", "copy", str(narration)], check=True)

    out_mp4 = OUT / "counterfoil-demo.mp4"
    enc = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", str(narration),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart",
         str(out_mp4)],
        stdin=subprocess.PIPE,
    )

    prompt = "counterfoil> "
    cache: dict = {}
    frames = 0
    for item in plan:
        n = max(1, round(item["secs"] * FPS))
        if item["kind"] == "card":
            seg = item["seg"]
            key = ("card", seg["title"], seg["sub"], seg["foot"])
            if key not in cache:
                cache[key] = card(seg["title"], seg["sub"], seg["foot"])
            img = cache[key]
            for _ in range(n):
                enc.stdin.write(img.tobytes())
                frames += 1
            continue

        lines, cmd = item["lines"], item["seg"]["cmd"]
        type_frames = max(int(0.5 * FPS), min(int(1.3 * FPS), int(len(cmd) * 0.035 * FPS)))
        gap_frames = int(0.35 * FPS)
        avail = max(1, n - type_frames - gap_frames - int(0.5 * FPS))
        step = min(avail * 0.62 / max(1, len(lines)), 0.8 * FPS)
        reveal_at = [type_frames + gap_frames + int(i * step) for i in range(len(lines))]

        for f in range(n):
            typed = cmd if f >= type_frames else cmd[: int(len(cmd) * f / type_frames)]
            shown = [lines[i] for i in range(len(lines)) if f >= reveal_at[i]]
            cursor = (f % 16) < 9
            key = (tuple(shown), typed, cursor if len(shown) == len(lines) else False)
            if key not in cache:
                cache[key] = terminal(shown, prompt, typed, cursor=key[2])
            enc.stdin.write(cache[key].tobytes())
            frames += 1

    enc.stdin.close()
    enc.wait()
    if enc.returncode != 0:
        return enc.returncode

    print(f"wrote {out_mp4}  ({frames} frames, {total:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
