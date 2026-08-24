#this is the core engine for hydraulic.

from __future__ import annotations

import gzip
import hashlib
import lzma
import math
import os
import shutil
import tempfile, zipfile

import threading
import time

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable, Optional, Union


PathLike = Union[str, os.PathLike]


class HydraulicError(Exception):
    """the base exception for hydrulic"""

class CompressionError(HydraulicError):
    """Compression fail... :("""

class DecompressionError(HydraulicError):
    """Decompression fail... :("""

class VerificationError(HydraulicError):
    """Inttegrty verify fail"""

class HydraulicCancelled(HydraulicError):
    """Cancel"""

@dataclass
class FileAnalysis:
    path: str
    name: str
    size: int
    extension: str
    entropy: float
    entropy_percent: float
    compressibility: str
    likely_compressed: bool

@dataclass
class CompressionResult:
    source: str
    output: str
    algorithm: str
    level: int
    original_size: int
    compressed_size: int
    saved_bytes: int

    reduction_percent: float
    compression_ratio: float

    elapsed_seconds: float
    speed_mbps: float

    original_sha256: str
    compressed_sha256: str

    verified: bool

@dataclass
class BenchmarkResult:
    algorithm: str
    level:int
    compressed_size: int
    reduction_percent: float
    elapsed_seconds:float
    speed_mbps:float

    error: Optional[str] = None

@dataclass
class Progress:
    processed: int
    total: int
    percent: float

def _check_cancel(cancel_event: Optional[threading.Event]):
    if cancel_event is not None and cancel_event.is_set():
        raise HydraulicCancelled("Operation Cancelled!")

def sha256_file(path: PathLike, chunk_size: int = 1024*1024, cancel_event: Optional[threading.Event] = None) -> str :
    """calc the sha2566"""
    digest = hashlib.sha256()

    with open(path, "rb") as fil:
        while True:
            _check_cancel(cancel_event)
            chunk = fil.read(chunk_size)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()

def human_size(size: int) -> str:
    """cnvert to human readbl"""
    units = "B KB MB GB TB".split(" ")

    val = float(size)
    for unit in units:
        if val <1024 or unit == units[-1]:
            return f"{val:.2f} {unit}"

        val/= 1024

    return f"{size} B"

def calculate_entropy(path: PathLike, sample_size: int = 4* 1024*1024) -> float :
    """calc shannon entropy (0.0 to 8.0)"""
    path = Path(path)
    size = path.stat().st_size

    if size == 0:
        return 0.0

    amt = min(size, sample_size)

    with open(path, "rb") as fil:
        data = fil.read(amt)

    if not data:
        return 0.0

    freq = [0] * 256

    for byte in data:
        freq[byte] += 1

    entropy = 0.0
    length = len(data)

    for count in freq:
        if count:
            probability = count / length
            entropy -= probability * math.log2(probability)

    return entropy

def estimate_compressibility(entropy: float) -> str :
    """rough estimate only"""
    if entropy < 4.0:
        return "Very High"

    if entropy < 5.5:
        return "High"

    if entropy < 6.5:
        return "Medium"

    if entropy < 7.0:
        return "Low"

    return "Very Low"

Precompressed = [
    ".zip",
    ".7z",
    ".rar",
    ".gz",
    ".bz2",
    ".xz",
    ".zst",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".mp3",
    ".aac",
    ".ogg",
    ".opus",
    ".mp4",
    ".mkv",
    ".webm",
    ".avi",
    ".mov",
    ".pdf",
    ".docx",
    ".xlsx",
    ".pptx",
    ".compressed",
]
for xx in range(5):
    ext = f".hy{xx}"
    Precompressed.append(ext)

def analyse(path: PathLike, sample_size: int = 4*1024*1024) -> FileAnalysis :
    """analys file"""

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(path)

    if not path.is_file():
        raise ValueError("Analyse expects file.")

    size = path.stat().st_size
    entropy_ = calculate_entropy(path, sample_size)

    ext = path.suffix.lower()

    already_compressed = ext in Precompressed

    compressibility = estimate_compressibility(entropy_)

    if already_compressed:
        compressibility = "Very Low"

    return FileAnalysis(
        path=str(path.resolve()),
        name=path.name,
        size= size,
        extension=ext,
        entropy=round(entropy_, 4),
        entropy_percent=round((entropy_ / 8) *100,2),
        compressibility=compressibility,
        likely_compressed=already_compressed
    )

