# 故障排查

## 引擎不可用

```bash
python studio_orchestrator.py --check
```

返回示例：
```
✓ MiniMax Studio: 可用
✓ Qwen TTS Studio: 可用
✗ Qwen Omni Studio: 未配置
```

## MiniMax 返回错误码

| 错误码 | 原因 | 处理 |
|--------|------|------|
| `1001` / `1013` / `1021` | 业务限流 | tenacity 自动重试 3 次 |
| 其他非零码 | 接口异常 | 自动 Fallback 到 Qwen TTS → Qwen Omni |

## Rich 标签错误

`MarkupError: closing tag '[/yellow]' doesn't match any open tag`

**原因**：subprocess 传递的路径字符串中包含未转义的 `[]` 字符，被 rich 解析为标签。

**常见触发场景**：读取大文件（如 60MB+ source maps）时，文件内容被意外传入 Panel 显示。

**修复原则**：
- subprocess 调用时确保只传递文件路径，不传递文件内容
- Panel 显示中避免使用用户输入的原始文本

## FFmpeg 不可用

`ffmpeg` 和 `ffprobe` 是系统级依赖，必须安装：

```bash
brew install ffmpeg   # macOS
sudo apt install ffmpeg  # Linux
```

验证安装：
```bash
ffmpeg -version
ffprobe -version
```

## Qwen Omni 生成多余文本

Qwen Omni 是全模态模型，可能在音频之外附带文本元数据。后处理时需过滤非音频字段。

**如仍有文本泄漏**：用 `--engine minimax` 强制使用 MiniMax。

## TTS 片段缓存未命中

缓存命中条件：`voice_id + text + speed + pitch + emotion` 全部一致。

如果合成的音色/速度与预期不符，检查：
1. 角色库中该角色的 `voice_id` 是否正确
2. 是否在命令行覆盖了角色库参数（如 `--speed`）
3. 情感参数是否在角色库中指定（`emotion` 需 `speech-2.8-hd/turbo` 模型支持）

## 立体声文件中角色偏左/偏右

`compute_role_pan_values()` 等间距分配声道值，单角色居中，多角色均匀分布于 [-0.8, +0.8]。

如需手动调整：修改 `minimax_tts_tool.py` 中的 `pan_map` 或在角色库中指定。

## API Key 未生效

优先级（高到低）：
1. 环境变量（`DASHSCOPE_API_KEY`、`MINIMAX_API_KEY` 等）
2. `~/.config/opencode/opencode.json` 中的 `apiKey` 字段
3. 代码中的默认值

检查 Key 是否有效：
```bash
# MiniMax
echo $MINIMAX_API_KEY | cut -c1-6  # 应输出 "sk-cp-"

# Qwen
echo $DASHSCOPE_API_KEY | cut -c1-6
```
