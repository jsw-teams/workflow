# Workflow

AI 辅助视频制作的代码、提示词和审查记录。图片与视频统一存放在 ishare，仓库通过 [media.json](media.json) 引用，不提交媒体二进制文件。

| 模块 | 已有结果 | 边界 |
| --- | --- | --- |
| [动作库](video/actions/README.md) | 八姿态挥剑预览 | 有循环重置，不是连续人体动画 |
| [有限动画](video/limited/README.md) | 《雨夜送药》150 秒；落脚约束对照 | 素材复用与二维动作，复杂环境接触有限 |
| [整场景叙事](video/scene/README.md) | 《垃圾車來了！》160 秒 | 76 张姿态停留和切接，不等于连续动作模型 |
| [花店试播](video/pilot/README.md) | 10 秒连续视频：走近、蹲下、伸手 | 可行性限于已观察动作；未触盆，NEEDS_REVIEW |

花店故事按 [六段情节](video/pilot/STORY.md) 考虑，接触、扶正、致意与离开逐段验证。故事板和静态状态图不作为真实影片证据。

## 按需运行

需要 Python 3.11+、FFmpeg/FFprobe、curl；重新合成旁白需要 Node.js 22+ 与网络。

```sh
python -m pip install -r video/requirements.txt
python tools/media.py fetch --prefix video/actions/
python video/actions/build_preview.py video/actions/sword-swing

python tools/media.py fetch --prefix video/limited/assets/
python video/limited/benchmark.py
python video/limited/measure.py --evidence video/limited/output
```

原图从 ishare 的 original 地址下载并核对 SHA-256，取回的素材与生成输出均被 Git 忽略。视频链接用于观看；可用 --videos 取回流媒体交付副本，但它经过转码，不能冒充原始下载文件或用于原文件哈希证明。旧成片的审查结论与原始哈希保留在各模块。

语音依赖 [wangwangit/tts](https://github.com/wangwangit/tts) 的固定 MIT 版本已完整纳入 [third_party/tts](third_party/tts/UPSTREAM.json)，无需运行时克隆。旁白音档和混音不再提交；重建整场景作品须按模块说明重新合成旁白，在线服务可用性与输出字节不保证重现。PDoomVideo 是研究参考，没有被当成运行依赖或复制其歌曲。

代码采用 [MIT](LICENSE)，素材与第三方说明见 [来源](video/ASSETS.md) 和 [归属](video/THIRD_PARTY.md)。文章：[动画工作流复盘](https://js.gripe/zh-SG/2026/10/ai-animation-workflow-retrospective/)。
