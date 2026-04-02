---
name: ai-content-studio
description: |
  AI Content Studio — 专业级 AI 音频内容创作工具。
  Use this skill whenever working in or with the ai-content-studio project:
  generating podcasts/TTS audio, running the orchestrator, fixing TTS bugs,
  extending engines, adding new voices, configuring role libraries, running
  tests, or reading the project's architecture. Make sure to invoke this skill
  for any task involving MiniMax T2A V2, Qwen TTS, Qwen Omni, voice synthesis,
  role configuration, or the audio studio workflow — even if the user doesn't
  explicitly name the project.
  触发词：播客生成、TTS 音频合成、多角色对话、语音合成、辩论播客

# OpenClaw 元数据
metadata:
  openclaw:
    version: "1.0"
    requires:
      bins:
        - ffmpeg
      env:
        - DASHSCOPE_API_KEY
        - MINIMAX_API_KEY
    install:
      - kind: brew
        formula: ffmpeg
        description: "音频处理引擎（macOS）"
---

# AI Content Studio Skill

专业级 AI 音频内容创作工具。三引擎编排（MiniMax → Qwen TTS → Qwen Omni），通过 LLM 编排播客脚本 + 高保真语音合成，生成广播级立体声音频。

## 目录结构

```
ai-content-studio/               # Skill 源码仓库
├── SKILL.md                     # 本文件（主入口）
├── scripts/
│   ├── install.sh               # Skill 安装脚本
│   └── studio/                  # TTS 引擎源码
│       ├── studio_orchestrator.py   # 推荐入口，编排 + Fallback
│       ├── content_studio.py        # MiniMax LLM 脚本生成
│       ├── minimax_tts_tool.py      # MiniMax T2A V2 TTS
│       ├── qwen_tts_studio.py       # Qwen LLM 脚本生成
│       ├── qwen_tts_tool.py         # Qwen qwen3-tts-flash TTS
│       ├── qwen_omni_studio.py      # Qwen Omni 全模态单次调用
│       ├── qwen_omni_tts_tool.py    # Qwen qwen3-omni-flash TTS
│       ├── audio_utils.py           # 共享工具（FFmpeg 混音、正则解析、VoicePool）
│       ├── config_utils.py          # 统一配置加载（opencode.json）
│       └── paths.py                 # 路径配置模块
├── references/
│   └── configs/                 # 角色库配置文件
│       ├── studio_roles.json     # MiniMax 工作角色库（36 角色）
│       ├── roles.json            # MiniMax 轻量角色库
│       ├── minimax_voices.json   # MiniMax 音色参考文档
│       └── qwen_voices.json      # Qwen TTS 角色库
├── tests/                       # 测试脚本
└── assets/                      # 运行时产出
    ├── outputs/                 # 音频输出
    ├── work/                    # MiniMax 临时文件
    ├── work_qwen/               # Qwen Omni 临时文件
    └── work_tts/                # Qwen TTS 临时文件
```

**Fallback 链路**: `MiniMax → Qwen TTS → Qwen Omni`（全部失败才报错）

---

## 常用命令

### 一句话跑通
```bash
cd scripts/studio && python studio_orchestrator.py --source "源文本.txt" --stereo -o out.mp3
```

### 生成模式（`--mode`）
| 值 | 说明 | 输出格式 |
|----|------|---------|
| `deep_dive` | 广播级深度对谈，含认知冲突与突破 | `[Alex, curious]: ...` |
| `summary` | 专业简报，快速概要 | `[Narrator, neutral]: ...` |
| `review` | 建设性专家评论，含优缺点 | `[Expert, calm]: ...` |
| `debate` | 正反方辩论，主持人引导 | `[Proponent]: ... [Opponent]: ...` |

### 指定引擎
```bash
cd scripts/studio
python studio_orchestrator.py --source "文本" --engine minimax    # 仅 MiniMax
python studio_orchestrator.py --source "文本" --engine qwen_tts   # 仅 Qwen TTS（49音色）
python studio_orchestrator.py --source "文本" --engine qwen       # 仅 Qwen Omni
python studio_orchestrator.py --source "文本" --engine auto       # 自动 Fallback（默认）
```

### 引擎状态检查
```bash
cd scripts/studio && python studio_orchestrator.py --check
```

### 立体声 + 背景音乐
```bash
python studio_orchestrator.py --source "文本.txt" --stereo --bgm ambient.mp3 -o out.mp3
```

