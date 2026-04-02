---
name: ai-content-studio
description: |
  AI Content Studio — 专业级 AI 音频内容创作工具。
  **立即激活本 skill**，当用户请求以下任何操作时：
  - 把文字内容做成播客音频 / 对话节目
  - 生成 TTS 语音 / 文本转语音 / 文字转音频
  - 多角色对话脚本 + 语音合成
  - 辩论节目 / 专家评论 / 新闻播报音频
  - 写播客脚本 / 对话脚本并合成语音
  - 上传文章/报告生成语音播客
  触发词：播客、TTS、语音合成、文本转音频、文字转语音、对话音频、辩论节目、语音播客、Podcast
compatibility:
  tools:
    - ffmpeg
  env:
    - DASHSCOPE_API_KEY
    - MINIMAX_API_KEY
---

# AI Content Studio

专业级 AI 音频内容创作工具。三引擎编排（MiniMax → Qwen TTS → Qwen Omni），通过 LLM 编排播客脚本 + 高保真语音合成，生成广播级立体声音频。

**Fallback 链路**: `MiniMax → Qwen TTS → Qwen Omni`（全部失败才报错）

---

## 场景触发 → 命令生成

用户请求内容转音频时，按以下流程快速定位正确命令：

### 第一步：判断场景

| 用户意图关键词 | 推荐模式 | 典型输出 |
|---------------|---------|---------|
| "播客/对话/聊聊/讨论" | `--mode deep_dive` | 两人深度对谈，含提问与反驳 |
| "摘要/播报/总结一下" | `--mode summary` | 单人专业简报，清晰简洁 |
| "评论/点评/优缺点" | `--mode review` | 含优缺点的专家评析 |
| "辩论/正反方/对辩" | `--mode debate` | 正反方对辩，主持人引导 |

> **默认**：用户未指定模式时，使用 `--mode deep_dive`

### 第二步：组装命令

```bash
# 标准命令（直接运行）
cd scripts/studio
python studio_orchestrator.py \
  --source "你的内容.txt" \
  --mode <选定的模式> \
  --stereo \       # 建议始终开启，不同角色左右声道分离
  -o output.mp3
```

### 第三步：按需增强

| 选项 | 何时使用 | 示例 |
|------|---------|------|
| `--bgm music.mp3` | 添加背景音乐 | 轻柔纯音乐，人声时自动压低音量 |
| `--engine <engine>` | 指定单一引擎 | `minimax`（推荐）/ `qwen_tts` / `qwen` |
| `--engine auto` | 自动 Fallback | 三个引擎依次尝试（默认行为） |
| `--roles <config>` | 自定义角色音色 | 参考 `references/configs_guide.md` |

---

## 命令速查

### 一句话跑通
```bash
cd scripts/studio && python studio_orchestrator.py --source "文本.txt" --stereo -o out.mp3
```

### 指定引擎
```bash
python studio_orchestrator.py --source "文本" --engine minimax   # MiniMax（推荐）
python studio_orchestrator.py --source "文本" --engine qwen_tts  # Qwen TTS（49音色）
python studio_orchestrator.py --source "文本" --engine qwen      # Qwen Omni（单文本）
python studio_orchestrator.py --source "文本" --engine auto       # 自动 Fallback
```

### 引擎状态检查
```bash
cd scripts/studio && python studio_orchestrator.py --check
```

### 背景音乐 + 立体声
```bash
python studio_orchestrator.py --source "文本.txt" --stereo --bgm ambient.mp3 -o out.mp3
```

### 独立 TTS（直接合成已有脚本，绕过 LLM）
```bash
# MiniMax
python minimax_tts_tool.py -s dialogue.txt -r ../../references/configs/studio_roles.json --stereo -o out.mp3

# Qwen TTS Studio
python qwen_tts_studio.py --source "文本.txt" -r ../../references/configs/qwen_voices.json -o out.mp3

# Qwen Omni
python qwen_omni_tts_tool.py "待合成文本" -o output.wav -v cherry
```

### 运行测试
```bash
python tests/test_minimax_tts.py
python tests/test_qwen_omni_tts.py
```

---

## 对话脚本格式

直接合成已有脚本时使用此格式（`[role, emotion]: text`）：

```txt
[Alex, curious]: 这项技术的核心原理是什么？
[Sam, skeptical]: 我认为这个方向还很不成熟。
[Alex, excited]: 但最新实验数据显示...
```

- `role` 必须在角色库（`references/configs/studio_roles.json` / `references/configs/qwen_voices.json`）中定义
- `emotion` 可选，默认 `neutral`；MiniMax 支持：`happy`, `calm`, `angry`, `sad`
- 角色切换自动插入 0.2s 停顿（`--pause` 可调）

---

## 典型命令示例

```bash
# 深度播客（最常用）
python studio_orchestrator.py \
  --source "文章.txt" \
  --mode deep_dive \
  --stereo \
  --bgm ambient.mp3 \
  -o "播客.mp3"

# 快速摘要
python studio_orchestrator.py \
  --source "报告.txt" \
  --mode summary \
  -o "摘要.mp3"

# 辩论节目
python studio_orchestrator.py \
  --source "争议话题.txt" \
  --mode debate \
  --stereo \
  -o "辩论.mp3"
```

---

## API 配置

从 `~/.config/opencode/opencode.json` 自动读取：
- `provider.bailian` → Qwen（DASHSCOPE_API_KEY + baseURL）
- `provider.minimax` → MiniMax（MINIMAX_API_KEY）

环境变量覆盖：
```bash
export DASHSCOPE_API_KEY="..."
export MINIMAX_API_KEY="..."
export MINIMAX_LLM_API_URL="..."   # MiniMax LLM API URL（可选）
export MINIMAX_TTS_API_URL="..."   # MiniMax TTS API URL（可选）
```

---

## 故障排查

| 问题 | 解决方案 |
|------|---------|
| `MarkupError` / Rich 标签错误 | 路径字符串中的 `[]` 未转义；确保 `[` 不被 rich 解析为标签 |
| `ffmpeg: command not found` | `brew install ffmpeg`（macOS）或 `sudo apt install ffmpeg`（Linux）|
| TTS 返回 `1001`/`1013`/`1021` | 业务限流，tenacity 自动重试 3 次，无需干预 |
| TTS 返回其他非零码 | 触发 Fallback 到下一个引擎 |
| Qwen Omni 生成多余文本 | Omni 全模态模型附带非音频元数据；后处理已自动过滤 |

详细故障排查：`references/troubleshooting.md`

---

## 参考文档

| 文档 | 用途 |
|------|------|
| `references/user_manual.md` | 面向终端用户的完整场景引导（四大场景详解、角色定制、FAQ） |
| `references/configs_guide.md` | 角色库配置详解（36+ 音色、自定义角色、高级参数） |
| `references/troubleshooting.md` | 故障排查（错误码、API 问题、FFmpeg） |
| `references/configs/` | 预置角色库 JSON 文件 |

---

## 安装 Skill

```bash
bash scripts/install.sh        # 安装到 ~/.claude/skills/ai-content-studio/
bash scripts/install.sh --uninstall  # 卸载
```

详见 `INSTALL.md`。
