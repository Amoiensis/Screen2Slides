from __future__ import annotations

import json
import math
import re
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Callable, Iterable

import cv2
import numpy as np
from PIL import Image
from pypdf import PdfReader, PdfWriter
from skimage.metrics import structural_similarity

try:
    import torch
    import torch.nn.functional as torch_f
except Exception:  # pragma: no cover - optional dependency at runtime
    torch = None
    torch_f = None


DEFAULT_SAMPLE_SECONDS = 1.0
DEFAULT_SIMILARITY_THRESHOLD = 0.98
DEFAULT_MIN_STABLE_SECONDS = 2.0
DEFAULT_PREVIEW_WIDTH = 960


@dataclass(frozen=True)
class Roi:
    x: int
    y: int
    width: int
    height: int

    @property
    def x2(self) -> int:
        return self.x + self.width

    @property
    def y2(self) -> int:
        return self.y + self.height

    def clipped(self, frame_width: int, frame_height: int) -> "Roi":
        x = max(0, min(self.x, frame_width - 1))
        y = max(0, min(self.y, frame_height - 1))
        x2 = max(x + 1, min(self.x2, frame_width))
        y2 = max(y + 1, min(self.y2, frame_height))
        return Roi(x=x, y=y, width=x2 - x, height=y2 - y)


@dataclass(frozen=True)
class VideoMetadata:
    width: int
    height: int
    fps: float
    frame_count: int
    duration_seconds: float


@dataclass(frozen=True)
class ExtractConfig:
    mode: str = "ssim"
    execution_device: str = "auto"
    sample_every_seconds: float = DEFAULT_SAMPLE_SECONDS
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD
    min_stable_seconds: float = DEFAULT_MIN_STABLE_SECONDS
    resize_width: int = 320
    max_slides: int = 200


@dataclass
class SampleFrame:
    timestamp_seconds: float
    frame_index: int
    image_bgr: np.ndarray
    signature: np.ndarray
    sharpness: float


@dataclass(frozen=True)
class SlideArtifact:
    index: int
    timestamp_seconds: float
    image_path: Path


@dataclass(frozen=True)
class ExtractionResult:
    run_id: str
    output_dir: Path
    pdf_path: Path
    slides: list[SlideArtifact]
    roi: Roi
    config: ExtractConfig
    metadata: VideoMetadata
    execution_device: str


@dataclass(frozen=True)
class ExecutionBackend:
    requested: str
    actual: str
    display_name: str
    message: str


@dataclass(frozen=True)
class ProgressUpdate:
    stage: str
    progress: float
    message: str
    eta_seconds: float | None


ProgressCallback = Callable[[ProgressUpdate], None]


def get_video_metadata(video_path: str | Path) -> VideoMetadata:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"Unable to open video: {video_path}")

    try:
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0) or 1.0
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        duration_seconds = frame_count / fps if frame_count else 0.0
        return VideoMetadata(
            width=width,
            height=height,
            fps=fps,
            frame_count=frame_count,
            duration_seconds=duration_seconds,
        )
    finally:
        capture.release()


def load_preview_frame(video_path: str | Path, timestamp_seconds: float = 0.0) -> np.ndarray:
    metadata = get_video_metadata(video_path)
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"Unable to open video: {video_path}")

    frame_index = min(
        max(int(timestamp_seconds * metadata.fps), 0),
        max(metadata.frame_count - 1, 0),
    )

    try:
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame_bgr = capture.read()
        if not ok:
            raise RuntimeError("Unable to decode preview frame.")
        return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    finally:
        capture.release()


def ensure_roi(roi: Roi | None, metadata: VideoMetadata) -> Roi:
    if roi is None:
        return Roi(x=0, y=0, width=metadata.width, height=metadata.height)
    return roi.clipped(metadata.width, metadata.height)


