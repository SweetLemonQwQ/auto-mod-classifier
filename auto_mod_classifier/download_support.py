import json
import threading
import time
import urllib.request
from collections import deque
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Sequence, Union

from .shared import DOWNLOAD_SOURCE_DOMESTIC, USER_AGENT

DEFAULT_DOWNLOAD_WORKERS = 6
_PROGRESS_UPDATE_INTERVAL_SECONDS = 0.25
_PROGRESS_SAMPLE_WINDOW_SECONDS = 2.0


def format_bytes(size: float) -> str:
    """把字节数格式化成更容易读的文本。"""
    value = float(max(size, 0.0))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024.0 or unit == "TB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return "0 B"


def build_download_status_text(speed_bytes: float, active_count: int, thread_limit: int, completed_count: int, total_count: int) -> str:
    """统一下载状态文案，供界面直接显示。"""
    return (
        f"当前网速：{format_bytes(speed_bytes)}/s | "
        f"下载线程：{max(active_count, 0)}/{max(thread_limit, 0)} | "
        f"已完成：{max(completed_count, 0)}/{max(total_count, 0)}"
    )


def build_idle_download_status_text() -> str:
    return build_download_status_text(0.0, 0, 0, 0, 0)


def choose_download_worker_count(total_files: int) -> int:
    return min(DEFAULT_DOWNLOAD_WORKERS, max(1, total_files))


def rewrite_download_url(url: str, download_source: str) -> str:
    """按用户选择切换官方源或国内镜像。"""
    if download_source != DOWNLOAD_SOURCE_DOMESTIC:
        return url

    replacements = (
        ("https://api.modrinth.com/", "https://mod.mcimirror.top/modrinth/"),
        ("https://cdn.modrinth.com/", "https://mod.mcimirror.top/"),
        ("https://api.curseforge.com/", "https://mod.mcimirror.top/curseforge/"),
        ("https://edge.forgecdn.net/", "https://mod.mcimirror.top/"),
        ("https://mediafilez.forgecdn.net/", "https://mod.mcimirror.top/"),
        ("http://edge.forgecdn.net/", "https://mod.mcimirror.top/"),
        ("http://mediafilez.forgecdn.net/", "https://mod.mcimirror.top/"),
        ("https://meta.fabricmc.net/", "https://bmclapi2.bangbang93.com/fabric-meta/"),
        ("https://maven.fabricmc.net/", "https://bmclapi2.bangbang93.com/maven/"),
        ("https://maven.minecraftforge.net/", "https://bmclapi2.bangbang93.com/maven/"),
        ("https://maven.neoforged.net/releases/", "https://bmclapi2.bangbang93.com/maven/"),
    )
    for before, after in replacements:
        if url.startswith(before):
            return after + url[len(before) :]
    return url


def build_download_candidates(urls: Union[str, Sequence[str]], download_source: str) -> list[str]:
    """把官方地址和镜像地址按优先级展开，并去重。"""
    raw_urls = [urls] if isinstance(urls, str) else list(urls)
    candidates: list[str] = []
    seen: set[str] = set()
    for url in raw_urls:
        if not url:
            continue
        expanded = (rewrite_download_url(url, download_source), url)
        for candidate in expanded:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            candidates.append(candidate)
    return candidates


