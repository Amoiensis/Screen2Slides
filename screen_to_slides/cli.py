from __future__ import annotations

import argparse
from pathlib import Path

from screen_to_slides.extractor import (
    DEFAULT_MIN_STABLE_SECONDS,
    DEFAULT_SAMPLE_SECONDS,
    DEFAULT_SIMILARITY_THRESHOLD,
    ExtractConfig,
    ProgressUpdate,
    Roi,
    extract_slides,
    get_video_metadata,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="screen_to_slides.cli",
        description="Extract slide-like pages from a video and export them as a PDF.",
    )
    parser.add_argument("video", help="Input video path")
    parser.add_argument(
        "--output-dir",
        default="",
        help="Output root directory. Defaults to the input video's parent directory.",
    )
    parser.add_argument(
        "--mode",
        choices=["ssim", "histogram", "ahash"],
        default="ssim",
        help="Similarity algorithm. Default: ssim",
    )
    parser.add_argument(
        "--device",
        choices=["cpu", "gpu", "auto"],
        default="cpu",
        help="Execution device. Default: cpu",
    )
    parser.add_argument(
        "--sample-every-seconds",
        type=float,
        default=DEFAULT_SAMPLE_SECONDS,
        help=f"Sampling interval in seconds. Default: {DEFAULT_SAMPLE_SECONDS}",
    )
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=DEFAULT_SIMILARITY_THRESHOLD,
        help=f"Similarity threshold. Default: {DEFAULT_SIMILARITY_THRESHOLD}",
    )
    parser.add_argument(
        "--min-stable-seconds",
        type=float,
        default=DEFAULT_MIN_STABLE_SECONDS,
        help=f"Minimum stable duration in seconds. Default: {DEFAULT_MIN_STABLE_SECONDS}",
    )
    parser.add_argument(
        "--max-slides",
        type=int,
        default=200,
        help="Maximum number of exported pages. Default: 200",
    )
    parser.add_argument("--x", type=int, default=None, help="ROI left boundary")
    parser.add_argument("--y", type=int, default=None, help="ROI top boundary")
    parser.add_argument("--width", type=int, default=None, help="ROI width")
    parser.add_argument("--height", type=int, default=None, help="ROI height")
    return parser


def _format_eta(seconds: float | None) -> str:
    if seconds is None:
        return "--:--"
    total = max(int(round(seconds)), 0)
    minutes, seconds = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def _build_roi(args: argparse.Namespace, video_path: Path) -> Roi | None:
    if all(value is None for value in (args.x, args.y, args.width, args.height)):
        return None

    metadata = get_video_metadata(video_path)
    return Roi(
        x=0 if args.x is None else args.x,
        y=0 if args.y is None else args.y,
        width=metadata.width if args.width is None else args.width,
        height=metadata.height if args.height is None else args.height,
    ).clipped(metadata.width, metadata.height)


def _progress_printer(update: ProgressUpdate) -> None:
    percent = int(round(update.progress * 100))
    eta_text = _format_eta(update.eta_seconds)
    print(f"[{percent:3d}%] {update.stage}: {update.message} ETA {eta_text}")


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    video_path = Path(args.video).expanduser()
    if not video_path.exists() or not video_path.is_file():
        parser.error(f"Video does not exist: {video_path}")

    roi = _build_roi(args, video_path)
    output_root = Path(args.output_dir).expanduser() if args.output_dir else video_path.parent
    config = ExtractConfig(
        mode=args.mode,
        execution_device=args.device,
        sample_every_seconds=args.sample_every_seconds,
        similarity_threshold=args.similarity_threshold,
        min_stable_seconds=args.min_stable_seconds,
        max_slides=args.max_slides,
    )

    result = extract_slides(
        video_path=video_path,
        roi=roi,
        config=config,
        output_root=output_root,
        progress_callback=_progress_printer,
    )

    print("")
    print("Extraction completed")
    print(f"Video: {video_path}")
    print(f"Slides: {len(result.slides)}")
    print(f"Execution device: {result.execution_device}")
    print(f"Output directory: {result.output_dir}")
    print(f"PDF: {result.pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