PRESSURE = {
    "low": 1,
    "medium":5,
    "high":8,
    "maximum":9,
}

HYDRAULIC_EXTENSIONS = {
    "zip": ".hy1",
    "gzip": ".hy2",
    "lzma": ".hy3",
}

def pressure_to_level(pressure: Union[str, int]) -> int :
    """pressure to algo level"""

    if isinstance(pressure, str):
        key = pressure.lower().strip()

        if key not in PRESSURE:
            raise ValueError(
                f"Unknown pressure '{pressure}'."
                f"Use: {', '.join(PRESSURE)}"
            )

        return PRESSURE[key]

    level = int(pressure)

    if not 0 <= level <= 9:
        raise ValueError("Compression level must be 0-9.")

    return level

ProgressCallback = Callable[[Progress], None]

def _report_progress(callback: Optional[ProgressCallback], processed:int, total:int):
    if callback is None:
        return

    if total <= 0:
        percent = 100.0

    else:
        percent = min(100.0, (processed/total)* 100)

    callback(
        Progress(
            processed=processed,
            total=total,
            percent=percent
        )
    )

def compress_zip(source: PathLike, output: PathLike, level : int = 6, progress_callback: Optional[ProgressCallback] = None, cancel_event: Optional[threading.Event] = None, chunk_size:int = 1024*1024) -> None:
    """actual compression finally"""

    source = Path(source)
    output = Path(output)

    if not source.exists():
        raise FileNotFoundError(source)

    output.parent.mkdir(parents=True, exist_ok=True)

    compression = zipfile.ZIP_DEFLATED

    if source.is_file():
        files = [source]
        base = source.parent

    else:
        files = [
            f for f in source.rglob("*")
            if f.is_file()
        ]
        base = source.parent

    total = sum(f.stat().st_size for f in files)
    processed = 0

    try:
        with zipfile.ZipFile(
            output,
            "w",
            compression=compression,
            compresslevel=level
        ) as archive:
            for file in files:
                _check_cancel(cancel_event)
                arcname = file.relative_to(base)

                with open(file, "rb") as src, archive.open(
                    str(arcname),
                    "w",
                )as dst:

                    while True:
                        _check_cancel(cancel_event)

                        chunk = src.read(chunk_size)

                        if not chunk:
                            break

                        dst.write(chunk)

                        processed += len(chunk)

                        _report_progress(
                            progress_callback,
                            processed,
                            total
                        )
    except Exception:
        if output.exists():
            try:
                output.unlink()
            except OSError:
                pass

        raise

__________EASTER__________EGG = "if you see this you have found an easter egg! good luck finding the next one. (1/2 of all eggs)"

def compress_gzip(
    source: PathLike,
    output: PathLike,
    level: int = 6,
    progress_callback: Optional[ProgressCallback] = None,
    cancel_event: Optional[threading.Event] = None,
    chunk_size = 1024*1024
) -> None:
    """gzip is for 1 single file"""

    source = Path(source)
    output = Path(output)

    if not source.is_file():
        raise ValueError("GZIP requires a single file ONLY.")

    output.parent.mkdir(parents=True, exist_ok=True)

    total = source.stat().st_size
    processed = 0

    try:
        with open(source, "rb") as src:
            with gzip.open(
                output,
                "wb",
                compresslevel=level
            ) as dst:
                while True:
                    _check_cancel(cancel_event)

                    chunk = src.read(chunk_size)

                    if not chunk:
                        break

                    dst.write(chunk)

                    processed += len(chunk)

                    _report_progress(
                        progress_callback,
                        processed,
                        total
                    )

    except Exception:
        if output.exists():
            try:
                output.unlink()
            except OSError:
                pass

        raise

