#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2025 Langchu Huang

import os
import sys
import time
import shutil
import argparse
import traceback
import subprocess
from tqdm import tqdm
from pathlib import Path
from typing import Optional, Tuple

ROOT = Path(__file__).resolve().parent
DEFAULT_MUSESCORE_PATHS = [
    "/Applications/MuseScore 4.app/Contents/MacOS/mscore",
    "/Applications/MuseScore 3.app/Contents/MacOS/mscore",
]

def find_musescore(explicit: Optional[str] = None) -> str:
    if explicit and Path(explicit).exists():
        return explicit
    env = os.environ.get("MUSESCORE")
    if env and Path(env).exists():
        return env
    for p in DEFAULT_MUSESCORE_PATHS:
        if Path(p).exists():
            return p
    which = shutil.which("mscore")
    if which:
        return which
    raise FileNotFoundError("MuseScore CLI not found. Set --mscore or $MUSESCORE.")

def run_cmd(cmd: list, timeout: int = 180) -> Tuple[str, str]:
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        out, err = p.communicate()
        raise RuntimeError(f"Timeout: {' '.join(cmd)}\n{err.decode('utf-8', 'ignore')}")
    if p.returncode != 0:
        raise RuntimeError(f"Failed: {' '.join(cmd)}\n{err.decode('utf-8', 'ignore')}")
    return out.decode("utf-8", "ignore"), err.decode("utf-8", "ignore")

def abc_to_musicxml(abc_path: Path, xml_path: Path, py: str) -> None:
    script = ROOT / "abc2xml.py"
    if not script.exists():
        raise FileNotFoundError(f"Missing abc2xml.py at {script}")
    out, _ = run_cmd([py, str(script), str(abc_path)])
    if not out.strip():
        raise RuntimeError(f"Empty MusicXML output: {abc_path}")
    xml_path.parent.mkdir(parents=True, exist_ok=True)
    xml_path.write_text(out, encoding="utf-8")

def musicxml_to_pdf(mscore_bin: str, xml_path: Path, pdf_path: Path) -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    run_cmd([mscore_bin, "-o", str(pdf_path), str(xml_path)])

def _convert_wav_to_mp3(wav_path: Path, mp3_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        run_cmd([ffmpeg, "-y", "-i", str(wav_path), str(mp3_path)])
        return
    afc = shutil.which("afconvert")
    if afc:
        tmp_aac = wav_path.with_suffix(".m4a")
        run_cmd([afc, "-f", "m4af", "-d", "aac", str(wav_path), str(tmp_aac)])
        tmp_aac.rename(mp3_path)
        return
    raise RuntimeError("No audio converter found (ffmpeg/afconvert).")

def musicxml_to_mp3(mscore_bin: str, xml_path: Path, mp3_path: Path) -> None:
    mp3_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        run_cmd([mscore_bin, "-o", str(mp3_path), str(xml_path)])
        return
    except Exception:
        wav_path = mp3_path.with_suffix(".wav")
        try:
            run_cmd([mscore_bin, "-o", str(wav_path), str(xml_path)])
            _convert_wav_to_mp3(wav_path, mp3_path)
        finally:
            if wav_path.exists():
                try:
                    wav_path.unlink()
                except Exception:
                    pass

def log_error(root: Path, src: Path, err: Exception) -> None:
    logs = root / "logs"
    logs.mkdir(exist_ok=True)
    with (logs / "watch_errors.log").open("a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {src}\n")
        f.write("".join(traceback.format_exception(err)))
        f.write("\n")

def compile_one(mscore_bin: str, py: str, abc_file: Path, out_dir: Path, root: Path, build_audio: bool) -> Optional[Path]:
    try:
        stem = abc_file.stem
        xml_path = out_dir / f"{stem}.musicxml"
        pdf_path = out_dir / f"{stem}.pdf"
        abc_to_musicxml(abc_file, xml_path, py)
        musicxml_to_pdf(mscore_bin, xml_path, pdf_path)
        if build_audio:
            mp3_path = out_dir / f"{stem}.mp3"
            musicxml_to_mp3(mscore_bin, xml_path, mp3_path)
            print(f"[OK] {abc_file.relative_to(root)} -> {pdf_path.relative_to(root)}, {mp3_path.relative_to(root)}")
        else:
            print(f"[OK] {abc_file.relative_to(root)} -> {pdf_path.relative_to(root)}")
        return pdf_path
    except Exception as e:
        print(f"[ERR] {abc_file.relative_to(root)}")
        log_error(root, abc_file, e)
        return None

def scan_and_build(mscore_bin: str, py: str, src_dir: Path, out_dir: Path, root: Path, build_audio: bool, state: dict) -> None:
    for p in src_dir.rglob("*.abc"):
        if not p.is_file():
            continue
        mtime = p.stat().st_mtime
        if p not in state or mtime > state[p]:
            compile_one(mscore_bin, py, p, out_dir, root, build_audio)
            state[p] = mtime

def batch_build(mscore_bin: str, py: str, src_dir: Path, out_dir: Path, root: Path, build_audio: bool, quiet: bool) -> dict:
    abc_files = [p for p in src_dir.rglob("*.abc") if p.is_file()]
    state = {}
    if not abc_files:
        print("No .abc found; watching…")
        return state
    if quiet:
        for p in abc_files:
            compile_one(mscore_bin, py, p, out_dir, root, build_audio)
            state[p] = p.stat().st_mtime
    else:
        print(f"Discovered {len(abc_files)} .abc files")
        for p in tqdm(abc_files):
            compile_one(mscore_bin, py, p, out_dir, root, build_audio)
            state[p] = p.stat().st_mtime
    return state

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

def main():
    args = parse_args()
    src_dir = args.src.resolve()
    out_dir = args.out.resolve()
    root = ROOT
    mscore_bin = find_musescore(args.mscore)
    build_audio = not args.no_audio
    print(f"MuseScore: {mscore_bin}")
    print(f"Source   : {src_dir}")
    print(f"Output   : {out_dir}")
    print(f"Audio    : {'on (MP3)' if build_audio else 'off'}")
    print(f"Interval : {args.interval}s")
    state = batch_build(mscore_bin, args.python, src_dir, out_dir, root, build_audio, quiet=args.quiet)
    print(f"Watching {src_dir} (check every {args.interval}s)  Ctrl+C to quit")
    try:
        while True:
            scan_and_build(mscore_bin, args.python, src_dir, out_dir, root, build_audio, state)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()