def extract_slides(
    video_path: str | Path,
    roi: Roi | None,
    config: ExtractConfig,
    output_root: str | Path,
    progress_callback: ProgressCallback | None = None,
) -> ExtractionResult:
    video_path = Path(video_path)
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    metadata = get_video_metadata(video_path)
    roi = ensure_roi(roi, metadata)
    backend = get_execution_backend(config.execution_device)
    start_time = perf_counter()

    run_id = uuid.uuid4().hex[:10]
    output_dir = output_root / _build_output_dir_name(video_path, run_id)
    slides_dir = output_dir / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)

    _emit_progress(progress_callback, start_time, "prepare", 0.02, "Preparing extraction...")
    samples = list(_iter_samples(video_path, metadata, roi, config, progress_callback, start_time))
    _emit_progress(progress_callback, start_time, "analyze", 0.82, "Analyzing slide transitions...")
    slide_samples = _pick_slide_samples(samples, config, backend.actual)
    if not slide_samples and samples:
        slide_samples = [max(samples, key=lambda sample: sample.sharpness)]
    if config.max_slides > 0:
        slide_samples = slide_samples[: config.max_slides]

    slide_artifacts: list[SlideArtifact] = []
    pil_images: list[Image.Image] = []
    total_slide_samples = max(len(slide_samples), 1)
    for index, sample in enumerate(slide_samples, start=1):
        rgb = cv2.cvtColor(sample.image_bgr, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb).convert("RGB")
        image_path = slides_dir / f"slide_{index:03d}_{_format_timestamp_for_name(sample.timestamp_seconds)}.jpg"
        pil_image.save(image_path, format="JPEG", quality=95)
        slide_artifacts.append(
            SlideArtifact(
                index=index,
                timestamp_seconds=sample.timestamp_seconds,
                image_path=image_path,
            )
        )
        pil_images.append(pil_image)
        export_progress = 0.82 + 0.13 * (index / total_slide_samples)
        _emit_progress(
            progress_callback,
            start_time,
            "export",
            export_progress,
            f"Exporting slide {index}/{len(slide_samples)}...",
        )

    pdf_path = output_dir / f"{output_dir.name}.pdf"
    _emit_progress(progress_callback, start_time, "pdf", 0.96, "Building PDF document...")
    if pil_images:
        first_image, *rest_images = pil_images
        first_image.save(
            pdf_path,
            format="PDF",
            resolution=100.0,
            save_all=True,
            append_images=rest_images,
        )
    else:
        blank = Image.new("RGB", (max(roi.width, 1), max(roi.height, 1)), color="white")
        blank.save(pdf_path, format="PDF", resolution=100.0)

    if slide_artifacts:
        _add_pdf_bookmarks(pdf_path, slide_artifacts)

    manifest = {
        "video_path": str(video_path.resolve()),
        "run_id": run_id,
        "roi": asdict(roi),
        "config": asdict(config),
        "execution_device": backend.actual,
        "metadata": asdict(metadata),
        "slides": [
            {
                "index": slide.index,
                "timestamp_seconds": slide.timestamp_seconds,
                "image_path": str(slide.image_path.resolve()),
            }
            for slide in slide_artifacts
        ],
        "pdf_path": str(pdf_path.resolve()),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    _emit_progress(progress_callback, start_time, "done", 1.0, "Completed.")

    return ExtractionResult(
        run_id=run_id,
        output_dir=output_dir,
        pdf_path=pdf_path,
        slides=slide_artifacts,
        roi=roi,
        config=config,
        metadata=metadata,
        execution_device=backend.actual,
    )


def _iter_samples(
    video_path: Path,
    metadata: VideoMetadata,
    roi: Roi,
    config: ExtractConfig,
    progress_callback: ProgressCallback | None = None,
    start_time: float | None = None,
) -> Iterable[SampleFrame]:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"Unable to open video: {video_path}")

    frame_step = max(int(round(metadata.fps * config.sample_every_seconds)), 1)
    estimated_samples = max(1, int(math.ceil(metadata.frame_count / frame_step)))
    frame_index = 0
    sampled_count = 0

    try:
        while frame_index < metadata.frame_count:
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, frame_bgr = capture.read()
            if not ok:
                break

            cropped = frame_bgr[roi.y : roi.y2, roi.x : roi.x2]
            if cropped.size == 0:
                frame_index += frame_step
                continue

            gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
            signature = _make_signature(gray, config)
            sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())

            yield SampleFrame(
                timestamp_seconds=frame_index / metadata.fps,
                frame_index=frame_index,
                image_bgr=cropped,
                signature=signature,
                sharpness=sharpness,
            )
            sampled_count += 1
            sampling_progress = min(sampled_count / estimated_samples, 1.0)
            _emit_progress(
                progress_callback,
                start_time,
                "sampling",
                0.02 + 0.78 * sampling_progress,
                f"Sampling frames... {sampled_count}/{estimated_samples}",
            )
            frame_index += frame_step
    finally:
        capture.release()


def _make_signature(gray_frame: np.ndarray, config: ExtractConfig) -> np.ndarray:
    height, width = gray_frame.shape[:2]
    resize_width = max(16, min(config.resize_width, width))
    resize_height = max(16, int(height * resize_width / max(width, 1)))
    resized = cv2.resize(
        gray_frame,
        (resize_width, resize_height),
        interpolation=cv2.INTER_AREA,
    )
    return resized


