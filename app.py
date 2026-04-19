from __future__ import annotations

import argparse
import base64
from pathlib import Path
import sys

import numpy as np
import plotly.graph_objects as go
import streamlit as st
from PIL import Image as PILImage

from screen_to_slides import __version__
from screen_to_slides.extractor import (
    DEFAULT_MIN_STABLE_SECONDS,
    DEFAULT_SAMPLE_SECONDS,
    DEFAULT_SIMILARITY_THRESHOLD,
    ExtractConfig,
    ProgressUpdate,
    Roi,
    ensure_roi,
    extract_slides,
    get_execution_backend,
    get_video_metadata,
    load_preview_frame,
    resize_for_selector,
)


ROOT = Path(__file__).resolve().parent
OUTPUTS_DIR = ROOT / "outputs"
UPLOADS_DIR = ROOT / "uploads"
EXAMPLE_VIDEO = ROOT / "record_2025_11_25_16_29_27_89_prat.mp4"
GITHUB_URL = "https://github.com/Amoiensis/Screen2Slides"
APP_ICON_PATH = ROOT / "assets" / "amoiensis_samll.png"
APP_ICON = PILImage.open(APP_ICON_PATH) if APP_ICON_PATH.exists() else "pages"
APP_ICON_B64 = (
    base64.b64encode(APP_ICON_PATH.read_bytes()).decode("ascii")
    if APP_ICON_PATH.exists()
    else ""
)
VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
    ".flv",
    ".wmv",
    ".m4v",
    ".mpeg",
    ".mpg",
    ".ts",
    ".m2ts",
}
APP_SOURCE_MODES = {"local", "upload", "hybrid"}


