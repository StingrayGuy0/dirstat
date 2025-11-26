#!/usr/bin/env python3
import os
import sys
import argparse
import math
import multiprocessing
from collections import defaultdict
import time
from tqdm import tqdm

def color(code): return f"\033[{code}m"
def reset(): return "\033[0m"
cyan = lambda t: f"{color('36')}{t}{reset()}"
yellow = lambda t: f"{color('33')}{t}{reset()}"
green = lambda t: f"{color('32')}{t}{reset()}"
magenta = lambda t: f"{color('35')}{t}{reset()}"
bold = lambda t: f"\033[1m{t}{reset()}"


def format_bytes(n):
    if n == 0:
        return "0 Bytes"
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB"]
    i = int(math.log(n, 1024))
    i = min(i, len(units) - 1)
    return f"{n / (1024 ** i):.2f} {units[i]}"


def file_worker(path):
    try:
        size = os.path.getsize(path)
        filename = os.path.basename(path).lower()

        parts = filename.split(".")
        if len(parts) == 1:
            ext = "(no ext)"
        else:
            common_multi = {"gz", "bz2", "xz", "zip", "7z", "rar", "lz", "lz4", "lzma", "zst"}
            primary = parts[-1]
            previous = parts[-2]

            if primary in common_multi and len(previous) <= 5 and previous.isalnum():
                ext = f".{previous}.{primary}"
            else:
                ext = parts[-1]
                ext = ext if ext.isalnum() and len(ext) <= 5 else "(no ext)"
                if ext != "(no ext)":
                    ext = "." + ext

        backup_exts = {".bak", ".tmp", ".old", ".temp", ".swp", ".save", ".orig"}
        classification = {
            "video": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mpg", ".mpeg", ".ivf"},
            "audio": {".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a", ".wma"},
            "image": {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"},
            "doc": {".pdf", ".txt", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"},
            "archive": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".tar.gz"},
            "binary": {".exe", ".dll", ".so", ".bin", ".dylib"},
            "code": {".c", ".cpp", ".h", ".hpp", ".py", ".js", ".ts", ".cs", ".go", ".rs", ".lua", ".java"},
            "ebook": {".epub", ".mobi", ".azw", ".azw3"},
        }

        if ext in backup_exts:
            ext = "(backup)"
        elif ext != "(no ext)":
            for name, group in classification.items():
                if ext in group:
                    ext = f"[{name}] {ext}"
                    break

        return ext, size

    except Exception:
        return None


def get_dir_stats(directory_path, skip_indexing=False):

    indexed_dirs = []

    if not skip_indexing:
        p_index = tqdm(
            desc=magenta("Indexing"),
            unit="dir",
            dynamic_ncols=True,
            bar_format=magenta("Indexing: ") + "{n} [{elapsed}, {rate_fmt}]"
        )
        for root, dirs, files in os.walk(directory_path):
            indexed_dirs.append(root)
            p_index.update(1)
        p_index.close()
    else:
        print(yellow("Skipping indexing phase (-s enabled)"))
        indexed_dirs = [directory_path]

    all_files = []
    p_scan = tqdm(
        indexed_dirs,
        desc=cyan("Scanning"),
        unit="dir",
        dynamic_ncols=True,
        bar_format=cyan("Scanning: ") + "{l_bar}{bar} {n}/{total} [{elapsed}, {rate_fmt}]"
    )

    for d in p_scan:
        try:
            for entry in os.listdir(d):
                f = os.path.join(d, entry)
                if os.path.isfile(f):
                    all_files.append(f)
                elif os.path.isdir(f) and skip_indexing:
                    indexed_dirs.append(f)
                    p_scan.total = len(indexed_dirs)
        except:
            pass

    p_scan.close()
    total_files = len(all_files)

    total_size = 0
    file_stats = defaultdict(lambda: {"count": 0, "size": 0})

    p_files = tqdm(
        total=total_files,
        desc=green("Processing"),
        unit="file",
        dynamic_ncols=True,
        bar_format=green("Processing: ") + "{l_bar}{bar} {n}/{total} [{elapsed}, {rate_fmt}]"
    )

    with multiprocessing.Pool() as pool:
        for result in pool.imap_unordered(file_worker, all_files, chunksize=500):
            if result:
                ext, size = result
                file_stats[ext]["count"] += 1
                file_stats[ext]["size"] += size
                total_size += size
            p_files.update(1)

    p_files.close()

    print("\n" + bold("--- Directory Statistics ---"))
    print(f"{bold('Directory:')} {directory_path}")
    print(f"{bold('Total subdirectories:')} {cyan(f'{len(indexed_dirs):,}')}")
    print(f"{bold('Total files scanned:')} {cyan(f'{total_files:,}')}")
    print(f"{bold('Total size:')} {green(format_bytes(total_size))}\n")

    print(bold("--- File Type Breakdown ---"))
    sorted_stats = sorted(file_stats.items(), key=lambda x: x[1]["size"], reverse=True)
    for ext, data in sorted_stats:
        count, size = data["count"], data["size"]
        pct = (size / total_size) * 100 if total_size > 0 else 0
        colorized = green if pct > 2 else yellow
        print(f"{magenta(ext or '(no ext)')}: {count:,} files ({pct:.2f}%)  →  {colorized(format_bytes(size))}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze directory statistics by file type.")
    parser.add_argument("directory_path", nargs="?", default=".", help="Directory to scan (default: .)")
    parser.add_argument("-s", "--skip-indexing", action="store_true", help="Skip indexing phase and scan directly")
    args = parser.parse_args()
    get_dir_stats(args.directory_path, args.skip_indexing)
