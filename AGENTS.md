# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

AI Content Studio — 专业级 AI 音频内容创作工具。通过大语言模型编排播客脚本，结合高保真语音合成，生成具备真实对话感的广播级音频。

核心策略：**MiniMax 优先**，失败自动切换 **Qwen Omni** 作为兜底方案。

---

## 开发常用命令

### 安装依赖
```bash
pip install -r requirements.txt
# 必须：FFmpeg
brew install ffmpeg        # macOS
sudo apt install ffmpeg    # Linux
```

### 运行完整流程
```bash
# 自动模式（MiniMax 优先，失败自动切 Qwen）
python studio_run.py --source "内容.txt" --stereo

# 强制指定引擎
python studio_run.py --source "内容.txt" --engine minimax
python studio_run.py --source "内容.txt" --engine qwen

# 检查引擎可用性
python studio_orchestrator.py --check
```

### TTS 工具独立调用
```bash
# MiniMax TTS（多角色对话）
python minimax_tts_tool.py -s dialogue.txt -r configs/studio_roles.json --stereo -o out.mp3

# Qwen Omni TTS
python qwen_omni_tts_tool.py "待合成文本" -o output.wav -v cherry
```

### 运行测试
```bash
python tests/test_minimax_tts.py
```

---

## 架构设计

### 双引擎编排架构

```
studio_orchestrator.py          ← 推荐入口
│
├── content_studio.py            MiniMax LLM 脚本生成
│   └── minimax_tts_tool.py     MiniMax TTS 合成
│
└── qwen_omni_studio.py         Qwen Omni Fallback（全模态单次调用）
    └── qwen_omni_tts_tool.py   Qwen Omni TTS 工具（可独立使用）
```

**Fallback 策略**：`engine_priority="auto"` 时，先尝试 MiniMax 全流程（LLM → TTS），失败则自动切换 Qwen Omni 单次调用完成脚本 + 音频。

### 两种引擎的核心差异

|          | MiniMax Studio                                     | Qwen Omni Studio                |
| -------- | -------------------------------------------------- | ------------------------------- |
| 流程     | 两步：LLM 生成脚本 → TTS 合成                      | 单次调用同时完成脚本 + 音频     |
| 缓存     | LLM 响应（内存 TTL 5min）+ TTS 分片（文件 SHA256） | TTS 分片（文件 SHA256）         |
| 音频格式 | MP3 32kHz                                          | WAV 24kHz（最终转 MP3 128kbps） |
| 立体声   | 通过 FFmpeg pan/adelay 实现声道空间分配            | 同左                            |
| 背景音乐 | acompressor 动态压缩                               | 同左                            |

**Qwen Omni 音色（qwen3-omni-flash，当前账户）**：`cherry`（默认）、`ethan`、`chelsie`
完整列表（qwen3.5-omni / qwen-omni-turbo 等其他版本）见[阿里云百炼官方文档](https://help.aliyun.com/zh/model-studio/omni-voice-list)。注意：音色可用性由账户等级决定，官方文档的音色列表仅供参考，实际以 API 响应为准。

### 脚本生成模式（两引擎通用）
- `deep_dive`：广播级深度对谈，含认知冲突与突破
- `summary`：单人播报，专业简报
- `review`：专家评论，含优缺点分析
- `debate`：正反方辩论

### 对话脚本格式
```
[角色名, 情感]: 文本内容
[Alex, curious]: 这项技术很有意思...
[Sam, skeptical]: 但我认为方向不对。
```

### API Key 配置优先级
1. 环境变量（`MINIMAX_API_KEY` / `DASHSCOPE_API_KEY`）
2. 配置文件 `~/.config/opencode/opencode.json`（结构：`provider.minimax.options.apiKey` / `provider.bailian.options.apiKey`）

---

## 关键实现细节

### TTS 分片缓存机制
- `minimax_tts_tool.py`：分片缓存用 SHA256 哈希命名存储于 `work/` 目录，基于 `text + voice_id + speed + vol + pitch + emotion` 生成键
- `qwen_omni_tts_tool.py`：缓存存储于 `work_qwen/` 目录
- `content_studio.py`：LLM 响应缓存在内存（`TTLCache`，100 条/5分钟 TTL）

### 混音引擎（FFmpeg filter_complex）
两个 TTS 工具共用相同的混音逻辑：声道空间处理（`pan`）→ 并行时序编排（`adelay`）→ 动态压缩（`acompressor`）→ 响度限制（`alimiter` + `loudnorm`）→ BGM Ducking（`sidechaincompress`）

### Qwen Omni 必须使用 `stream=True`
`qwen3-omni-flash` 模型只有在 `stream=True` 时才会在 SSE 流中返回音频数据（`delta.audio.data`），裸 PCM 数据需要手动构造 WAV header（`make_wav_header` 函数，16-bit PCM 24kHz 单声道）

### MiniMax T2A V2 错误码处理
常见业务错误码：`1001`/`1013`/`1021`（限流）→ tenacity 自动重试；其他非零码返回 `None` 触发 fallback

---

## 文件结构

```
.
├── studio_run.py              Thin wrapper，向后兼容入口
├── studio_orchestrator.py     推荐入口，统一编排 + 引擎检测
├── content_studio.py          MiniMax LLM 脚本生成（V5.1）
├── minimax_tts_tool.py        MiniMax TTS 引擎（T2A V2 Pro V5.0）
├── qwen_omni_studio.py        Qwen Omni 全流程 Fallback
├── qwen_omni_tts_tool.py      Qwen Omni TTS 独立工具
├── configs/
│   ├── studio_roles.json      角色库（角色名 → 音色/语速/情感）
│   └── roles.json             旧版角色配置
└── tests/
    ├── test_minimax_tts.py    MiniMax 集成测试（依赖真实 API）
    └── test_qwen_omni_tts.py Qwen Omni 集成测试（4 场景，覆盖基础合成/多角色/BGM 混音）
```
