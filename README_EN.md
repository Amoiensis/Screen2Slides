<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td width="72" valign="middle" style="border:none; padding:0 12px 0 0;">
      <img src="assets/amoiensis_samll.png" alt="Screen2Slides Logo" width="56">
    </td>
    <td valign="middle" style="border:none; padding:0;">
      <h1>Screen2Slides</h1>
    </td>
  </tr>
</table>

[中文说明](README.md) | [English](README_EN.md)

Screen2Slides extracts slide-like pages from screen recordings, meeting recordings, or lecture videos by analyzing a user-selected rectangular region, then exports the result as a PDF.

## Workflow

1. Start the app and open it in a browser.
2. Select a video.
3. Draw the slide region.
4. Click the extraction button.
5. Review the results and download the PDF.

Quick start guidance:

- For personal use, start with `run_app_local.sh`
- The default `cpu + ssim` setup is enough to get started
- Keep advanced settings collapsed until you actually need tuning

## Example

The following example shows a complete meeting-video extraction flow.

Example meeting video:

- https://www.bilibili.com/video/BV15Rx5eXEnW/

Select the slide region and run the analysis:

![](./docs/image/select_area.png)

Export the resulting PDF:

![](./docs/image/slides_download.png)

Reference full PDF provided by the lab for result verification:

- https://alignmentsurvey.com/uploads/pair_lab/talks/post_train.pdf

## Features

- Three launch modes: local, upload, and hybrid
- Region-of-interest selection on a preview frame
- Three similarity algorithms: `ssim`, `histogram`, and `ahash`
- `cpu / gpu / auto` execution device options
- Thumbnail review with manual delete and restore before PDF export
- Outputs `slides/*.jpg`, `slides.pdf`, and `manifest.json`
- Adds timestamp-based bookmarks to the generated PDF

## Suggested Settings

Default guidance:

- The default `cpu` mode is enough for normal use
- Enable `gpu` or `auto` only when you want acceleration
- Start with `ssim` in most cases

Recommended presets:

| Scenario | Algorithm | Similarity threshold |
| --- | --- | --- |
| Slide region is fully known and there are no subtitle overlays | `ssim` | `0.98` |
| Slide region is fully known but subtitle overlays are present | `ssim` | `0.92` |
| Slide region is fully known but the speaker appears in a small picture-in-picture window | `ssim` | `0.85` |
| Slide region is hard to isolate and the camera view changes frequently | `ssim` | `0.80` |

Tuning direction:

- If too many pages are missed, reduce the sampling interval, reduce the minimum stable duration, and slightly raise the similarity threshold
- If too many duplicate pages appear, slightly lower the similarity threshold

## Environment

- Python `3.9+`
- A Conda or virtualenv environment is recommended
- Base dependencies are listed in `requirements.txt`
- CPU is the default and works out of the box with no extra GPU setup
- Install `torch` separately if you want optional GPU acceleration

Install dependencies:

```bash
pip install -r requirements.txt
```

If you use Conda, activate your environment first:

```bash
conda activate <your_env_name>
pip install -r requirements.txt
```

## Launch Modes

The app listens on `0.0.0.0:9555` by default.

Accessible URLs:

- Local access: <http://localhost:9555>
- LAN access: `http://<your_server_ip>:9555`

For personal use, local mode is the recommended default:

```bash
bash run_app_local.sh
```

Windows equivalent:

```bat
run_app_local.bat
```

Script summary:

| Scenario | macOS / Linux | Windows | Description |
| --- | --- | --- | --- |
| Default local mode | `bash run_app_local.sh` | `run_app_local.bat` | Local-only mode, best for personal use |
| Upload-only mode | `bash run_app_upload.sh` | `run_app_upload.bat` | Shows the upload entry only |
| Hybrid mode | `bash run_app_hybrid.sh` | `run_app_hybrid.bat` | Lets the user switch between local selection and upload |
| Default alias | `bash run_app.sh` | `run_app.bat` | Same as local mode |

To override the Python executable:

```bash
PYTHON_BIN=python bash run_app_local.sh
```

On Windows, you can set the environment variable first, for example:

```bat
set PYTHON_BIN=python
run_app_local.bat
```

## Local CLI

In addition to the web UI, the project also supports local command-line usage.

Minimal usage:

```bash
bash run_cli.sh /path/to/video.mp4
```

Windows equivalent:

```bat
run_cli.bat C:\path\to\video.mp4
```

Equivalent form:

```bash
python -m screen_to_slides.cli /path/to/video.mp4
```

Common arguments:

- `--output-dir`: output root directory, defaults to the input video's parent directory
- `--mode`: `ssim` / `histogram` / `ahash`
- `--device`: `cpu` / `gpu` / `auto`, default is `cpu`
- `--sample-every-seconds`: sampling interval, default `1.0`
- `--similarity-threshold`: similarity threshold, default `0.98`
- `--min-stable-seconds`: minimum stable duration, default `2.0`
- `--max-slides`: maximum exported pages, default `200`
- `--x --y --width --height`: explicit ROI values; if all are omitted, the whole frame is used

Example:

```bash
bash run_cli.sh /path/to/video.mp4 \
  --mode ssim \
  --device cpu \
  --similarity-threshold 0.92 \
  --sample-every-seconds 0.5 \
  --min-stable-seconds 1.0 \
  --max-slides 300
```

## Output

Each run creates a result directory named with the video name plus a random suffix. It typically contains:

- `slides/`: extracted page images
- `slides.pdf`: generated PDF
- `manifest.json`: timestamps and page metadata

## Online Demo and Data Safety

You can try the project online first:

- <http://www.peking.ren/screen2slides/>

Notes:

- The public demo is intended for quick evaluation and light testing
- Upload and processing size limits are enforced because online resources are limited
- For further discussion, feedback, or access to more stable and better-provisioned online resources, you can join the QQ group: `1097740457`

<img src="./docs/comunity/QQ_Gorup_1097740457.JPG" alt="QQ Group 1097740457" width="260">

Meeting recordings, lecture videos, and screen captures often involve copyright, privacy, or internal materials. The project also supports self-hosted local deployment, so videos, extracted frames, and generated PDFs can be processed entirely on your own machine without sending data to a third-party service.

## License

This project uses `PolyForm Noncommercial 1.0.0`.

- Non-commercial use is allowed
- Commercial use, enterprise deployment, redistribution, or other licensing cooperation requires a separate commercial license from the author
- This is more accurately source-available, not a traditional OSI open source license

- Amoiensis
- GitHub: <https://github.com/Amoiensis>
- Email: <amoiensis@outlook.com>

See [LICENSE](LICENSE) for the full terms.

Current version: `0.1.0`

GitHub: <https://github.com/Amoiensis/Screen2Slides>
