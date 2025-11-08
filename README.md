# 🎵 ABC Composer

For those who want to try **composing / making music with ABC notation** —
this tool watches your `.abc` files and **renders them in real time** into **PDF** and **MP3** using MuseScore CLI.

It supports both **interleaved** and **regular** ABC formats.
Further features remain to be explored 🚀

---

## 🧩 Requirements

- Python ≥ 3.8
- [MuseScore 4](https://musescore.org) (CLI accessible as `mscore`)
Optional:
- `ffmpeg` – for MP3 export

---

## 🚀 Usage

Render all `.abc` files in real time:
```bash
python watch.py
```
Specify custom directories or options:

```bash
def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="watch_abc", description="Realtime ABC → MusicXML → PDF/MP3")
    ap.add_argument("--src", type=Path, default=ROOT, help="Source directory (default: script dir)")
    ap.add_argument("--out", type=Path, default=ROOT / "build", help="Output directory (default: ./build)")
    ap.add_argument("--mscore", type=str, default=None, help="MuseScore CLI path (overrides detection)")
    ap.add_argument("--python", type=str, default=sys.executable, help="Python executable to run abc2xml.py")
    ap.add_argument("--interval", type=float, default=2.0, help="Seconds between scans (default 2s)")
    ap.add_argument("--no-audio", action="store_true", help="Disable audio export")
    ap.add_argument("--quiet", action="store_true", help="Silent batch build (no tqdm)")
    return ap.parse_args()
```

---

## 📚 Resources

- [MIT Easy ABC Guide](https://trillian.mit.edu/~jc/music/abc/doc/ABC.html)  
- [NotABC Online Editor](https://notabc.app/abc/notation-songs-lyrics/)  
- [ABC Standard v2.1](https://abcnotation.com/wiki/abc:standard:v2.1#duplets_triplets_quadruplets_etc)  

Example datasets:
- 🎻 [Kunst der Fuge](https://www.kunstderfuge.com/) – Classical pieces  
- 🎵 [ABC Notation Collection](https://abcnotation.com/) – Folk and traditional tunes  

⸻

🪶 License
MIT License © 2025 Langchu Huang