def _pick_slide_samples(
    samples: list[SampleFrame],
    config: ExtractConfig,
    execution_device: str,
) -> list[SampleFrame]:
    if not samples:
        return []

    min_segment_frames = max(
        1,
        int(math.ceil(config.min_stable_seconds / max(config.sample_every_seconds, 1e-6))),
    )

    segments: list[list[SampleFrame]] = [[samples[0]]]
    for sample in samples[1:]:
        similarity = compute_similarity(
            segments[-1][-1].signature,
            sample.signature,
            mode=config.mode,
            device=execution_device,
        )
        if similarity >= config.similarity_threshold:
            segments[-1].append(sample)
        else:
            segments.append([sample])

    stable_segments = [segment for segment in segments if len(segment) >= min_segment_frames]
    if not stable_segments:
        stable_segments = segments

    representatives: list[SampleFrame] = []
    for segment in stable_segments:
        candidate = max(segment, key=lambda sample: sample.sharpness)
        if representatives:
            similarity = compute_similarity(
                representatives[-1].signature,
                candidate.signature,
                mode=config.mode,
                device=execution_device,
            )
            if similarity >= config.similarity_threshold:
                if candidate.sharpness > representatives[-1].sharpness:
                    representatives[-1] = candidate
                continue
        representatives.append(candidate)
    return representatives


def compute_similarity(left: np.ndarray, right: np.ndarray, mode: str, device: str = "cpu") -> float:
    if left.shape != right.shape:
        right = cv2.resize(right, (left.shape[1], left.shape[0]), interpolation=cv2.INTER_AREA)

    normalized_mode = mode.lower()
    normalized_device = "cuda" if device == "cuda" else "cpu"
    if normalized_mode == "ssim":
        if normalized_device == "cuda":
            return _torch_ssim_similarity(left, right)
        return float(structural_similarity(left, right, data_range=255))
    if normalized_mode == "ahash":
        if normalized_device == "cuda":
            return _torch_ahash_similarity(left, right)
        return _ahash_similarity(left, right)
    if normalized_mode == "histogram":
        if normalized_device == "cuda":
            return _torch_histogram_similarity(left, right)
        return _histogram_similarity(left, right)
    raise ValueError(f"Unsupported similarity mode: {mode}")


def _ahash_similarity(left: np.ndarray, right: np.ndarray) -> float:
    left_hash = _average_hash(left)
    right_hash = _average_hash(right)
    equal_ratio = np.mean(left_hash == right_hash)
    return float(equal_ratio)


def _average_hash(frame: np.ndarray, size: int = 8) -> np.ndarray:
    small = cv2.resize(frame, (size, size), interpolation=cv2.INTER_AREA)
    average = small.mean()
    return small >= average


def _histogram_similarity(left: np.ndarray, right: np.ndarray) -> float:
    left_hist = cv2.calcHist([left], [0], None, [64], [0, 256])
    right_hist = cv2.calcHist([right], [0], None, [64], [0, 256])
    cv2.normalize(left_hist, left_hist)
    cv2.normalize(right_hist, right_hist)
    score = cv2.compareHist(left_hist, right_hist, cv2.HISTCMP_CORREL)
    return float((score + 1.0) / 2.0)


def get_execution_backend(requested: str = "auto") -> ExecutionBackend:
    normalized = requested.lower()
    if normalized not in {"auto", "cpu", "gpu"}:
        raise ValueError(f"Unsupported execution backend: {requested}")

    if normalized == "cpu":
        return ExecutionBackend(
            requested=normalized,
            actual="cpu",
            display_name="CPU",
            message="Using CPU execution.",
        )

    if torch is not None and torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)
        return ExecutionBackend(
            requested=normalized,
            actual="cuda",
            display_name=f"GPU ({device_name})",
            message=f"Using CUDA acceleration on {device_name}.",
        )

    fallback_reason = (
        "GPU was requested, but CUDA is not available in the current Python runtime."
        if normalized == "gpu"
        else "GPU is not available; auto mode falls back to CPU."
    )
    return ExecutionBackend(
        requested=normalized,
        actual="cpu",
        display_name="CPU",
        message=fallback_reason,
    )


