# AI Content Studio

专业级 AI 音频内容创作工具。通过大语言模型编排播客脚本，结合高保真语音合成，生成具备真实对话感的广播级音频。

**核心策略**：MiniMax 优先 → Qwen TTS 兜底 → Qwen Omni 最终兜底，三引擎自动切换。

---

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
brew install ffmpeg        # macOS
# sudo apt install ffmpeg  # Linux
```

### 配置 API Key

从 `~/.config/opencode/opencode.json` 自动读取（`provider.bailian` → Qwen，`provider.minimax` → MiniMax），也支持环境变量覆盖：

```bash
export DASHSCOPE_API_KEY="your-dashscope-key"
export MINIMAX_API_KEY="your-minimax-key"
```

### 一句话跑通

```bash
# 自动模式：MiniMax 优先，失败自动 Fallback
python studio_orchestrator.py --source "源文本.txt" --stereo -o out.mp3
```

---

## 引擎说明

| 引擎 | 模型 | 能力 | 适用场景 |
|------|------|------|---------|
| **MiniMax** | T2A V2 Pro | LLM 脚本生成 + 情感 TTS + 立体声 + BGM | 深度播客、高保真专业音频 |
| **Qwen TTS** | qwen3-tts-flash | LLM 脚本生成 + 49 种音色 | 方言/多语言、高性价比（0.001元/字符） |
| **Qwen Omni** | qwen3-omni-flash | 单次调用完成脚本 + 音频 | 短文本快速合成兜底 |

### Fallback 链路

```
Auto 模式：
  MiniMax → Qwen TTS → Qwen Omni
          ↓全部失败
      返回错误
```

```bash
# 指定引擎（跳过 Fallback）
python studio_orchestrator.py --source "文本" --engine minimax
python studio_orchestrator.py --source "文本" --engine qwen_tts
python studio_orchestrator.py --source "文本" --engine qwen

# 查看引擎可用性
python studio_orchestrator.py --check
```

---

## 生成模式

| 模式 | 说明 | 输出格式 |
|------|------|---------|
| `deep_dive` | 广播级深度对谈，含认知冲突与突破 | `[Alex, curious]: ...` |
| `summary` | 专业简报，快速概要 | `[Narrator, neutral]: ...` |
| `review` | 建设性专家评论，含优缺点 | `[Expert, calm]: ...` |
| `debate` | 正反方辩论，主持人引导 | `[Proponent]: ... [Opponent]: ...` |

```bash
# 默认 deep_dive 模式
python studio_orchestrator.py --source "文章.txt" -o podcast.mp3

# 快速摘要
python studio_orchestrator.py --source "研报.txt" --mode summary -o summary.mp3

# 辩论（立体声）
python studio_orchestrator.py --source "产品.txt" --mode debate --stereo -o debate.mp3
```

---

## 配置文件

详细使用说明见 [`USER_MANUAL.md`](USER_MANUAL.md)。

| 文件 | 引擎 | 用途 |
|------|------|------|
| `configs/studio_roles.json` | MiniMax | 推荐工作角色库（36 角色，覆盖 6 大场景） |
| `configs/roles.json` | MiniMax | 轻量角色库（3 角色，快速测试） |
| `configs/minimax_voices.json` | MiniMax | 音色参考文档 + 参数指南（纯查阅） |
| `configs/qwen_voices.json` | Qwen TTS | Qwen TTS Studio 角色库（24 角色 + 29 音色轮询池） |

详见 [`configs/README.md`](configs/README.md)。

```bash
# 指定角色库
python studio_orchestrator.py --source "文本.txt" --roles configs/studio_roles.json --stereo
```

---

## 音频输出

### 立体声

`--stereo` 将不同角色分配到左右声道（-0.8 ~ +0.8 等距分布），增强空间感：

```bash
python studio_orchestrator.py --source "文章.txt" --stereo -o stereo.mp3
```

### 背景音乐

`--bgm` 指定背景音乐，合成时自动执行动态 Ducking（人声出现时音乐自动压低）：

```bash
python studio_orchestrator.py --source "文章.txt" --bgm ambient.mp3 -o with_bgm.mp3
```

### 输出格式

最终输出均为 **MP3 128kbps**。

---

## TTS 工具独立调用

各引擎的 TTS 工具也可直接调用，绕过 LLM 脚本生成：

```bash
# MiniMax TTS（单文本）
python minimax_tts_tool.py "待合成文本" -o output.mp3 -v male-qn-qingse -e happy

# MiniMax TTS（多角色对话文件）
python minimax_tts_tool.py -s dialogue.txt -r configs/roles.json --stereo -o multi.mp3

# Qwen Omni TTS（单文本）
python qwen_omni_tts_tool.py "待合成文本" -o output.wav -v cherry

# Qwen TTS Studio（LLM 脚本 + TTS）
python qwen_tts_studio.py --source "文本.txt" -r configs/qwen_voices.json -o out.mp3
```

---

## 典型案例

```bash
# 案例 A：深度播客（MiniMax + 立体声 + 背景音乐）
python studio_orchestrator.py \
  --source "技术文档.txt" \
  --mode deep_dive \
  --roles configs/studio_roles.json \
  --stereo --bgm ambient.mp3 \
  -o "outputs/深度播客.mp3"

