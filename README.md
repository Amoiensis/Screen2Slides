# Screen To Slides

从电脑录制的线上会议视频中，针对指定矩形区域自动抽取 PPT 页，并导出为 PDF。

## 当前版本能力

- `Streamlit` 单页应用，支持示例视频和 MP4 上传
- 在预览帧上框选希望纳入 PDF 的矩形区域
- 可选 `Auto / CPU / GPU` 执行设备，检测到 CUDA 时优先做相似度计算加速
- 支持 3 种相似度算法:
  - `ssim`: 基于 `scikit-image` 的结构相似度，默认推荐
  - `histogram`: 基于灰度直方图相关性，较轻量
  - `ahash`: 平均哈希，速度快但对布局细节不如 `ssim`
- 抽取结果同时保存为:
  - `slides/*.jpg`
  - `slides.pdf`
  - `manifest.json`

## 运行环境

推荐使用你给出的 Conda 环境:

```bash
conda activate py39_cuda12.4
cd /data_hdd_lvm/data_store/screen_to_slides
bash run_app.sh
```

应用默认监听 `0.0.0.0:9555`，局域网内其他机器也可以访问。

## 使用说明

1. 选择示例视频或上传新 MP4。
2. 调整预览时间点到 PPT 比较清晰的时刻。
3. 在图上用框选工具拖出 PPT 区域。
4. 如有需要，手工微调 `x / y / width / height`。
5. 选择抽取算法和阈值。
6. 点击 `开始抽取并生成 PDF`。

## 参数建议

- 会议录屏里 PPT 结构相对稳定时，优先用 `ssim`
- 如环境中 `torch.cuda.is_available()` 为真，可在界面选择 `gpu`
- `similarity_threshold=0.98` 是一个适合 PPT 场景的起点
- 如果切页频繁漏检，可以降低到 `0.95 ~ 0.97`
- 如果同一页被拆成多页，可以提高阈值或增大 `最短稳定时长`

## 参考思路

- SSIM: Wang, Bovik, Sheikh, Simoncelli, "Image Quality Assessment: From Error Visibility to Structural Similarity", 2004
- `scikit-image.metrics.structural_similarity`
- 场景切分项目可以参考 `PySceneDetect` 的内容检测思路
- `wudududu/extract-video-ppt`: 直接基于帧间相似度阈值导出 PDF，适合作为轻量规则方案参考
- `Wangxs404/video2ppt`: 面向更完整视频转课件流程的项目，适合作为后续扩展参考

当前仓库没有直接拷贝这些项目代码，只借鉴了它们在 "帧采样 + 相似度判定 + 导出" 这类流程上的思路，目的是保持部署尽量轻便。
