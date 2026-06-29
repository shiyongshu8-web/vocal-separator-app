from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import uuid
import wave
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

APP_DIR = Path(__file__).resolve().parent
JOBS_DIR = APP_DIR / "jobs"
OUTPUTS_DIR = APP_DIR / "outputs"
MAX_UPLOAD_MB = 300
HOST = "127.0.0.1"
PORT = int(os.environ.get("VOCAL_SEPARATOR_PORT", "7860"))

HTML = r'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>人声与背景音分离</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #1d1d1f;
      --muted: #6e6e73;
      --line: rgba(0, 0, 0, .1);
      --panel: rgba(255, 255, 255, .82);
      --soft: rgba(255, 255, 255, .58);
      --accent: #0071e3;
      --accent-strong: #0077ed;
      --secondary: #424245;
      --danger: #d70015;
      --success-bg: #eaf7ee;
      --success-ink: #1d7f37;
      --shadow: 0 18px 42px rgba(0, 0, 0, .08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
      color: var(--ink);
      background: #f5f5f7;
      -webkit-font-smoothing: antialiased;
    }
    main { width: min(1120px, calc(100% - 32px)); margin: 0 auto; padding: 40px 0 54px; }
    header { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 20px; align-items: center; margin-bottom: 24px; }
    h1 { margin: 0 0 12px; font-size: clamp(34px, 5vw, 64px); line-height: .98; font-weight: 700; letter-spacing: 0; }
    .lede { margin: 0; max-width: 680px; color: var(--muted); font-size: 19px; line-height: 1.48; }
    .status-strip, .panel { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; box-shadow: var(--shadow); backdrop-filter: saturate(180%) blur(18px); }
    .status-strip { padding: 16px 18px; }
    .status-strip strong { display: block; margin-bottom: 6px; font-size: 15px; }
    .status-strip span { color: var(--muted); font-size: 13px; line-height: 1.5; }
    .layout { display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 16px; align-items: start; }
    form.panel { padding: 22px; }
    .drop { display: grid; place-items: center; min-height: 260px; border: 1px dashed rgba(0, 113, 227, .32); border-radius: 8px; background: linear-gradient(180deg, rgba(255,255,255,.7), rgba(250,250,252,.78)); text-align: center; padding: 28px; transition: border-color .18s ease, background .18s ease, transform .18s ease; cursor: pointer; }
    .drop:hover, .drop.dragging { border-color: var(--accent); background: #fff; transform: translateY(-1px); }
    .drop svg { width: 52px; height: 52px; margin-bottom: 18px; color: var(--accent); }
    .drop b { display: block; font-size: 21px; margin-bottom: 8px; font-weight: 650; }
    .drop span { color: var(--muted); line-height: 1.5; font-size: 14px; }
    input[type=file] { display: none; }
    .file-name { margin-top: 12px; min-height: 24px; color: var(--muted); font-size: 13px; overflow-wrap: anywhere; }
    .controls { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 16px; }
    label.field { display: block; background: rgba(255, 255, 255, .72); border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px; }
    label.field span { display: block; margin-bottom: 8px; color: var(--muted); font-size: 12px; font-weight: 600; }
    select { width: 100%; border: 0; background: transparent; color: var(--ink); font: inherit; outline: none; }
    .actions { display: flex; gap: 10px; align-items: center; margin-top: 16px; }
    button { appearance: none; border: 0; border-radius: 999px; background: var(--accent); color: white; min-height: 44px; padding: 0 20px; font: 600 15px/1 -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", "Microsoft YaHei", Arial, sans-serif; cursor: pointer; box-shadow: 0 8px 18px rgba(0, 113, 227, .2); transition: background .16s ease, transform .16s ease, opacity .16s ease; }
    button:hover { background: var(--accent-strong); transform: translateY(-1px); }
    button:disabled { opacity: .55; cursor: wait; }
    .hint { color: var(--muted); font-size: 13px; line-height: 1.45; }
    .side { padding: 18px; }
    .side h2, .results h2 { font-size: 17px; margin: 0 0 12px; font-weight: 650; }
    .side p { margin: 0 0 14px; color: var(--muted); line-height: 1.55; font-size: 14px; }
    .results { display: none; margin-top: 16px; padding: 18px; }
    .download-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
    .result-card { display: block; border: 1px solid var(--line); border-radius: 8px; padding: 16px; color: var(--ink); background: rgba(255, 255, 255, .7); }
    .result-card b { display: block; margin-bottom: 5px; font-weight: 650; }
    .result-card span { color: var(--muted); font-size: 13px; overflow-wrap: anywhere; }
    .download-button, .save-button { display: inline-flex; align-items: center; justify-content: center; min-height: 38px; margin-top: 10px; padding: 0 14px; border-radius: 999px; color: #fff; text-decoration: none; font-weight: 600; font-size: 14px; }
    .download-button { background: var(--accent); }
    .download-button:hover { background: var(--accent-strong); }
    .save-button { margin-right: 8px; background: var(--secondary); box-shadow: none; }
    .save-button:hover { background: #1d1d1f; }
    .save-path { display: none; margin-top: 10px; padding: 10px 12px; border-radius: 8px; background: rgba(0, 113, 227, .08); color: #005bb5; font-size: 13px; line-height: 1.5; overflow-wrap: anywhere; }
    audio { width: 100%; margin-top: 10px; }
    .message { display: none; margin-top: 14px; border-radius: 8px; padding: 12px 14px; background: var(--success-bg); color: var(--success-ink); line-height: 1.5; overflow-wrap: anywhere; }
    .message.error { background: #fff1f1; color: var(--danger); }
    @media (max-width: 820px) { header, .layout, .controls, .download-grid { grid-template-columns: 1fr; } main { width: min(100% - 22px, 680px); padding-top: 22px; } .drop { min-height: 210px; } }
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>人声与背景音分离</h1>
        <p class="lede">上传一段音频或视频，应用会输出独立的人声轨和背景/伴奏轨。已安装 Demucs 时会优先使用 AI 模型，否则使用快速 FFmpeg 算法。</p>
      </div>
      <div class="status-strip"><strong>本地处理</strong><span>文件保存在应用目录的 jobs 文件夹里，不会上传到外部服务。</span></div>
    </header>

    <div class="layout">
      <section>
        <form class="panel" id="form">
          <label class="drop" id="drop">
            <input id="file" name="audio" type="file" accept="audio/*,video/*">
            <div>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle></svg>
              <b>选择或拖入音频文件</b>
              <span>支持 mp3、wav、flac、m4a、mp4 等常见格式，单文件建议不超过 300 MB。</span>
            </div>
          </label>
          <div class="file-name" id="fileName"></div>
          <div class="controls">
            <label class="field"><span>分离模式</span><select name="mode" id="mode"><option value="auto">高质量优先：Demucs AI，失败后快速算法</option><option value="demucs">只用 Demucs AI（最干净，较慢）</option><option value="fast">快速算法（预览/兜底）</option></select></label>
            <label class="field"><span>输出格式</span><select name="format" id="format"><option value="wav">WAV 高兼容</option><option value="mp3">MP3 体积小</option></select></label>
          </div>
          <div class="actions"><button id="submit" type="submit">开始分离</button><span class="hint" id="progress">等待上传文件</span></div>
          <div class="message" id="message"></div>
        </form>
        <div class="panel results" id="results"><h2>处理结果</h2><div class="download-grid" id="downloads"></div></div>
      </section>
      <aside class="panel side"><h2>模式说明</h2><p><b>Demucs AI</b>：质量更好，适合歌曲、短视频配乐和人声提取；第一次使用可能需要下载模型。</p><p><b>快速算法</b>：无需模型，速度快；适合临时预览，但遇到单声道、非居中人声或复杂混音时效果较弱。</p><p>输出的人声与背景音都可以直接试听、下载或保存到本机。</p></aside>
    </div>
  </main>

  <script>
    const form = document.querySelector("#form");
    const fileInput = document.querySelector("#file");
    const fileName = document.querySelector("#fileName");
    const drop = document.querySelector("#drop");
    const submit = document.querySelector("#submit");
    const progress = document.querySelector("#progress");
    const message = document.querySelector("#message");
    const results = document.querySelector("#results");
    const downloads = document.querySelector("#downloads");
    function setMessage(text, isError = false) { message.textContent = text; message.className = isError ? "message error" : "message"; message.style.display = text ? "block" : "none"; }
    function refreshFileName() { const file = fileInput.files[0]; fileName.textContent = file ? `${file.name} · ${(file.size / 1024 / 1024).toFixed(1)} MB` : ""; progress.textContent = file ? "准备处理" : "等待上传文件"; }
    fileInput.addEventListener("change", refreshFileName);
    drop.addEventListener("dragover", (event) => { event.preventDefault(); drop.classList.add("dragging"); });
    drop.addEventListener("dragleave", () => drop.classList.remove("dragging"));
    drop.addEventListener("drop", (event) => { event.preventDefault(); drop.classList.remove("dragging"); if (event.dataTransfer.files.length) { fileInput.files = event.dataTransfer.files; refreshFileName(); } });
    form.addEventListener("submit", async (event) => {
      event.preventDefault(); setMessage(""); results.style.display = "none"; downloads.innerHTML = "";
      if (!fileInput.files.length) { setMessage("请先选择一个音频或视频文件。", true); return; }
      submit.disabled = true; progress.textContent = "正在上传并分离，长音频可能需要几分钟...";
      try {
        const response = await fetch("/api/separate", { method: "POST", body: new FormData(form) });
        const data = await response.json();
        if (!response.ok || !data.ok) throw new Error(data.error || "处理失败");
        progress.textContent = "处理完成"; setMessage(data.message || "分离完成。");
        downloads.innerHTML = data.files.map((item, index) => `<div class="result-card" data-index="${index}"><b>${item.label}</b><span>${item.name}</span><audio controls preload="metadata" src="${item.url}"></audio><button class="save-button" type="button" data-url="${item.url}">保存到本机</button><a class="download-button" href="${item.url}?download=1" download="${item.name}">下载</a><div class="save-path"></div></div>`).join("");
        results.style.display = "block";
      } catch (error) { progress.textContent = "处理失败"; setMessage(error.message, true); }
      finally { submit.disabled = false; }
    });
    downloads.addEventListener("click", async (event) => {
      const button = event.target.closest(".save-button"); if (!button) return;
      const pathBox = button.closest(".result-card").querySelector(".save-path");
      button.disabled = true; button.textContent = "正在保存..."; pathBox.style.display = "block"; pathBox.textContent = "正在写入本机输出目录...";
      try {
        const response = await fetch(`/api/save?url=${encodeURIComponent(button.dataset.url)}`);
        const data = await response.json();
        if (!response.ok || !data.ok) throw new Error(data.error || "保存失败");
        pathBox.textContent = `保存位置：${data.path}`; button.textContent = "已保存";
      } catch (error) { pathBox.textContent = error.message; button.textContent = "保存到本机"; }
      finally { button.disabled = false; }
    });
  </script>
</body>
</html>'''

class AppError(RuntimeError):
    pass

class SeparationWarning(RuntimeError):
    def __init__(self, message: str, vocals: Path, background: Path):
        super().__init__(message)
        self.vocals = vocals
        self.background = background

def json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)

def get_ffmpeg() -> str | None:
    bundled = APP_DIR / "bin" / "ffmpeg.exe"
    if bundled.exists():
        return str(bundled)
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None

def get_demucs_python() -> str:
    configured = os.environ.get("DEMUCS_PYTHON")
    if configured and Path(configured).exists():
        return configured
    for env_name in (".venv-demucs314", ".venv-ai"):
        candidate = APP_DIR / env_name / "Scripts" / "python.exe"
        if candidate.exists():
            return str(candidate)
    return sys.executable

def safe_suffix(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    allowed = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wma", ".mp4", ".mov", ".mkv", ".webm"}
    return suffix if suffix in allowed else ".audio"

def build_subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    bin_dir = APP_DIR / "bin"
    if bin_dir.exists():
        env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
    return env

def run_command(command: list[str], cwd: Path | None = None) -> None:
    process = subprocess.run(command, cwd=str(cwd) if cwd else None, env=build_subprocess_env(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    if process.returncode != 0:
        raise AppError(process.stdout[-3000:] or "外部命令执行失败。")

def run_command_output(command: list[str]) -> str:
    process = subprocess.run(command, env=build_subprocess_env(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    if process.returncode != 0:
        raise AppError(process.stdout[-3000:] or "外部命令执行失败。")
    return process.stdout

def get_audio_channels(ffmpeg: str, source: Path) -> int | None:
    ffprobe = Path(ffmpeg).with_name("ffprobe.exe")
    if not ffprobe.exists():
        return None
    output = run_command_output([str(ffprobe), "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=channels", "-of", "default=noprint_wrappers=1:nokey=1", str(source)]).strip()
    match = re.search(r"\d+", output)
    return int(match.group(0)) if match else None

def convert_audio(ffmpeg: str, source: Path, target: Path, audio_filter: str | None = None) -> None:
    command = [ffmpeg, "-y", "-i", str(source)]
    if audio_filter:
        command += ["-af", audio_filter]
    if target.suffix.lower() == ".mp3":
        command += ["-codec:a", "libmp3lame", "-b:a", "192k"]
    else:
        command += ["-codec:a", "pcm_s16le"]
    command.append(str(target))
    run_command(command)

def clamp_int16(value: float) -> int:
    return max(-32768, min(32767, int(value)))

def read_sample(frame: bytes, sample_width: int) -> int:
    if sample_width == 1:
        return (frame[0] - 128) << 8
    if sample_width == 2:
        return int.from_bytes(frame, "little", signed=True)
    if sample_width == 3:
        extended = frame + (b"\xff" if frame[2] & 0x80 else b"\x00")
        return int.from_bytes(extended, "little", signed=True) >> 8
    if sample_width == 4:
        return int.from_bytes(frame, "little", signed=True) >> 16
    raise AppError("内置 WAV 算法只支持 8/16/24/32-bit PCM WAV。")

def append_int16(target: bytearray, value: float) -> None:
    target.extend(clamp_int16(value).to_bytes(2, "little", signed=True))

def separate_wav_builtin(input_path: Path, out_dir: Path) -> tuple[Path, Path]:
    vocal_path = out_dir / "vocals_builtin.wav"
    background_path = out_dir / "background_builtin.wav"
    with wave.open(str(input_path), "rb") as source:
        channels = source.getnchannels()
        sample_width = source.getsampwidth()
        frame_rate = source.getframerate()
        raw = source.readframes(source.getnframes())
        if channels not in {1, 2}:
            raise AppError("内置 WAV 算法只支持单声道或双声道 WAV。")
    step = channels * sample_width
    vocals = bytearray()
    background = bytearray()
    for offset in range(0, len(raw), step):
        left = read_sample(raw[offset:offset + sample_width], sample_width)
        if channels == 1:
            append_int16(vocals, left)
            append_int16(background, 0)
            continue
        right = read_sample(raw[offset + sample_width:offset + 2 * sample_width], sample_width)
        append_int16(vocals, (left + right) / 2)
        append_int16(background, left - right)
        append_int16(background, right - left)
    with wave.open(str(vocal_path), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(frame_rate)
        target.writeframes(bytes(vocals))
    with wave.open(str(background_path), "wb") as target:
        target.setnchannels(1 if channels == 1 else 2)
        target.setsampwidth(2)
        target.setframerate(frame_rate)
        target.writeframes(bytes(background))
    return vocal_path, background_path

def separate_fast(input_path: Path, out_dir: Path, output_format: str) -> tuple[Path, Path]:
    ffmpeg = get_ffmpeg()
    if not ffmpeg:
        if input_path.suffix.lower() == ".wav" and output_format == "wav":
            return separate_wav_builtin(input_path, out_dir)
        raise AppError("没有找到 FFmpeg。WAV 文件可选择 WAV 输出使用内置算法；其他格式请安装依赖或把 ffmpeg 加入 PATH。")
    suffix = ".mp3" if output_format == "mp3" else ".wav"
    vocal_path = out_dir / f"vocals_fast{suffix}"
    background_path = out_dir / f"background_fast{suffix}"
    channels = get_audio_channels(ffmpeg, input_path)
    if channels == 1:
        convert_audio(ffmpeg, input_path, vocal_path)
        convert_audio(ffmpeg, input_path, background_path)
        raise SeparationWarning("源音频是单声道，快速算法无法真正分离；已输出可播放的原始音频。请使用 Demucs AI 获得更干净结果。", vocal_path, background_path)
    convert_audio(ffmpeg, input_path, vocal_path, "pan=mono|c0=0.5*FL+0.5*FR")
    convert_audio(ffmpeg, input_path, background_path, "pan=stereo|c0=FL-FR|c1=FR-FL")
    return vocal_path, background_path

def separate_demucs(input_path: Path, out_dir: Path, output_format: str) -> tuple[Path, Path]:
    run_command([get_demucs_python(), "-m", "demucs", "--two-stems", "vocals", "-n", "htdemucs", "-o", str(out_dir), str(input_path)])
    candidates = list(out_dir.glob("htdemucs/*/vocals.wav")) or list(out_dir.glob("*/**/vocals.wav"))
    if not candidates:
        raise AppError("Demucs 已运行，但没有找到 vocals.wav 输出。")
    vocals = candidates[0]
    no_vocals = vocals.with_name("no_vocals.wav")
    if not no_vocals.exists():
        raise AppError("Demucs 已运行，但没有找到 no_vocals.wav 输出。")
    if output_format == "wav":
        final_vocals = out_dir / "vocals_ai.wav"
        final_background = out_dir / "background_ai.wav"
        shutil.copy2(vocals, final_vocals)
        shutil.copy2(no_vocals, final_background)
        return final_vocals, final_background
    ffmpeg = get_ffmpeg()
    if not ffmpeg:
        raise AppError("Demucs 输出成功，但转换 MP3 需要 FFmpeg。")
    final_vocals = out_dir / "vocals_ai.mp3"
    final_background = out_dir / "background_ai.mp3"
    convert_audio(ffmpeg, vocals, final_vocals)
    convert_audio(ffmpeg, no_vocals, final_background)
    return final_vocals, final_background

def parse_upload(handler: BaseHTTPRequestHandler) -> tuple[bytes, str, str, str]:
    content_length = int(handler.headers.get("Content-Length", "0"))
    if content_length <= 0:
        raise AppError("上传内容为空。")
    if content_length > MAX_UPLOAD_MB * 1024 * 1024:
        raise AppError(f"文件太大，请上传不超过 {MAX_UPLOAD_MB} MB 的文件。")
    content_type = handler.headers.get("Content-Type", "")
    raw = handler.rfile.read(content_length)
    header = f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8")
    message = BytesParser(policy=default).parsebytes(header + raw)
    audio_bytes = b""
    filename = "input.audio"
    mode = "auto"
    output_format = "wav"
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if name == "audio":
            filename = part.get_filename() or filename
            audio_bytes = part.get_payload(decode=True) or b""
        elif name == "mode":
            mode = (part.get_payload(decode=True) or b"auto").decode("utf-8", "replace")
        elif name == "format":
            output_format = (part.get_payload(decode=True) or b"wav").decode("utf-8", "replace")
    if not audio_bytes:
        raise AppError("没有收到音频文件。")
    if mode not in {"auto", "demucs", "fast"}:
        mode = "auto"
    if output_format not in {"wav", "mp3"}:
        output_format = "wav"
    return audio_bytes, filename, mode, output_format

def handle_separate(handler: BaseHTTPRequestHandler) -> None:
    audio_bytes, filename, mode, output_format = parse_upload(handler)
    job_id = uuid.uuid4().hex[:12]
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    input_path = job_dir / f"input{safe_suffix(filename)}"
    input_path.write_bytes(audio_bytes)
    try:
        if mode in {"auto", "demucs"}:
            try:
                vocals, background = separate_demucs(input_path, job_dir, output_format)
                used = "Demucs AI"
            except Exception as exc:
                if mode == "demucs":
                    raise
                try:
                    vocals, background = separate_fast(input_path, job_dir, output_format)
                    used = f"快速算法（Demucs 不可用：{str(exc).strip().splitlines()[-1][:160]}）"
                except SeparationWarning as warning:
                    vocals, background = warning.vocals, warning.background
                    used = f"快速算法（{warning}）"
        else:
            try:
                vocals, background = separate_fast(input_path, job_dir, output_format)
                used = "快速算法"
            except SeparationWarning as warning:
                vocals, background = warning.vocals, warning.background
                used = f"快速算法（{warning}）"
        json_response(handler, HTTPStatus.OK, {"ok": True, "message": f"分离完成，使用模式：{used}", "files": [{"label": "人声", "name": vocals.name, "url": f"/jobs/{job_id}/{vocals.name}"}, {"label": "背景音 / 伴奏", "name": background.name, "url": f"/jobs/{job_id}/{background.name}"}]})
    except Exception as exc:
        json_response(handler, HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})

def resolve_job_file_from_url(file_url: str) -> Path:
    parsed = urlparse(file_url)
    if not parsed.path.startswith("/jobs/"):
        raise AppError("只能保存本应用生成的结果文件。")
    target = (JOBS_DIR / unquote(parsed.path.removeprefix("/jobs/"))).resolve()
    try:
        target.relative_to(JOBS_DIR.resolve())
    except ValueError:
        raise AppError("文件路径不合法。")
    if not target.is_file():
        raise AppError("结果文件不存在，请重新处理。")
    return target

def handle_save(handler: BaseHTTPRequestHandler, query: str) -> None:
    target = resolve_job_file_from_url(parse_qs(query).get("url", [""])[0])
    destination = OUTPUTS_DIR / target.relative_to(JOBS_DIR.resolve())
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, destination)
    json_response(handler, HTTPStatus.OK, {"ok": True, "path": str(destination.resolve())})

class Handler(BaseHTTPRequestHandler):
    server_version = "VocalSeparator/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            body = HTML.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/save":
            try:
                handle_save(self, parsed.query)
            except Exception as exc:
                json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
            return
        if parsed.path.startswith("/jobs/"):
            self.serve_job_file(parsed.path, download="download=1" in parsed.query)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_HEAD(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            body = HTML.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return
        if parsed.path.startswith("/jobs/"):
            self.serve_job_file(parsed.path, send_body=False, download="download=1" in parsed.query)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if urlparse(self.path).path == "/api/separate":
            handle_separate(self)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def serve_job_file(self, request_path: str, send_body: bool = True, download: bool = False) -> None:
        target = (JOBS_DIR / unquote(request_path.removeprefix("/jobs/"))).resolve()
        try:
            target.relative_to(JOBS_DIR.resolve())
        except ValueError:
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type = "audio/mpeg" if target.suffix.lower() == ".mp3" else "audio/wav"
        file_size = target.stat().st_size
        start, end, status = 0, file_size - 1, HTTPStatus.OK
        range_header = self.headers.get("Range")
        if range_header:
            match = re.match(r"bytes=(\d*)-(\d*)", range_header)
            if match:
                if match.group(1):
                    start = int(match.group(1))
                if match.group(2):
                    end = int(match.group(2))
                if start >= file_size:
                    self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                    self.send_header("Content-Range", f"bytes */{file_size}")
                    self.end_headers()
                    return
                end = min(end, file_size - 1)
                status = HTTPStatus.PARTIAL_CONTENT
        length = max(0, end - start + 1)
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Disposition", f'{"attachment" if download else "inline"}; filename="{target.name.replace(chr(34), "")}"')
        self.send_header("Content-Length", str(length))
        if status == HTTPStatus.PARTIAL_CONTENT:
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        self.end_headers()
        if send_body:
            with target.open("rb") as file:
                file.seek(start)
                self.wfile.write(file.read(length))

    def log_message(self, format: str, *args: object) -> None:
        print("%s - %s" % (self.address_string(), format % args))

def main() -> None:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"人声分离应用已启动：http://{HOST}:{PORT}")
    print("按 Ctrl+C 停止服务。")
    server.serve_forever()

if __name__ == "__main__":
    main()