def _torch_ssim_similarity(left: np.ndarray, right: np.ndarray) -> float:
    if torch is None or torch_f is None or not torch.cuda.is_available():
        return float(structural_similarity(left, right, data_range=255))

    x = torch.from_numpy(left.astype(np.float32) / 255.0).to("cuda")
    y = torch.from_numpy(right.astype(np.float32) / 255.0).to("cuda")
    x = x.unsqueeze(0).unsqueeze(0)
    y = y.unsqueeze(0).unsqueeze(0)

    kernel_size = 7 if min(left.shape[:2]) >= 7 else 3
    padding = kernel_size // 2

    mu_x = torch_f.avg_pool2d(x, kernel_size, stride=1, padding=padding)
    mu_y = torch_f.avg_pool2d(y, kernel_size, stride=1, padding=padding)
    sigma_x = torch_f.avg_pool2d(x * x, kernel_size, stride=1, padding=padding) - mu_x * mu_x
    sigma_y = torch_f.avg_pool2d(y * y, kernel_size, stride=1, padding=padding) - mu_y * mu_y
    sigma_xy = torch_f.avg_pool2d(x * y, kernel_size, stride=1, padding=padding) - mu_x * mu_y

    c1 = 0.01**2
    c2 = 0.03**2
    numerator = (2 * mu_x * mu_y + c1) * (2 * sigma_xy + c2)
    denominator = (mu_x * mu_x + mu_y * mu_y + c1) * (sigma_x + sigma_y + c2)
    score = (numerator / denominator.clamp_min(1e-6)).mean().clamp(0.0, 1.0)
    return float(score.item())


def _torch_ahash_similarity(left: np.ndarray, right: np.ndarray) -> float:
    if torch is None or torch_f is None or not torch.cuda.is_available():
        return _ahash_similarity(left, right)

    x = torch.from_numpy(left.astype(np.float32)).to("cuda").unsqueeze(0).unsqueeze(0)
    y = torch.from_numpy(right.astype(np.float32)).to("cuda").unsqueeze(0).unsqueeze(0)
    x_small = torch_f.interpolate(x, size=(8, 8), mode="area")[0, 0]
    y_small = torch_f.interpolate(y, size=(8, 8), mode="area")[0, 0]
    x_hash = x_small >= x_small.mean()
    y_hash = y_small >= y_small.mean()
    return float((x_hash == y_hash).float().mean().item())


def _torch_histogram_similarity(left: np.ndarray, right: np.ndarray) -> float:
    if torch is None or not torch.cuda.is_available():
        return _histogram_similarity(left, right)

    x = torch.from_numpy(left.astype(np.float32)).to("cuda").flatten()
    y = torch.from_numpy(right.astype(np.float32)).to("cuda").flatten()
    x_hist = torch.histc(x, bins=64, min=0.0, max=255.0)
    y_hist = torch.histc(y, bins=64, min=0.0, max=255.0)
    x_hist = x_hist / x_hist.norm(p=2).clamp_min(1e-6)
    y_hist = y_hist / y_hist.norm(p=2).clamp_min(1e-6)
    return float(torch.dot(x_hist, y_hist).clamp(0.0, 1.0).item())


def resize_for_selector(image_rgb: np.ndarray, max_width: int = DEFAULT_PREVIEW_WIDTH) -> tuple[np.ndarray, float]:
    height, width = image_rgb.shape[:2]
    if width <= max_width:
        return image_rgb, 1.0

    scale = max_width / width
    resized = cv2.resize(
        image_rgb,
        (int(round(width * scale)), int(round(height * scale))),
        interpolation=cv2.INTER_AREA,
    )
    return resized, scale


def _format_timestamp_for_name(timestamp_seconds: float) -> str:
    total_seconds = int(round(timestamp_seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}-{minutes:02d}-{seconds:02d}"




def _format_timestamp_display(timestamp_seconds: float) -> str:
    total_seconds = int(round(timestamp_seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _add_pdf_bookmarks(pdf_path: Path, slide_artifacts: list[SlideArtifact]) -> None:
    if not slide_artifacts:
        return
    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    for index, slide in enumerate(slide_artifacts):
        label = f"Page {slide.index} - {_format_timestamp_display(slide.timestamp_seconds)}"
        writer.add_outline_item(label, index)
    with open(str(pdf_path), "wb") as f:
        writer.write(f)

def _build_output_dir_name(video_path: Path, run_id: str) -> str:
    stem = video_path.stem.strip() or "video"
    normalized = re.sub(r"\s+", "_", stem)
    normalized = re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff]+", "_", normalized).strip("_")
    normalized = normalized or "video"
    return f"{normalized}_{run_id}"


def _emit_progress(
    progress_callback: ProgressCallback | None,
    start_time: float | None,
    stage: str,
    progress: float,
    message: str,
) -> None:
    if progress_callback is None:
        return

    clamped = max(0.0, min(progress, 1.0))
    eta_seconds: float | None = None
    if start_time is not None and clamped > 0.02 and clamped < 1.0:
        elapsed = perf_counter() - start_time
        eta_seconds = max((elapsed / clamped) - elapsed, 0.0)

    progress_callback(
        ProgressUpdate(
            stage=stage,
            progress=clamped,
            message=message,
            eta_seconds=eta_seconds,
        )
    )