TEXT = {
    "zh": {
        "app.title": "Screen To Slides",
        "app.subtitle": "上传录屏、框选 PPT 区域，然后直接抽取并导出 PDF。",
        "lang.label": "语言选择 / Language",
        "lang.zh": "中文",
        "lang.en": "English",
        "app.footer_meta": "版本 {version} · GitHub: {url}",
        "app.footer_license": "许可: PolyForm Noncommercial 1.0.0；商业使用请联系授权。",
        "source.section": "1. 视频选择",
        "source.label": "选择视频来源",
        "source.local": "本地视频",
        "source.upload": "服务器上传",
        "source.hybrid": "兼容模式",
        "source.uploader": "上传视频文件",
        "source.dir": "扫描目录或视频文件路径",
        "source.file": "选择视频文件",
        "source.file_placeholder": "请选择一个视频文件",
        "source.missing": "视频不存在: {path}",
        "source.no_files": "该目录下没有找到可处理的视频文件。",
        "source.empty": "上传视频文件，或从本地目录中选择一个视频文件。",
        "source.mode_caption": "当前启动模式: {mode}",
        "source.pending": "尚未选择视频",
        "overview.section": "2. 视频概览",
        "overview.duration": "视频时长",
        "overview.path": "当前视频",
        "overview.meta": "分辨率 {resolution} · {fps} FPS",
        "preview.label": "预览时间点",
        "preview.help": "可拖动进度条，也可直接输入时分秒，例如 00:12:34。",
        "preview.input": "直接输入时分秒",
        "preview.invalid": "时间格式无效，请输入 `HH:MM:SS` 或总秒数。",
        "selector.section": "3. 选择区块",
        "selector.caption": "在图上拖拽矩形，选出需要纳入 PDF 的 PPT 区域。",
        "selector.empty": "上传或选择视频后，这里会显示可框选的预览画面。",
        "roi.left": "左边界",
        "roi.top": "上边界",
        "roi.width": "宽度",
        "roi.height": "高度",
        "roi.reset": "全画面",
        "summary.section": "4. 抽取设置",
        "summary.roi": "当前区域",
        "summary.roi_value": "{width} x {height}",
        "summary.device": "执行设备",
        "summary.device_fallback": "{device}。{message}",
        "summary.max_slides": "最多导出页数",
        "summary.advanced": "高级配置",
        "advanced.output_dir": "输出目录（可选）",
        "advanced.output_dir_help": "留空时，默认在输入视频所在目录下创建结果子目录。",
        "advanced.mode": "相似度算法",
        "advanced.mode_help": "`ssim` 更稳定；`histogram` 更轻量；`ahash` 更快但更粗糙。",
        "advanced.device": "执行设备",
        "advanced.device_help": "默认直接使用 CPU；如需更快处理，可手动切换到 GPU 增强或 auto 自动判断。",
        "advanced.sample": "采样间隔（秒）",
        "advanced.threshold": "相似度阈值",
        "advanced.threshold_help": "PPT 录屏通常建议从 0.98 开始。",
        "advanced.stable": "最短稳定时长（秒）",
        "advanced.stable_help": "用于过滤切页动画和短暂过渡帧。",
        "run.button": "抽取分析并生成 PDF",
        "run.progress": "正在抽取候选幻灯片并生成 PDF...",
        "run.progress_idle": "等待开始",
        "run.progress_eta": "预计剩余时间: {eta}",
        "run.progress_no_eta": "正在估算剩余时间...",
        "run.stage.prepare": "准备任务",
        "run.stage.sampling": "正在采样视频帧",
        "run.stage.analyze": "正在分析切页",
        "run.stage.export": "正在导出页面图片",
        "run.stage.pdf": "正在生成 PDF",
        "run.stage.done": "处理完成",
        "run.done": "完成，提取到 {count} 页，执行设备: {device}",
        "results.section": "5. 结果预览",
        "results.empty": "执行抽取后，这里会展示 PDF 下载和缩略图列表。",
        "results.download": "下载 PDF",
        "results.no_images": "没有生成可展示的页面图片。",
        "results.delete": "删除此页",
        "results.restore": "恢复此页",
        "results.delete_short": "[删除]",
        "results.restore_short": "[恢复]",
        "results.dir": "当前结果目录",
    },
    "en": {
        "app.title": "Screen To Slides",
        "app.subtitle": "Upload a meeting recording, select the slide area, then extract and export a PDF.",
        "lang.label": "Language Setting / 语言选择",
        "lang.zh": "中文",
        "lang.en": "English",
        "app.footer_meta": "Version {version} · GitHub: {url}",
        "app.footer_license": "License: PolyForm Noncommercial 1.0.0; contact the author for commercial licensing.",
        "source.section": "1. Video Selection",
        "source.label": "Choose video source",
        "source.local": "Local video",
        "source.upload": "Server upload",
        "source.hybrid": "Hybrid mode",
        "source.uploader": "Upload video file",
        "source.dir": "Scan directory or video file path",
        "source.file": "Choose video file",
        "source.file_placeholder": "Select a video file",
        "source.missing": "Video does not exist: {path}",
        "source.no_files": "No supported video files were found in this directory.",
        "source.empty": "Upload a video file or choose one from a local directory.",
        "source.mode_caption": "Current launch mode: {mode}",
        "source.pending": "No video selected yet",
        "overview.section": "2. Video Overview",
        "overview.duration": "Duration",
        "overview.path": "Current video",
        "overview.meta": "Resolution {resolution} · {fps} FPS",
        "preview.label": "Preview timestamp",
        "preview.help": "Drag the slider or enter a time directly, for example 00:12:34.",
        "preview.input": "Enter timecode",
        "preview.invalid": "Invalid time format. Use `HH:MM:SS` or total seconds.",
        "selector.section": "3. Select Region",
        "selector.caption": "Draw a rectangle on the image to choose the slide area included in the PDF.",
        "selector.empty": "The selectable preview appears here after a video is selected or uploaded.",
        "roi.left": "Left",
        "roi.top": "Top",
        "roi.width": "Width",
        "roi.height": "Height",
        "roi.reset": "Full frame",
        "summary.section": "4. Extraction",
        "summary.roi": "Current region",
        "summary.roi_value": "{width} x {height}",
        "summary.device": "Execution device",
        "summary.device_fallback": "{device}. {message}",
        "summary.max_slides": "Maximum pages",
        "summary.advanced": "Advanced settings",
        "advanced.output_dir": "Output directory (optional)",
        "advanced.output_dir_help": "Leave empty to create the result folder under the input video's directory.",
        "advanced.mode": "Similarity algorithm",
        "advanced.mode_help": "`ssim` is more stable; `histogram` is lighter; `ahash` is faster but rougher.",
        "advanced.device": "Execution device",
        "advanced.device_help": "CPU is the default. Switch to GPU enhancement or auto only when you want acceleration.",
        "advanced.sample": "Sampling interval (seconds)",
        "advanced.threshold": "Similarity threshold",
        "advanced.threshold_help": "For slide recordings, 0.98 is a good starting point.",
        "advanced.stable": "Minimum stable duration (seconds)",
        "advanced.stable_help": "Filters short transitions and slide animations.",
        "run.button": "Extract And Build PDF",
        "run.progress": "Extracting candidate slides and generating PDF...",
        "run.progress_idle": "Waiting to start",
        "run.progress_eta": "Estimated remaining time: {eta}",
        "run.progress_no_eta": "Estimating remaining time...",
        "run.stage.prepare": "Preparing task",
        "run.stage.sampling": "Sampling video frames",
        "run.stage.analyze": "Analyzing slide transitions",
        "run.stage.export": "Exporting slide images",
        "run.stage.pdf": "Building PDF",
        "run.stage.done": "Completed",
        "run.done": "Done. Extracted {count} slides on {device}.",
        "results.section": "5. Results",
        "results.empty": "After extraction, this area shows the PDF download and the thumbnail list.",
        "results.download": "Download PDF",
        "results.no_images": "No slide images were generated.",
        "results.delete": "Remove this slide",
        "results.restore": "Restore this slide",
        "results.delete_short": "[Delete]",
        "results.restore_short": "[Restore]",
        "results.dir": "Output directory",
    },
}