class DownloadStatsReporter:
    """聚合多个下载任务的网速和线程状态，给界面做实时展示。"""

    def __init__(self, emit_status: Optional[Callable[[str], None]], total_files: int, thread_limit: int):
        self.emit_status = emit_status
        self.total_files = max(0, total_files)
        self.thread_limit = max(0, thread_limit)
        self.active_files = 0
        self.completed_files = 0
        self.downloaded_bytes = 0
        self._lock = threading.Lock()
        self._last_emit_at = 0.0
        self._samples: deque[tuple[float, int]] = deque()

    def start_file(self) -> None:
        with self._lock:
            self.active_files += 1
            self._emit_locked(force=True)

    def add_bytes(self, size: int) -> None:
        if size <= 0:
            return
        with self._lock:
            self.downloaded_bytes += size
            self._emit_locked(force=False)

    def finish_file(self) -> None:
        with self._lock:
            self.active_files = max(0, self.active_files - 1)
            self.completed_files += 1
            self._emit_locked(force=True)

    def fail_file(self) -> None:
        with self._lock:
            self.active_files = max(0, self.active_files - 1)
            self._emit_locked(force=True)

    def close(self) -> None:
        with self._lock:
            self.active_files = 0
            self._samples.clear()
            self._last_emit_at = 0.0
        self._emit_text(build_idle_download_status_text())

    def _emit_text(self, text: str) -> None:
        if callable(self.emit_status):
            self.emit_status(text)

    def _emit_locked(self, force: bool) -> None:
        if not callable(self.emit_status):
            return

        now = time.monotonic()
        if not force and now - self._last_emit_at < _PROGRESS_UPDATE_INTERVAL_SECONDS:
            return

        self._samples.append((now, self.downloaded_bytes))
        while len(self._samples) > 1 and now - self._samples[0][0] > _PROGRESS_SAMPLE_WINDOW_SECONDS:
            self._samples.popleft()

        speed_bytes = 0.0
        if self.active_files > 0 and len(self._samples) >= 2:
            start_time, start_bytes = self._samples[0]
            duration = now - start_time
            if duration > 0:
                speed_bytes = (self.downloaded_bytes - start_bytes) / duration

        self._last_emit_at = now
        text = build_download_status_text(
            speed_bytes=speed_bytes,
            active_count=self.active_files,
            thread_limit=self.thread_limit,
            completed_count=self.completed_files,
            total_count=self.total_files,
        )
        self._emit_text(text)


def http_get_text(url: str, download_source: str, timeout: int = 45) -> str:
    last_error: Optional[Exception] = None
    for candidate in build_download_candidates(url, download_source):
        try:
            req = urllib.request.Request(candidate, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"获取文本失败：{url}\n{last_error}")


def http_get_json(url: str, download_source: str, timeout: int = 45) -> Any:
    last_error: Optional[Exception] = None
    for candidate in build_download_candidates(url, download_source):
        try:
            req = urllib.request.Request(candidate, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"获取 JSON 失败：{url}\n{last_error}")


def http_download(
    urls: Union[str, Sequence[str]],
    destination: Path,
    download_source: str,
    reporter: Optional[DownloadStatsReporter] = None,
    timeout: int = 120,
) -> None:
    """下载单个文件，支持镜像回退、进度统计和原子替换。"""
    destination.parent.mkdir(parents=True, exist_ok=True)
    candidates = build_download_candidates(urls, download_source)
    if not candidates:
        raise RuntimeError("未提供可用下载地址。")

    temp_path = destination.with_name(destination.name + ".part")
    if temp_path.exists():
        temp_path.unlink()

    file_started = False
    try:
        if reporter is not None:
            reporter.start_file()
            file_started = True

        last_error: Optional[Exception] = None
        for candidate in candidates:
            try:
                req = urllib.request.Request(candidate, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    with temp_path.open("wb") as fp:
                        while True:
                            chunk = resp.read(1024 * 1024)
                            if not chunk:
                                break
                            fp.write(chunk)
                            if reporter is not None:
                                reporter.add_bytes(len(chunk))
                temp_path.replace(destination)
                if reporter is not None:
                    reporter.finish_file()
                    file_started = False
                return
            except Exception as exc:
                last_error = exc
                if temp_path.exists():
                    temp_path.unlink()

        raise RuntimeError(f"下载失败：{candidates[0]}\n{last_error}")
    except Exception:
        if file_started and reporter is not None:
            reporter.fail_file()
        if temp_path.exists():
            temp_path.unlink()
        raise
