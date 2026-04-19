from __future__ import annotations

import sys
from pathlib import Path


DEMO_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = DEMO_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import app as base_app


DEMO_VIDEO = DEMO_ROOT / "screen2slides_demo.mp4"
DEMO_UPLOADS_DIR = DEMO_ROOT / "uploads"
DEMO_OUTPUTS_DIR = DEMO_ROOT / "outputs"
MAX_UPLOAD_BYTES = 80 * 1024 * 1024

base_app.UPLOADS_DIR = DEMO_UPLOADS_DIR
base_app.OUTPUTS_DIR = DEMO_OUTPUTS_DIR

base_app.TEXT["zh"].update(
    {
        "app.subtitle": "测试环境 Demo：本地样例固定为 screen2slides_demo.mp4，上传仅支持小于 80 MB 的 MP4。",
        "source.demo_note": "测试环境限制：本地模式仅提供固定样例文件，上传模式仅支持小于 80 MB 的 MP4。",
        "source.demo_fixed": "固定样例视频",
        "source.demo_missing": "测试样例不存在，请在当前目录放置 screen2slides_demo.mp4。",
        "source.upload_limit": "上传文件需为 MP4，且大小必须小于 80 MB。",
        "source.upload_selected": "已上传文件",
    }
)
base_app.TEXT["en"].update(
    {
        "app.subtitle": "Demo environment: local mode uses a fixed screen2slides_demo.mp4 file, and upload mode accepts MP4 files smaller than 80 MB only.",
        "source.demo_note": "Demo restriction: local mode uses one fixed sample file, and upload mode accepts MP4 files smaller than 80 MB only.",
        "source.demo_fixed": "Fixed demo video",
        "source.demo_missing": "The demo sample is missing. Please place screen2slides_demo.mp4 in this folder.",
        "source.upload_limit": "Uploads must be MP4 files smaller than 80 MB.",
        "source.upload_selected": "Uploaded file",
    }
)


def _render_demo_source_panel(language: str, app_mode: str) -> Path | None:
    base_app.st.subheader(base_app._t(language, "source.section"))
    base_app.st.caption(base_app._t(language, "source.mode_caption", mode=base_app._t(language, f"source.{app_mode}")))
    base_app.st.info(base_app._t(language, "source.demo_note"))

    if app_mode == "hybrid":
        source_mode = base_app.st.radio(
            base_app._t(language, "source.label"),
            options=["local", "upload"],
            horizontal=True,
            format_func=lambda value: base_app._t(language, f"source.{value}"),
        )
    else:
        source_mode = app_mode

    if source_mode == "local":
        base_app.st.session_state["video_source_type"] = "local"
        base_app.st.text_input(
            base_app._t(language, "source.demo_fixed"),
            value=DEMO_VIDEO.name,
            disabled=True,
        )
        if not DEMO_VIDEO.exists():
            base_app.st.warning(base_app._t(language, "source.demo_missing"))
            return None
        base_app.st.session_state["video_path"] = str(DEMO_VIDEO)
        return DEMO_VIDEO

    base_app.st.session_state["video_source_type"] = "upload"
    uploaded = base_app.st.file_uploader(
        base_app._t(language, "source.uploader"),
        type=["mp4"],
        help=base_app._t(language, "source.upload_limit"),
    )
    if not uploaded:
        return None

    if uploaded.size >= MAX_UPLOAD_BYTES or Path(uploaded.name).suffix.lower() != ".mp4":
        base_app.st.error(base_app._t(language, "source.upload_limit"))
        return None

    safe_name = Path(uploaded.name).stem.replace(" ", "_")
    upload_path = DEMO_UPLOADS_DIR / f"{safe_name}_{uploaded.size}.mp4"
    DEMO_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    if not upload_path.exists() or upload_path.stat().st_size != uploaded.size:
        upload_path.write_bytes(uploaded.getbuffer())

    base_app.st.caption(f"{base_app._t(language, 'source.upload_selected')}: `{uploaded.name}`")
    base_app.st.session_state["video_path"] = str(upload_path)
    return upload_path


base_app._render_source_panel = _render_demo_source_panel


def main() -> None:
    DEMO_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    DEMO_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    base_app.main()


if __name__ == "__main__":
    main()