def _t(language: str, key: str, **kwargs) -> str:
    return TEXT[language][key].format(**kwargs)


def _apply_theme() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stHeader"] {
            display: none;
        }
        [data-testid="stToolbar"] {
            display: none;
        }
        .block-container {
            padding-top: 1.2rem;
        }
        div[data-testid="stNumberInput"] {
            margin-bottom: -0.35rem;
        }
        div[data-testid="stButton"] {
            margin-bottom: -0.35rem;
        }
        button[kind="tertiary"] {
            padding: 0;
            min-height: auto;
            border: 0;
            background: transparent;
            color: #6b7280;
            font-size: 0.8rem;
            line-height: 1.1;
        }
        button[kind="tertiary"]:hover {
            color: #111827;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


st.set_page_config(
    page_title="Screen To Slides",
    page_icon=APP_ICON,
    layout="wide",
)


def _get_app_source_mode() -> str:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--app-mode", choices=sorted(APP_SOURCE_MODES), default="local")
    args, _ = parser.parse_known_args(sys.argv[1:])
    return args.app_mode


def main() -> None:
    OUTPUTS_DIR.mkdir(exist_ok=True)
    UPLOADS_DIR.mkdir(exist_ok=True)
    _apply_theme()
    st.session_state.setdefault("roi_selector_version", 0)

    current_language = st.session_state.get("language", "zh")
    title_col, lang_col = st.columns([5.5, 1.4], gap="small")
    with title_col:
        if APP_ICON_B64:
            st.markdown(
                f"""
                <div style="display:flex; align-items:center; gap:0.6rem;">
                  <img src="data:image/png;base64,{APP_ICON_B64}" alt="logo" style="height:2.45rem; width:auto; display:block;" />
                  <h1 style="margin:0; font-size:2.45rem; line-height:1.1;">{_t(current_language, "app.title")}</h1>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.title(_t(current_language, "app.title"))
    with lang_col:
        language = st.selectbox(
            _t(current_language, "lang.label"),
            options=["zh", "en"],
            index=0 if current_language == "zh" else 1,
            format_func=lambda value: TEXT[current_language][f"lang.{value}"],
        )
    st.session_state["language"] = language

    if language != current_language:
        st.rerun()

    st.caption(_t(language, "app.subtitle"))

    app_mode = _get_app_source_mode()
    video_path = _render_source_panel(language, app_mode)
    metadata = None
    current_roi = None
    preview_image = None
    selector_image = None

    if video_path:
        metadata = get_video_metadata(video_path)
        current_roi = ensure_roi(st.session_state.get("roi"), metadata)
        st.session_state["roi"] = current_roi
        _render_video_summary(language, video_path, metadata)
        preview_seconds = _render_preview_locator(language, metadata)
        preview_image = load_preview_frame(video_path, float(preview_seconds))
        selector_image, scale = resize_for_selector(preview_image)
    else:
        _render_video_summary_empty(language)
        _render_preview_locator_empty(language)

    selection_col, settings_col = st.columns([1.5, 1.0], gap="large")
    with selection_col:
        st.subheader(_t(language, "selector.section"))
        st.caption(_t(language, "selector.caption"))
        if video_path and metadata is not None and current_roi is not None and selector_image is not None:
            selector_roi = _scale_roi_for_preview(current_roi, scale)
            selected_preview_roi = _render_roi_selector(selector_image, selector_roi)
            if selected_preview_roi is not None:
                st.session_state["roi"] = _scale_roi_to_original(selected_preview_roi, scale, metadata)
                st.session_state["roi_selector_version"] += 1
                st.rerun()
            _render_roi_inputs(language, current_roi, metadata)
            current_roi = ensure_roi(st.session_state["roi"], metadata)
            st.session_state["roi"] = current_roi
        else:
            _render_empty_roi_selector(language)
            _render_empty_roi_inputs(language)

    with settings_col:
        settings_offset_px = 72 if selector_image is None else max(48, min(180, int(selector_image.shape[0] * 0.18)))
        st.markdown(f"<div style='height:{settings_offset_px}px'></div>", unsafe_allow_html=True)
        st.subheader(_t(language, "summary.section"))
        is_upload = st.session_state.get("video_source_type") == "upload"
        config, output_root = _render_config_panel(language, video_path, is_upload)
        backend = get_execution_backend(config.execution_device)
        roi_text = (
            _t(language, "summary.roi_value", width=current_roi.width, height=current_roi.height)
            if current_roi is not None
            else "-"
        )
        st.caption(f"{_t(language, 'summary.roi')}: {roi_text}")
        device_note = (
            backend.display_name
            if backend.actual == "cuda"
            else _t(language, "summary.device_fallback", device=backend.display_name, message=backend.message)
        )
        st.caption(f"{_t(language, 'summary.device')}: {device_note}")
        progress_area = st.empty()
        run_clicked = st.button(
            _t(language, "run.button"),
            type="primary",
            width="stretch",
            disabled=video_path is None,
        )
        if run_clicked and video_path and current_roi is not None:
            st.session_state["excluded_slides"] = set()
            with progress_area.container():
                progress_bar = st.progress(0)
                progress_status = st.empty()
                progress_eta = st.empty()
                progress_status.caption(_t(language, "run.progress_idle"))
                progress_eta.caption(_t(language, "run.progress_no_eta"))

            def on_progress(update: ProgressUpdate) -> None:
                progress_bar.progress(int(round(update.progress * 100)))
                progress_status.caption(_progress_label(language, update))
                if update.eta_seconds is None or update.progress >= 1.0:
                    progress_eta.caption(
                        _t(language, "run.stage.done")
                        if update.progress >= 1.0
                        else _t(language, "run.progress_no_eta")
                    )
                else:
                    progress_eta.caption(
                        _t(language, "run.progress_eta", eta=_format_eta(update.eta_seconds))
                    )

            with st.spinner(_t(language, "run.progress")):
                result = extract_slides(
                    video_path=video_path,
                    roi=current_roi,
                    config=config,
                    output_root=output_root,
                    progress_callback=on_progress,
                )
            st.session_state["last_result_dir"] = str(result.output_dir)
            progress_bar.progress(100)
            progress_status.caption(_t(language, "run.stage.done"))
            progress_eta.caption(_t(language, "run.progress_eta", eta="0s"))
            st.success(
                _t(
                    language,
                    "run.done",
                    count=len(result.slides),
                    device=result.execution_device,
                )
            )

    _render_result_section(language)
    _render_footer(language)


def _render_source_panel(language: str, app_mode: str) -> Path | None:
    st.subheader(_t(language, "source.section"))
    st.caption(_t(language, "source.mode_caption", mode=_t(language, f"source.{app_mode}")))

    if app_mode == "hybrid":
        source_mode = st.radio(
            _t(language, "source.label"),
            options=["local", "upload"],
            horizontal=True,
            format_func=lambda value: _t(language, f"source.{value}"),
        )
    else:
        source_mode = app_mode

    if source_mode == "local":
        st.session_state["video_source_type"] = "local"
        source_default = st.session_state.get(
            "local_video_source",
            str(ROOT),
        )
        source_value = st.text_input(_t(language, "source.dir"), value=source_default).strip()
        st.session_state["local_video_source"] = source_value

        source_path = Path(source_value).expanduser() if source_value else ROOT
        selected_from_path: Path | None = None
        local_dir = source_path
        if source_path.suffix.lower() in VIDEO_EXTENSIONS:
            if source_path.exists() and source_path.is_file():
                selected_from_path = source_path
                local_dir = source_path.parent
            else:
                st.warning(_t(language, "source.missing", path=source_path))
                return None

        st.session_state["local_video_dir"] = str(local_dir)
        local_files = _list_local_videos(local_dir)
        if not local_files:
            st.info(_t(language, "source.no_files"))
            return None

        selected_index = None
        if selected_from_path is not None:
            try:
                selected_index = local_files.index(selected_from_path)
            except ValueError:
                selected_index = None
        else:
            selected_from_state = st.session_state.get("local_selected_video")
            if selected_from_state:
                selected_path = Path(selected_from_state)
                if selected_path in local_files:
                    selected_index = local_files.index(selected_path)

        selected_file = st.selectbox(
            _t(language, "source.file"),
            options=local_files,
            index=selected_index,
            placeholder=_t(language, "source.file_placeholder"),
            format_func=lambda path: str(path.relative_to(local_dir)) if local_dir in path.parents or path == local_dir else str(path),
        )
        if selected_file is None:
            st.session_state.pop("video_path", None)
            st.session_state["local_selected_video"] = ""
            return None

        st.session_state["video_path"] = str(selected_file)
        st.session_state["local_selected_video"] = str(selected_file)
        return selected_file

    st.session_state["video_source_type"] = "upload"
    uploaded = st.file_uploader(
        _t(language, "source.uploader"),
        type=[extension.lstrip(".") for extension in sorted(VIDEO_EXTENSIONS)],
    )
    if not uploaded:
        return None

    suffix = Path(uploaded.name).suffix or ".mp4"
    safe_name = Path(uploaded.name).stem.replace(" ", "_")
    upload_path = UPLOADS_DIR / f"{safe_name}_{uploaded.size}{suffix}"
    if not upload_path.exists() or upload_path.stat().st_size != uploaded.size:
        upload_path.write_bytes(uploaded.getbuffer())

    st.session_state["video_path"] = str(upload_path)
    return upload_path


def _render_footer(language: str) -> None:
    st.markdown("---")
    st.caption(_t(language, "app.footer_meta", version=__version__, url=GITHUB_URL))
    st.caption(_t(language, "app.footer_license"))


def _render_video_summary(language: str, video_path: Path, metadata) -> None:
    st.subheader(_t(language, "overview.section"))
    cols = st.columns([1.1, 2.9], gap="large")
    cols[0].metric(_t(language, "overview.duration"), _format_seconds(metadata.duration_seconds))
    with cols[1]:
        display_video = video_path.name if st.session_state.get("video_source_type") == "upload" else str(video_path)
        st.caption(f"{_t(language, 'overview.path')}: `{display_video}`")
        st.caption(
            _t(
                language,
                "overview.meta",
                resolution=f"{metadata.width} x {metadata.height}",
                fps=f"{metadata.fps:.2f}",
            )
        )


def _render_video_summary_empty(language: str) -> None:
    st.subheader(_t(language, "overview.section"))
    cols = st.columns([1.1, 2.9], gap="large")
    cols[0].metric(_t(language, "overview.duration"), "--:--:--")
    with cols[1]:
        st.caption(f"{_t(language, 'overview.path')}: `{_t(language, 'source.pending')}`")
        st.caption(_t(language, "overview.meta", resolution="-- x --", fps="--"))


def _list_local_videos(directory: Path) -> list[Path]:
    if not directory.exists() or not directory.is_dir():
        return []
    candidates = sorted(
        path for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    )
    return [path for path in candidates if path.is_file()][:200]


def _render_preview_locator(language: str, metadata) -> int:
    total_seconds = max(int(round(metadata.duration_seconds)), 0)
    if "preview_seconds" not in st.session_state:
        st.session_state["preview_seconds"] = 0
    if "preview_hms_input" not in st.session_state:
        st.session_state["preview_hms_input"] = _format_seconds(st.session_state["preview_seconds"])
    st.session_state["preview_seconds"] = max(0, min(st.session_state["preview_seconds"], total_seconds))

    previous_seconds = int(st.session_state["preview_seconds"])
    preview_seconds = st.select_slider(
        _t(language, "preview.label"),
        options=list(range(total_seconds + 1)),
        value=int(st.session_state["preview_seconds"]),
        format_func=_format_seconds,
        help=_t(language, "preview.help"),
    )
    st.session_state["preview_seconds"] = preview_seconds
    if preview_seconds != previous_seconds:
        st.session_state["preview_hms_input"] = _format_seconds(preview_seconds)

    entered_value = st.text_input(
        _t(language, "preview.input"),
        key="preview_hms_input",
    ).strip()
    parsed_seconds = _parse_timecode(entered_value)
    if entered_value and parsed_seconds is None:
        st.caption(_t(language, "preview.invalid"))
    elif parsed_seconds is not None:
        clamped = max(0, min(parsed_seconds, total_seconds))
        if clamped != st.session_state["preview_seconds"]:
            st.session_state["preview_seconds"] = clamped
            st.session_state["preview_hms_input"] = _format_seconds(clamped)
            st.rerun()

    return int(st.session_state["preview_seconds"])


def _render_preview_locator_empty(language: str) -> None:
    st.select_slider(
        _t(language, "preview.label"),
        options=[0, 1],
        value=0,
        format_func=_format_seconds,
        help=_t(language, "preview.help"),
        disabled=True,
    )
    st.text_input(
        _t(language, "preview.input"),
        value="00:00:00",
        disabled=True,
    )


def _render_roi_selector(image_rgb: np.ndarray, roi: Roi) -> Roi | None:
    height, width = image_rgb.shape[:2]
    grid_step = max(2, int(width / 180))
    xs, ys = np.meshgrid(np.arange(0, width, grid_step), np.arange(0, height, grid_step))
    fig = go.Figure()
    fig.add_layout_image(
        dict(
            source=_to_pil_image(image_rgb),
            x=0,
            y=0,
            sizex=width,
            sizey=height,
            xref="x",
            yref="y",
            sizing="stretch",
            yanchor="top",
            layer="below",
        )
    )
    fig.add_trace(
        go.Scattergl(
            x=xs.ravel(),
            y=ys.ravel(),
            mode="markers",
            marker={"size": 6, "color": "rgba(0, 0, 0, 0.02)"},
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.add_shape(
        type="rect",
        x0=roi.x,
        y0=roi.y,
        x1=roi.x2,
        y1=roi.y2,
        line={"color": "#ff6a3d", "width": 3},
        fillcolor="rgba(255, 106, 61, 0.12)",
    )
    fig.update_xaxes(visible=False, range=[0, width])
    fig.update_yaxes(visible=False, range=[height, 0], scaleanchor="x")
    fig.update_layout(
        width=width,
        height=height,
        margin=dict(l=0, r=0, t=0, b=0),
        dragmode="select",
        paper_bgcolor="white",
        plot_bgcolor="white",
    )

    event = st.plotly_chart(
        fig,
        key=f"roi_selector_{st.session_state.get('roi_selector_version', 0)}",
        on_select="rerun",
        selection_mode=("box",),
        config={
            "displaylogo": False,
            "scrollZoom": False,
            "doubleClick": False,
            "modeBarButtonsToRemove": [
                "toImage",
                "lasso2d",
            ],
        },
    )
    selection = getattr(event, "selection", None) if event else None
    box = getattr(selection, "box", None) if selection else None
    points = getattr(selection, "points", None) if selection else None
    box_roi = _extract_roi_from_box_metadata(box, width=width, height=height)
    if box_roi is not None:
        return box_roi
    if points:
        xs_selected = [point["x"] for point in points if "x" in point]
        ys_selected = [point["y"] for point in points if "y" in point]
        if xs_selected and ys_selected:
            x0 = int(max(min(xs_selected), 0))
            y0 = int(max(min(ys_selected), 0))
            x1 = int(min(max(xs_selected), width))
            y1 = int(min(max(ys_selected), height))
            if x1 <= x0:
                x1 = min(x0 + grid_step, width)
            if y1 <= y0:
                y1 = min(y0 + grid_step, height)
            if x1 > x0 and y1 > y0:
                return Roi(x=x0, y=y0, width=x1 - x0, height=y1 - y0)
    return None


def _render_empty_roi_selector(language: str) -> None:
    st.markdown(
        f"""
        <div style="
            height: 360px;
            border: 1px dashed #d1d5db;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #9ca3af;
            font-size: 0.95rem;
            background: #fafafa;
        ">
            {_t(language, "selector.empty")}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_roi_inputs(language: str, current_roi: Roi, metadata) -> None:
    label_cols = st.columns(5, gap="small")
    labels = [
        _t(language, "roi.left"),
        _t(language, "roi.top"),
        _t(language, "roi.width"),
        _t(language, "roi.height"),
    ]
    for col, label in zip(label_cols[:4], labels):
        col.markdown(f"<div style='text-align:center; color:#6b7280; font-size:0.875rem;'>{label}</div>", unsafe_allow_html=True)
    label_cols[4].caption("")

    input_cols = st.columns(5, gap="small", vertical_alignment="bottom")
    roi_values = {
        "x": input_cols[0].number_input(
            "x",
            min_value=0,
            max_value=metadata.width - 1,
            value=int(current_roi.x),
            step=1,
            label_visibility="collapsed",
        ),
        "y": input_cols[1].number_input(
            "y",
            min_value=0,
            max_value=metadata.height - 1,
            value=int(current_roi.y),
            step=1,
            label_visibility="collapsed",
        ),
        "width": input_cols[2].number_input(
            "width",
            min_value=1,
            max_value=metadata.width,
            value=int(current_roi.width),
            step=1,
            label_visibility="collapsed",
        ),
        "height": input_cols[3].number_input(
            "height",
            min_value=1,
            max_value=metadata.height,
            value=int(current_roi.height),
            step=1,
            label_visibility="collapsed",
        ),
    }
    if input_cols[4].button(_t(language, "roi.reset"), width="stretch"):
        st.session_state["roi"] = Roi(x=0, y=0, width=metadata.width, height=metadata.height)
    else:
        st.session_state["roi"] = Roi(**roi_values).clipped(metadata.width, metadata.height)


def _render_empty_roi_inputs(language: str) -> None:
    label_cols = st.columns(5, gap="small")
    labels = [
        _t(language, "roi.left"),
        _t(language, "roi.top"),
        _t(language, "roi.width"),
        _t(language, "roi.height"),
    ]
    for col, label in zip(label_cols[:4], labels):
        col.markdown(
            f"<div style='text-align:center; color:#6b7280; font-size:0.875rem;'>{label}</div>",
            unsafe_allow_html=True,
        )
    label_cols[4].caption("")

    input_cols = st.columns(5, gap="small", vertical_alignment="bottom")
    for idx, key in enumerate(["x", "y", "width", "height"]):
        input_cols[idx].number_input(
            key,
            min_value=0,
            value=0,
            step=1,
            label_visibility="collapsed",
            disabled=True,
            key=f"empty_{key}_input",
        )
    input_cols[4].button(
        _t(language, "roi.reset"),
        width="stretch",
        disabled=True,
        key="empty_roi_reset",
    )


def _render_config_panel(language: str, video_path: Path | None, is_upload: bool) -> tuple[ExtractConfig, Path]:
    max_slides = st.number_input(_t(language, "summary.max_slides"), min_value=1, max_value=1000, value=200, step=1)
    with st.expander(_t(language, "summary.advanced"), expanded=False):
        output_dir_value = ""
        if not is_upload:
            output_dir_value = st.text_input(
                _t(language, "advanced.output_dir"),
                value=st.session_state.get("output_root_input", ""),
                help=_t(language, "advanced.output_dir_help"),
            ).strip()
            st.session_state["output_root_input"] = output_dir_value
        mode = st.selectbox(
            _t(language, "advanced.mode"),
            options=["ssim", "histogram", "ahash"],
            help=_t(language, "advanced.mode_help"),
        )
        execution_device = st.selectbox(
            _t(language, "advanced.device"),
            options=["auto", "cpu", "gpu"],
            index=1,
            help=_t(language, "advanced.device_help"),
        )
        sample_every_seconds = st.slider(
            _t(language, "advanced.sample"),
            min_value=0.5,
            max_value=5.0,
            value=float(DEFAULT_SAMPLE_SECONDS),
            step=0.5,
        )
        similarity_threshold = st.slider(
            _t(language, "advanced.threshold"),
            min_value=0.80,
            max_value=0.999,
            value=float(DEFAULT_SIMILARITY_THRESHOLD),
            step=0.001,
            help=_t(language, "advanced.threshold_help"),
        )
        min_stable_seconds = st.slider(
            _t(language, "advanced.stable"),
            min_value=0.5,
            max_value=10.0,
            value=float(DEFAULT_MIN_STABLE_SECONDS),
            step=0.5,
            help=_t(language, "advanced.stable_help"),
        )
    output_root = Path(output_dir_value).expanduser() if output_dir_value else (video_path.parent if video_path else OUTPUTS_DIR)
    return (
        ExtractConfig(
            mode=mode,
            execution_device=execution_device,
            sample_every_seconds=sample_every_seconds,
            similarity_threshold=similarity_threshold,
            min_stable_seconds=min_stable_seconds,
            max_slides=int(max_slides),
        ),
        output_root,
    )


def _render_result_section(language: str) -> None:
    st.subheader(_t(language, "results.section"))
    result_dir_value = st.session_state.get("last_result_dir")
    if not result_dir_value:
        st.info(_t(language, "results.empty"))
        return

    result_dir = Path(result_dir_value)
    slide_paths = sorted((result_dir / "slides").glob("*.jpg"))
    if not slide_paths:
        st.warning(_t(language, "results.no_images"))
        return

    # Initialize excluded slides set
    if "excluded_slides" not in st.session_state:
        st.session_state["excluded_slides"] = set()

    excluded = st.session_state["excluded_slides"]

    # Build PDF only from non-excluded slides
    included_paths = [p for i, p in enumerate(slide_paths) if i not in excluded]
    pdf_name = f"{result_dir.name}.pdf"
    if included_paths:
        from PIL import Image as PILImage
        from pypdf import PdfReader, PdfWriter
        from screen_to_slides.extractor import SlideArtifact, _format_timestamp_display
        import io

        # Read manifest for timestamps
        manifest_path = result_dir / "manifest.json"
        timestamps = {}
        if manifest_path.exists():
            import json
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for s in manifest.get("slides", []):
                ts = s.get("timestamp_seconds", 0)
                img = s.get("image_path", "")
                timestamps[Path(img).name] = ts

        pil_images = []
        for p in included_paths:
            pil_images.append(PILImage.open(p).convert("RGB"))

        # Generate PDF in memory
        buf = io.BytesIO()
        if pil_images:
            first, *rest = pil_images
            first.save(buf, format="PDF", resolution=100.0, save_all=True, append_images=rest)

            # Add bookmarks with timestamps
            reader = PdfReader(buf)
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            for idx, p in enumerate(included_paths):
                ts = timestamps.get(p.name, 0)
                label = f"Page {idx + 1} - {_format_timestamp_display(ts)}"
                writer.add_outline_item(label, idx)
            final_buf = io.BytesIO()
            writer.write(final_buf)
            pdf_bytes = final_buf.getvalue()
        else:
            pdf_bytes = b""

        if pdf_bytes:
            st.download_button(
                _t(language, "results.download"),
                data=pdf_bytes,
                file_name=pdf_name,
                mime="application/pdf",
                width="stretch",
            )

    st.caption(f"{_t(language, 'results.dir')}: `{result_dir.name}`")

    # Thumbnail gallery: small top-left toggle text above each image
    gallery_cols = st.columns(3)
    for index, slide_path in enumerate(slide_paths):
        column = gallery_cols[index % len(gallery_cols)]
        with column:
            _deleted = index in excluded
            _toggle_label = _t(language, "results.restore_short") if _deleted else _t(language, "results.delete_short")
            _toggle_help = _t(language, "results.restore") if _deleted else _t(language, "results.delete")
            if st.button(
                _toggle_label,
                key=f"toggle_slide_{index}",
                type="tertiary",
                help=_toggle_help,
                width="content",
            ):
                if _deleted:
                    excluded.discard(index)
                else:
                    excluded.add(index)
                st.rerun()
            with open(slide_path, "rb") as _imgf:
                _b64 = base64.b64encode(_imgf.read()).decode()
            _img_style = "filter:grayscale(0.8) opacity(0.45);" if _deleted else ""
            _overlay_html = (
                '<div style="position:absolute;inset:0;background:rgba(128,128,128,0.35);pointer-events:none;"></div>'
                if _deleted
                else ""
            )
            _thumbnail_html = (
                '<div style="position:relative;display:inline-block;width:100%;border-radius:6px;overflow:hidden;">'
                f'<img src="data:image/jpeg;base64,{_b64}" style="width:100%;display:block;{_img_style}"/>'
                f"{_overlay_html}"
                "</div>"
            )
            st.markdown(_thumbnail_html, unsafe_allow_html=True)


def _to_pil_image(image_rgb: np.ndarray):
    from PIL import Image

    return Image.fromarray(image_rgb)


def _scale_roi_for_preview(roi: Roi, scale: float) -> Roi:
    if scale == 1.0:
        return roi
    return Roi(
        x=int(round(roi.x * scale)),
        y=int(round(roi.y * scale)),
        width=max(1, int(round(roi.width * scale))),
        height=max(1, int(round(roi.height * scale))),
    )


def _scale_roi_to_original(roi: Roi, scale: float, metadata) -> Roi:
    if scale == 1.0:
        return roi.clipped(metadata.width, metadata.height)
    inverse = 1.0 / scale
    return Roi(
        x=int(round(roi.x * inverse)),
        y=int(round(roi.y * inverse)),
        width=max(1, int(round(roi.width * inverse))),
        height=max(1, int(round(roi.height * inverse))),
    ).clipped(metadata.width, metadata.height)


def _format_seconds(seconds: float) -> str:
    seconds = int(round(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _parse_timecode(value: str) -> int | None:
    if not value:
        return None
    stripped = value.strip()
    if stripped.isdigit():
        return int(stripped)

    parts = stripped.split(":")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        return None

    hours, minutes, seconds = (int(part) for part in parts)
    if minutes >= 60 or seconds >= 60:
        return None
    return hours * 3600 + minutes * 60 + seconds


def _extract_roi_from_box_metadata(box_metadata, width: int, height: int) -> Roi | None:
    if not box_metadata:
        return None

    item = box_metadata[0]
    if item is None:
        return None

    x0 = x1 = y0 = y1 = None

    if all(key in item for key in ("x0", "x1", "y0", "y1")):
        x0, x1, y0, y1 = item["x0"], item["x1"], item["y0"], item["y1"]
    elif "range" in item and isinstance(item["range"], dict):
        x_range = item["range"].get("x")
        y_range = item["range"].get("y")
        if isinstance(x_range, (list, tuple)) and len(x_range) == 2:
            x0, x1 = x_range
        if isinstance(y_range, (list, tuple)) and len(y_range) == 2:
            y0, y1 = y_range
    elif all(key in item for key in ("x", "y")):
        x_vals = item.get("x")
        y_vals = item.get("y")
        if isinstance(x_vals, (list, tuple)) and len(x_vals) >= 2:
            x0, x1 = x_vals[0], x_vals[-1]
        if isinstance(y_vals, (list, tuple)) and len(y_vals) >= 2:
            y0, y1 = y_vals[0], y_vals[-1]

    if None in (x0, x1, y0, y1):
        return None

    left = int(round(max(min(x0, x1), 0)))
    right = int(round(min(max(x0, x1), width)))
    top = int(round(max(min(y0, y1), 0)))
    bottom = int(round(min(max(y0, y1), height)))

    if right <= left or bottom <= top:
        return None
    return Roi(x=left, y=top, width=right - left, height=bottom - top)


def _format_eta(seconds: float) -> str:
    seconds = max(int(round(seconds)), 0)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    if minutes > 0:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def _progress_label(language: str, update: ProgressUpdate) -> str:
    stage_key = f"run.stage.{update.stage}"
    label = TEXT[language].get(stage_key, update.message)
    percent = int(round(update.progress * 100))
    return f"{label} · {percent}%"


if __name__ == "__main__":
    main()