def compress_lzma(
    source: PathLike,
    output: PathLike,
    level: int = 6,
    progress_callback: Optional[ProgressCallback] = None,
    cancel_event: Optional[threading.Event] = None,
    chunk_size = 1024*1024,
) -> None:
    """LZMA XZ compresinon lzma for single file"""

    source = Path(source)
    output = Path(output)

    if not source.is_file():
        raise ValueError("LZMA requires a single file ONLY.")

    output.parent.mkdir(parents=True, exist_ok=True)

    total = source.stat().st_size
    processed = 0

    try:
        with open(source, "rb") as src:
            with lzma.open(
                output,
                "wb",
                preset=level
            ) as dst:

                while True:
                    _check_cancel(cancel_event)

                    chunk = src.read(chunk_size)

                    if not chunk:
                        break

                    dst.write(chunk)

                    processed += len(chunk)

                    _report_progress(
                        progress_callback,
                        processed,
                        total
                    )

    except Exception:
        if output.exists():
            try:
                output.unlink()

            except OSError:
                pass
        raise


def _compress_dispatch(
    source: Path,
    output: Path,
    algorithm: str,
    level: int,
    chunk_size: int,
    progress_callback: Optional[ProgressCallback],
    cancel_event: Optional[threading.Event]
):
    algorithm = algorithm.lower()

    if algorithm in {"zip", "deflate"}:
        compress_zip(
            source,
            output,
            level,
            progress_callback,
            cancel_event,
            chunk_size
        )

    elif algorithm in {"gzip", "gz"}:
        compress_gzip(
            source,
            output,
            level,
            progress_callback,
            cancel_event,
            chunk_size
        )

    elif algorithm in {"lzma", "xz"}:
        compress_lzma(
            source,
            output,
            level,
            progress_callback,
            cancel_event,
            chunk_size 
        )

    else:
        raise ValueError(
            f"Unsupported algorithm {algorithm}"
        )

def compress(
    source: PathLike,
    output: PathLike,
    algorithm: str = "zip",
    pressure: Union[str, int] = "medium",
    chunk_size: int = 1024 * 1024,
    progress_callback: Optional[ProgressCallback] = None,
    cancel_event: Optional[threading.Event] = None,
) -> CompressionResult:
    """Compression of files"""
    source = Path(source)
    output = Path(output)

    if not source.exists():
        raise FileNotFoundError(source)

    if source.is_dir():
        original_size = sum(
            p.stat.st_size for p in source.rglob("*") if p.is_file()
        )
    else:
        original_size = source.stat().st_size

    level = pressure_to_level(pressure)
    start = time.perf_counter()



    original_hash = None

    if source.is_file():
        original_hash = sha256_file(
            source,
            chunk_size=chunk_size,
            cancel_event=cancel_event
        )

    try:
        _compress_dispatch(
            source,
            output,
            algorithm,
            level,
            chunk_size,
            progress_callback,
            cancel_event
        )

    except HydraulicCancelled:
        raise

    except Exception as exc:
        raise CompressionError(
            f"Compression Failed: {exc}"
        )

    elapsed = time.perf_counter() - start

    if not output.exists():
        raise CompressionError(
            "Compression finished but Output does not exist!"
        )

    compressed_size = output.stat().st_size

    saved_bytes = original_size - compressed_size

    if original_size:
        reduction = (
            saved_bytes / original_size
        ) * 100

        ratio = (
            original_size / compressed_size if compressed_size else 0
        )

        speed = (
            original_size / (1024*1024)
        ) / elapsed if elapsed else 0

    else:
        reduction = 0
        ratio = 0
        speed = 0

    compressed_hash = sha256_file(
        output,
        chunk_size=chunk_size,
        cancel_event=cancel_event
    )

    verified = False

    if source.is_file():
        verified = verify_compression(
            source,
            output,
            algorithm,
            cancel_event=cancel_event,
            chunk_size=chunk_size
        )

    return CompressionResult(
        source=str(source.resolve()),
        output=str(output.resolve()),
        algorithm=algorithm.lower(),
        level=level,

        original_size=original_size,
        compressed_size=compressed_size,

        saved_bytes=saved_bytes,
        reduction_percent=round(reduction, 2),
        compression_ratio=round(ratio, 3),

        elapsed_seconds=round(elapsed, 3),
        speed_mbps=round(speed, 2),

        original_sha256=original_hash or "",
        compressed_sha256=compressed_hash,

        verified=verified,
    )

