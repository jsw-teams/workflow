# 视频工作流

完整示例：[《垃圾車來了！》160 秒旁白字幕版](环境互动视频流/examples/garbage-truck/film.mp4)。

|流程|负责什么|已有素材|
|---|---|---|
|[动图与动作库制作](动图与动作库制作/README.md)|人物 ID、关键姿态、一次性动作、GIF / WebP 预览及检索标签|八姿态挥剑 GIF；重置接点明确标记|
|[有限动画与低成本静态视频流](有限动画与低成本静态视频流/README.md)|复用背景和少量人物纹理，限制环境交互，节省整张场景的重复生成；独立量测动作|固定落脚／取消约束对照，编码后鞋底量测|
|[环境互动视频流](环境互动视频流/README.md)|人物、道具与背景整张生成，组织小接触事件与画外旁白，限制复杂遮挡|76 张整场景姿态、11 段旁白、43 条旁白字幕、完整 160 秒成片|

共用原创形象结构预留在 [characters/original](characters/original/README.md)。造型尚未决定，未填项保持空值。动作索引引用动作库，不重复保存另一套图片。

## 从仓库根目录执行

需要 Python 3.11+、FFmpeg / FFprobe；重新合成语音还需要 Node.js 22+ 与 Git。字幕需要 Microsoft JhengHei（Windows）或 Noto Sans CJK TC（Linux）。

```sh
python -m pip install -r media-video/requirements.txt
python "media-video/动图与动作库制作/build_preview.py" "media-video/动图与动作库制作/actions/sword-swing"
python "media-video/有限动画与低成本静态视频流/measure.py" --evidence "media-video/有限动画与低成本静态视频流/evidence"
python "media-video/环境互动视频流/render.py"
python "media-video/环境互动视频流/verify.py"
```

这些命令使用保存素材，不调用 ImageGen 或在线 TTS。需要新的生成时，以完整上一影格、场景和人物参考准备工具输入；生成后先检视，失败图移到独立失败目录。

## 效果与限制

环境互动流程已能重建完整的日常叙事作品，旁白和字幕不依赖人物嘴型。它仍以原图停留与切接为主，尚未证明稳定的连续人物动画。源图原生尺寸为 836×470 和 1672×941，1080p 是放大后的编码尺寸。

复杂人物／栏杆遮挡、密集自然步态、物品计数仍可能失败。低成本路线不适合这些接触事件；环境互动路线也要拆分接触、避开密集前景和多人肢体交叠。模型、seed、参考权重与实际账单未由生成工具公开，不把调用数当成真实费用。

素材来源与第三方工具说明见 [ASSETS.md](ASSETS.md) 和 [THIRD_PARTY.md](THIRD_PARTY.md)。
