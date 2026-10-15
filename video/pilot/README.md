# 雨夜花店：连续视频可行性

第一轮真实下载片段为 10 秒、720p、24 fps，240 帧完整解码。用户报告由 gemini.google.com 的“Gemini 4”生成；底层视频模型版本及实际参考附件绑定未验证。

可见结果是走近、停步、下蹲和伸手。人物停得过远，直到末帧仍没有触及陶盆盆沿。结论为 **NEEDS_REVIEW**：连续画面组织已有有限可行性，完整接触动作未通过。详见 [审查报告](REVIEW.md)、[逐项结果](review.json) 和 [六段故事](STORY.md)。

图片与视频地址、原始哈希统一保存于根目录 `media.json` 的 `video/pilot/` 条目。六格图是故事参考；9 秒证据图和原片接触表才来自真实视频。原片通过 ishare 以流媒体播放，经过转码；报告的原始文件哈希并非流媒体交付哈希。

运行质检前按需取回三张参考原图：

```sh
python tools/media.py fetch --prefix video/pilot/references/
python video/pilot/qa_media.py --video /path/to/original-download.mp4 --contract video/pilot/shot_contract.json --out .cache/pilot-review
```

随后看接触表与接触前后的全分辨率帧，填写 PASS、FAIL 或 UNVERIFIED。图片本地哈希匹配不等于请求确实绑定过该图。视频生成由用户网页操作，本仓库不含付费 API 自动调用。

没有可观察的触盆完成点时，剪辑脚本会拒绝导出。第二轮继续使用锁定母图，按 `prompt-trial-02.txt` 修正停步位置；本轮末帧未升级为已批准参考。