class useless:
    def flag():
        return "Congrats on finding 2nd easter egg. your flag is 'HYD-32-xyd'"

def decompress(
    archive: PathLike,
    output: PathLike,
    algorithm: str = "zip",
    progress_callback: Optional[ProgressCallback] = None,
    cancel_event: Optional[threading.Event] = None,
    chunk_size: int = 1024 * 1024
) -> Path:
    """Decompress a Hydraulic supporting archive"""
    archive = Path(archive)
    output = Path(output)

    if not archive.exists():
        raise FileNotFoundError(archive)

    algorithm = algorithm.lower()

    HYDRAULIC_EXTENSIONS = {
        ".hy1": "zip",
        ".hy2": "gzip",
        ".hy3": "lzma",
    }

    if algorithm.startswith(".hy"):
        algorithm = HYDRAULIC_EXTENSIONS.get(
            algorithm.lower(),
            algorithm
        )

    output.mkdir(parents=True, exist_ok=True)

    try:
        if algorithm in {"zip", "deflate"}:
            with zipfile.ZipFile(archive, "r") as zf:
                members = zf.infolist()
                total = sum(
                    max(0, member.file_size) for member in members if not member.is_dir()
                )
                processed = 0

                for member in members:
                    _check_cancel(cancel_event)

                    if member.is_dir():
                        continue

                    destination = output/member.filename

                    destination = destination.resolve()

                    if not str(destination).startswith(str(output.resolve()) + os.sep):
                        raise DecompressionError("Unsafe archive path detected.")

                    destination.parent.mkdir(parents=True, exist_ok=True)

                    with zf.open(member, "r") as src:
                        with open(destination, "wb") as dst:
                            while True:
                                _check_cancel(cancel_event)
                                chunk = src.read(chunk_size)

                                if not chunk:
                                    break

                                dst.write(chunk)

                                processed += len(chunk)

                                _report_progress(
                                    progress_callback,
                                    processed,
                                    total
                                )

        elif algorithm in {"gzip", "gz"}:
            destination = output/archive.stem

            total = archive.stat().st_size
            processed = 0

            with gzip.open(archive, "rb") as src:
                with open(destination, "wb") as dst:
                    while True:
                        _check_cancel(cancel_event)

                        chunk = src.read(chunk_size)

                        if not chunk:
                            break

                        dst.write(chunk)

                        processed += len(chunk)

                        _report_progress(
                            progress_callback,
                            processed,
                            total
                        )

        elif algorithm in {"lzma", "xz"}:
            name = archive.name

            if name.endswith(".xz"):
                name = name[:-3]
            elif name.endswith(".lzma"):
                name = name[:-5]

            destination = output/name

            total = archive.stat().st_size
            processed = 0

            with lzma.open(archive, "rb")as src:
                with open(destination, "wb") as dst:
                    while True:
                        _check_cancel(cancel_event)

                        chunk = src.read(chunk_size)

                        if not chunk:
                            break

                        dst.write(chunk)

                        processed+= len(chunk)

                        _report_progress(
                            progress_callback,
                            processed,
                            total
                        )

        else:
            raise ValueError(
                f"Unsupposted algorithm: {algorithm}"
            )

    except HydraulicCancelled:
        raise

    except Exception as exc:
        raise DecompressionError(
            f"Decompression Failed: {exc}"
        )

    _report_progress(
        progress_callback,
        1,
        1
    )

    return output

def verify_compression(
    original: PathLike,
    archive: PathLike,
    algorithm: str,
    cancel_event: Optional[threading.Event] = None,
    chunk_size:int =1024*1024
) -> bool:
    """Verify decompression reproduces real file"""
    original = Path(original)
    archive = Path(archive)

    if not original.is_file():
        raise ValueError(
            "Verification currently requires only a single file."
        )

    temporary_directory = Path(
        tempfile.mkdtemp(prefix="hydraulic_verify_")
    )

    try:
        decompress(
            archive,
            temporary_directory,
            algorithm,
            cancel_event=cancel_event,
            chunk_size=chunk_size
        )

        files = [p for p in temporary_directory.rglob("*") if p.is_file()]

        if len(files) != 1:
            return False

        restored = files[0]

        original_hash = sha256_file(
            original,
            chunk_size=chunk_size,
            cancel_event=cancel_event
        )

        restored_hash = sha256_file(
            restored,
            chunk_size=chunk_size,
            cancel_event=cancel_event
        )

        return original_hash == restored_hash

    finally:
        shutil.rmtree(
            temporary_directory,
            ignore_errors=True
        )