# 案例 B：Qwen TTS Studio（49 音色，高性价比）
python studio_orchestrator.py \
  --source "内容.txt" \
  --engine qwen_tts \
  --roles configs/qwen_voices.json \
  -o "outputs/qwen_tts.mp3"

# 案例 C：Qwen Omni 全流程（短文本兜底）
python studio_orchestrator.py \
  --source "短文本" \
  --engine qwen \
  --voice ethan \
  -o "outputs/qwen_omni.mp3"

# 案例 D：多角色对话 TXT（直接 TTS，跳过 LLM）
cat > dialogue.txt << 'EOF'
[Alex, curious]: 这项技术的核心原理是什么？
[Sam, skeptical]: 我认为这个方向还很不成熟。
[Alex, excited]: 但最新实验数据显示...
EOF
python minimax_tts_tool.py -s dialogue.txt -r configs/roles.json --stereo -o dialogue.mp3
```

---

## 完整参数参考

### 编排器 (`studio_orchestrator.py`)

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--source` | 源文本或文件路径 | **必填** |
| `--mode` | 生成模式 | `deep_dive` |
| `-o`, `--output` | 输出文件路径 | `outputs/auto_<ts>.mp3` |
| `--engine` | 引擎 (`auto`/`minimax`/`qwen`/`qwen_tts`) | `auto` |
| `--roles` | 角色库配置文件 | `configs/studio_roles.json` |
| `--stereo` | 开启立体声 | False |
| `--bgm` | 背景音乐文件 | - |
| `--instruction` | 额外要求（自然语言） | - |
| `--llm-model` | Qwen TTS 脚本生成模型 | `qwen-turbo` |
| `--check` | 仅检查引擎可用性 | - |

### MiniMax TTS 工具 (`minimax_tts_tool.py`)

| 参数 | 说明 |
|------|------|
| `text` | 待合成文本 |
| `-s`, `--source` | 对话脚本文件（`[role, emotion]: text` 格式） |
| `-r`, `--roles` | 角色库 JSON |
| `--stereo` | 立体声 |
| `--bgm` | 背景音乐 |
| `--pause` | 角色切换停顿（秒，默认 0.2） |
| `--english-normalization` | 英文数字规范化 |
| `--latex-read` | LaTeX 公式朗读（`$$` 包裹） |
| `--language-boost` | 语种增强：`Chinese` / `English` / `Japanese` 等 |
| `--voice-modify` | 音效：`'{"sound_effects":"spacious_echo"}'` |

---

## 文件结构

```
ai-content-studio/
├── README.md                    # 项目说明
├── USER_MANUAL.md               # 面向终端用户的使用指南
├── studio_orchestrator.py      # 推荐入口，三引擎编排 + Fallback
├── studio_run.py               # 向后兼容入口
│
├── content_studio.py            # MiniMax LLM 脚本生成
├── minimax_tts_tool.py         # MiniMax TTS 引擎（T2A V2 Pro）
│
├── qwen_tts_studio.py          # Qwen TTS Studio（qwen-turbo → qwen3-tts-flash）
├── qwen_tts_tool.py            # Qwen TTS 工具（qwen3-tts-flash，49 音色）
│
├── qwen_omni_studio.py         # Qwen Omni Fallback（全模态单次调用）
├── qwen_omni_tts_tool.py       # Qwen Omni TTS 工具
│
├── audio_utils.py              # 共享音频工具（FFmpeg / 切分 / 混音 / 解析）
├── config_utils.py             # 统一 API 配置加载
│
├── configs/
│   ├── README.md               # 配置文件详细说明
│   ├── studio_roles.json       # MiniMax 工作角色库（36 角色）
│   ├── roles.json              # MiniMax 轻量角色库
│   ├── minimax_voices.json     # MiniMax 音色参考文档
│   └── qwen_voices.json        # Qwen TTS 角色库（24 角色 + 29 音色）
│
├── outputs/                     # 产出目录（自动创建）
├── work/                        # 临时音频片段（自动清理）
├── work_qwen/                   # Qwen Omni 临时文件（自动清理）
├── work_tts/                    # Qwen TTS 临时文件（自动清理）
│
└── tests/
    ├── test_minimax_tts.py      # MiniMax 集成测试
    └── test_qwen_omni_tts.py    # Qwen Omni 集成测试（4 场景）
```

---

## 故障排查

**引擎不可用**

```bash
python studio_orchestrator.py --check
```

**MiniMax 返回错误码**

- `1001` / `1013` / `1021`：业务限流，tenacity 自动重试 3 次
- 其他非零码：自动 Fallback 到 Qwen TTS → Qwen Omni

**Qwen Omni 生成多余文本**

Qwen Omni 严格遵循 system prompt 约束。如仍有文本泄漏，用 `--engine minimax` 强制使用 MiniMax。

---

## 依赖

```
requests  tenacity  rich  cachetools
ffmpeg（系统级，必须安装）
```