### 独立 TTS 工具（绕过 LLM，直接合成已有脚本）
```bash
cd scripts/studio

# MiniMax（多角色对话文件）
python minimax_tts_tool.py -s dialogue.txt -r ../../references/configs/studio_roles.json --stereo -o out.mp3

# Qwen TTS Studio
python qwen_tts_studio.py --source "文本.txt" -r ../../references/configs/qwen_voices.json -o out.mp3

# Qwen Omni（单文本）
python qwen_omni_tts_tool.py "待合成文本" -o output.wav -v cherry
```

### 运行测试
```bash
python tests/test_minimax_tts.py
python tests/test_qwen_omni_tts.py
```

---

## 对话脚本格式

文件格式（`[role, emotion]: text`）：
```txt
[Alex, curious]: 这项技术的核心原理是什么？
[Sam, skeptical]: 我认为这个方向还很不成熟。
[Alex, excited]: 但最新实验数据显示...
```

- `role` 必须在角色库（`references/configs/studio_roles.json` / `references/configs/qwen_voices.json`）中定义
- `emotion` 可选，默认 `neutral`；MiniMax 支持：`happy`, `calm`, `angry`, `sad`
- 角色切换自动插入 0.2s 停顿（`--pause` 可调）

---

## 配置文件速查

| 文件 | 引擎 | 用途 |
|------|------|------|
| `references/configs/studio_roles.json` | MiniMax | 推荐工作角色库（36 角色，6 大场景） |
| `references/configs/roles.json` | MiniMax | 轻量角色库（3 角色，快速测试） |
| `references/configs/minimax_voices.json` | MiniMax | 音色参考文档 + 参数指南（纯查阅） |
| `references/configs/qwen_voices.json` | Qwen TTS | Qwen 角色库（24 角色 + 29 音色轮询池） |

详见 `references/configs/README.md`。

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

## 关键代码模式

### 路径导入（scripts/studio/ 内部）
```python
from paths import REPO_ROOT, OUTPUTS_DIR, WORK_DIR, CONFIGS_DIR
```

### 共享工具（所有引擎通用）
```python
from audio_utils import (
    parse_dialogue_segments_from_text,  # 正则解析对话文本
    merge_audio_files,                     # FFmpeg 混音引擎
    compute_role_pan_values,               # 立体声声道分配
    VoicePool,                             # 音色轮询分配器
    split_text,                            # 智能文本切分
    stream_qwen_omni_events,               # SSE 流解析
    make_wav_header,                       # PCM WAV header 构造
)
```

### SHA256 缓存模式（TTS 片段缓存）
```python
import hashlib
def segment_cache_key(voice, text, params):
    h = hashlib.sha256()
    h.update(f"{voice}:{text}:{params}".encode())
    return h.hexdigest()[:16]
# 缓存文件命名：seg_<16位hash>.mp3
```

### MiniMax T2A V2 API 端点
- LLM: `/v1/messages`（Anthropic 兼容）
- TTS: `/v1/t2a_v2`

### Qwen API 端点
- Qwen TTS: `/api/v1/services/aigc/multimodal-generation/generation`
- Qwen Omni: `/chat/completions`（流式 SSE）

---

## 扩展项目

### 新增音色/角色
1. 在 `references/configs/studio_roles.json`（MiniMax）或 `references/configs/qwen_voices.json`（Qwen TTS）中添加条目
2. 角色名须与脚本中 `[role]` 标签完全匹配
3. 运行 `python studio_orchestrator.py --check` 验证

### 新增 TTS 引擎
1. 在 `studio_orchestrator.py` 中添加 `EnginePriority` 枚举值
2. 实现对应的 `run_<engine>_studio()` 函数
3. 在 `check_engines()` 中添加可用性检测
4. 在 `EnginePriority.AUTO` 的 Fallback 链路中注册

---

## 故障排查

**Rich 标签错误**：`MarkupError` 通常来自 subprocess 传递的路径字符串中包含未转义的 `[]` 字符。确保 `[` 不被 rich 解析为标签。

**FFmpeg 不可用**：`ffmpeg` 和 `ffprobe` 是系统级依赖，必须安装：
```bash
brew install ffmpeg   # macOS
sudo apt install ffmpeg  # Linux
```

**TTS 返回错误码**：`1001`/`1013`/`1021` = 业务限流（tenacity 自动重试 3 次）；其他非零码触发 Fallback。

**Qwen Omni 生成多余文本**：Omni 是全模态模型，可能在音频之外附带文本元数据。后处理时需过滤非音频字段。

---

## 安装 Skill

```bash
bash scripts/install.sh        # 安装到 ~/.claude/skills/ai-content-studio/
bash scripts/install.sh --uninstall  # 卸载
```

详见 `INSTALL.md`。