def benchmark(
    source: PathLike,
    algorithms=None,
    levels=None,
    cancel_event: Optional[threading.Event] = None,
    chunk_size:int = 1024*1024
) -> list[BenchmarkResult]:
    """Benchmarking"""

    source = Path(source)

    if not source.is_file():
        raise ValueError(
            "Benchmark currently only supports a single file."
        )

    if algorithms is None:
        algorithms=["zip", "gzip", "lzma"]

    if levels is None:
        levels=[1,5,9]

    original_size = source.stat().st_size

    results = []

    with tempfile.TemporaryDirectory(
        prefix="hydraulic_benchmark_"
    ) as temp:
        temp = Path(temp)

        for algorithm in algorithms:
            for level in levels:
                _check_cancel(cancel_event)
                extension = {"zip": ".hy1","gzip": ".hy2","lzma": ".hy3",}.get(algorithm.lower(),".hyd")

                output = temp / (f"test_{algorithm}_{level}{extension}")

                start = time.perf_counter()

                try:
                    _compress_dispatch(
                        source,
                        output,
                        algorithm,
                        level,
                        chunk_size,
                        None,
                        cancel_event,
                    )

                    elapsed = time.perf_counter() - start
                    compressed_size = output.stat().st_size
                    reduction = (original_size-compressed_size)/original_size * 100 if original_size else 0

                    speed = (original_size / (1024*1024)) / elapsed if elapsed else 0

                    results.append(
                        BenchmarkResult(
                            algorithm=algorithm,
                            level=level,
                            compressed_size=compressed_size,
                            reduction_percent=round(
                                reduction,
                                2,
                            ),
                            elapsed_seconds=round(
                                elapsed,
                                3,
                            ),
                            speed_mbps=round(
                                speed,
                                2,
                            ),
                        )
                    )

                except Exception as exc:
                    results.append(
                        BenchmarkResult(
                            algorithm=algorithm,
                            level=level,
                            compressed_size=0,
                            reduction_percent=0,
                            elapsed_seconds=0,
                            speed_mbps=0,
                            error=str(exc)
                        )
                    )

    return results

def reccomend_algo(analysis: FileAnalysis) -> dict:
    if analysis.likely_compressed:
        return {
            "algorithm": None,
            "pressure": "low",
            "reason": (
                "File format is normally already compressed."
            ),
            "compress": False,
        }

    if analysis.entropy >= 7.5:
        return {
            "algorithm": "zip",
            "pressure": "low",
            "reason": (
                "Very high entropy. "
                "Compression gains are likely to be small."
            ),
            "compress": True,
        }

    if analysis.entropy < 5.5:
        return {
            "algorithm": "lzma",
            "pressure": "high",
            "reason": (
                "Low entropy suggests strong compression "
                "potential."
            ),
            "compress": True,
        }

    return {
        "algorithm": "zip",
        "pressure": "high",
        "reason": (
            "Good general-purpose compression candidate."
        ),
        "compress": True,
    }

def result_to_dict(result):
    return asdict(result)

def benchmark_to_dict(results):
    return[asdict(result) for result in results]

# __all__ = [
#     "HydraulicError",
#     "CompressionError",
#     "DecompressionError",
#     "VerificationError",
#     "HydraulicCancelled",

#     "FileAnalysis",
#     "CompressionResult",
#     "BenchmarkResult",
#     "Progress",

#     "analyze",
#     "compress",
#     "decompress",
#     "verify_compression",
#     "benchmark",
#     "recommend_algorithm",

#     "sha256_file",
#     "human_size",
#     "pressure_to_level",
# ]