# AI Content Studio 使用手册

AI Content Studio 是一款专业级 AI 音频内容创作工具。通过大语言模型编排播客脚本，结合高保真语音合成，生成具备真实对话感的广播级音频。当 MiniMax 引擎不可用时，自动切换到 Qwen Omni 全模态引擎作为兜底方案。

---

## 一、架构概览

```
AI Content Studio Orchestrator
│
├── MiniMax Studio（优先引擎）
│   ├── content_studio.py      ← LLM 脚本生成
│   └── minimax_tts_tool.py   ← TTS 语音合成
│
└── Qwen Omni Studio（Fallback）
    └── qwen_omni_studio.py   ← 单次调用完成脚本 + 音频
```

**Fallback 策略**：自动检测 → MiniMax 优先 → 失败自动切换 Qwen Omni

---

## 二、快速上手

### 极简调用

```bash
# 自动模式（MiniMax 优先，失败自动切 Qwen）
python tts/studio_run.py --source "内容文档.txt" --stereo

# 强制使用 Qwen Omni 全流程
python tts/studio_orchestrator.py --source "内容文档.txt" --engine qwen

# 查看引擎状态
python tts/studio_orchestrator.py --check
```

---

## 三、引擎与 Fallback

### 引擎说明

| 引擎 | 能力 | 适用场景 |
|------|------|---------|
| **MiniMax Studio** | LLM 脚本生成 + 专业 TTS | 深度对话、高保真、立体声、背景音乐 |
| **Qwen Omni Studio** | 全模态单次调用 | 快速合成、额度受限时的兜底方案 |

### 强制指定引擎

```bash
# 仅 MiniMax（不 fallback）
python tts/studio_run.py --source "文本" --engine minimax

# 仅 Qwen Omni（不 fallback）
python tts/studio_run.py --source "文本" --engine qwen

# 自动（默认）- MiniMax 优先，失败自动切 Qwen
python tts/studio_run.py --source "文本" --engine auto
```

---

## 四、生成模式

| 模式 | 说明 | 输出格式 |
|------|------|---------|
| `deep_dive` | 广播级深度对谈，含认知冲突、突破、总结 | [Alex, curious]: ... [Sam, skeptical]: ... |
| `summary` | 专业简报，快速概要 | [Narrator, neutral]: ... |
| `review` | 建设性专家评论 | [Expert, calm]: ... |
| `debate` | 辩论，正反方对辩 | [Proponent, neutral]: ... [Opponent, neutral]: ... |

### 示例

```bash
# 深度播客（默认）
python tts/studio_run.py --source "文章.txt" --mode deep_dive -o out.mp3

# 快速摘要
python tts/studio_run.py --source "研报.txt" --mode summary -o summary.mp3

# 辩论模式
python tts/studio_run.py --source "产品.txt" --mode debate --stereo -o debate.mp3
```

---

## 五、TTS 工具独立调用

如需直接合成文本（不经过 LLM 脚本生成），可单独使用各 TTS 引擎：

### MiniMax TTS

```bash
# 单文本合成
python tts/minimax_tts_tool.py "待合成文本" -o output.mp3 -v male-qn-qingse -e happy

# 多角色对话
python tts/minimax_tts_tool.py -s dialogue.txt -r configs/roles.json -o multi_voice.mp3 --stereo
```

**音色参数** (`-v`): `male-qn-qingse`, `female-qn-qingse`, `male-qn-jingying` 等

### Qwen Omni TTS

```bash
# 单文本合成
python tts/qwen_omni_tts_tool.py "待合成文本" -o output.wav -v cherry

# 多角色对话
python tts/qwen_omni_tts_tool.py -s dialogue.txt -r configs/roles.json -o multi_voice.mp3 --stereo
```

**可用音色**:

| 引擎 | 可用音色 |
|------|---------|
| **qwen3-omni-flash**（当前账户） | `cherry`（默认）、`ethan`、`chelsie` |
| **qwen3.5-omni**（完整列表） | 女声：Tina（默认）、Cindy、Liora、Mira、Serena、Maia、Momo、Angel、Mia、Katerina、Jennifer、Mione、Sunny、Qiao、Sohee、Anna、Sonrisa、Roya、Hana、Griet、Eliška、Marina、Siiri、Ingrid、Sigga、Bea、Chloe |
| | 男声：Raymond、Ethan、Theo、Harvey、Evan、Wil、Li、Cassian、Joyner、Gold、Ryan、Aiden、Dylan、Eric、Peter、Joseph、Marcus、Rocky、Lenn、Bodega、Emilien、Andre、Radio Gol、Alek、Rizky、Arda、Dolce、Jakub |

> Qwen Omni 音色列表完整版见[阿里云百炼官方文档](https://help.aliyun.com/zh/model-studio/omni-voice-list)

---

## 六、配置文件

### API Key 配置

系统从 `~/.config/opencode/opencode.json` 自动读取配置，也可通过环境变量覆盖：

```bash
# MiniMax
export MINIMAX_TTS_API_KEY="your-key"
export MINIMAX_API_KEY="your-key"

# Qwen Omni (DashScope)
export DASHSCOPE_API_KEY="your-key"
export DASHSCOPE_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
```

### 角色库配置

创建 `configs/studio_roles.json`：

```json
{
  "Alex": {
    "voice_id": "female-qn-qingse",
    "emotion": "curious",
    "speed": 1.1,
    "personality": "技术极客，善于提问"
  },
  "Sam": {
    "voice_id": "male-qn-qingse",
    "emotion": "skeptical",
    "speed": 0.95,
    "personality": "资深专家，严谨务实"
  }
}
```

---

## 七、音频输出与混音

### 立体声

`--stereo` 开启后，不同角色分配到不同声道（偏左/偏右），增强空间感：

```bash
python tts/studio_run.py --source "文章.txt" --stereo -o stereo.mp3
```

### 背景音乐

`--bgm` 指定背景音乐文件，合成时自动执行 Ducking（人声说话时音乐压低）：

```bash
python tts/studio_run.py --source "文章.txt" --bgm music.mp3 -o with_bgm.mp3
```

### 输出格式

所有最终输出均为 **MP3 128kbps**，采样率跟随源引擎（MiniMax 32kHz / Qwen Omni 24kHz）。

---

## 八、文件结构

```
tts/
├── studio_orchestrator.py   # 统一编排器（推荐入口）
├── studio_run.py            # 向后兼容入口（thin wrapper）
│
├── content_studio.py         # MiniMax LLM 脚本生成
├── minimax_tts_tool.py      # MiniMax TTS 引擎
├── qwen_omni_tts_tool.py    # Qwen Omni TTS 引擎
├── qwen_omni_studio.py      # Qwen Omni 全流程 Fallback
│
├── configs/
│   └── studio_roles.json    # 角色库配置
├── outputs/                  # 产出目录
│   ├── final_studio_audio.mp3
│   └── generated_script.txt
└── work/                     # 临时文件（自动清理）
```

---

## 九、完整参数参考

### 编排器参数 (`studio_run.py` / `studio_orchestrator.py`)

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--source` | 源文本或文件路径 | **必须** |
| `--mode` | 生成模式 (`deep_dive`/`summary`/`review`/`debate`) | `deep_dive` |
| `-o`, `--output` | 输出文件路径 | `outputs/auto_<timestamp>.mp3` |
| `--engine` | 引擎优先级 (`auto`/`minimax`/`qwen`) | `auto` |
| `--stereo` | 开启立体声 | False |
| `--bgm` | 背景音乐文件路径 | - |
| `--instruction` | 额外要求（自然语言） | - |
| `-r`, `--roles` | 角色库配置文件路径 | `configs/studio_roles.json` |
| `--llm-url` | MiniMax LLM API 地址 | 官方 |
| `--tts-url` | MiniMax TTS API 地址 | 官方 |
| `-v`, `--voice` | Qwen Omni 音色 | `cherry` |
| `--check` | 仅检查引擎可用性 | - |

### MiniMax TTS 独立工具参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `text` | 待合成文本 | **必须** |
| `-o`, `--output` | 输出文件 | `output.mp3` |
| `-v`, `--voice` | 音色 ID | `male-qn-qingse` |
| `-e`, `--emotion` | 情感 | `neutral` |
| `-s`, `--source` | 对话脚本文件 | - |
| `-r`, `--roles` | 角色库配置 | - |
| `--stereo` | 开启立体声 | - |
| `--bgm` | 背景音乐 | - |
| `--pause` | 角色切换停顿（秒） | `0.2` |

### Qwen Omni TTS 独立工具参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `text` | 待合成文本 | **必须** |
| `-o`, `--output` | 输出文件 | `qwen_output.wav` |
| `-v`, `--voice` | 音色名 | `cherry` |
| `-m`, `--model` | 模型名 | `qwen3-omni-flash` |
| `-s`, `--source` | 对话脚本文件 | - |
| `-r`, `--roles` | 角色库配置 | - |
| `--stereo` | 开启立体声 | - |
| `--bgm` | 背景音乐 | - |

---

## 十、典型案例

### 案例 A：快速摘要

```bash
python tts/studio_run.py \
  --source "万字研报.txt" \
  --mode summary \
  -o "outputs/高层摘要.mp3"
```

### 案例 B：深度对谈（立体声 + 背景音乐）

```bash
python tts/studio_run.py \
  --source "技术文档.txt" \
  --mode deep_dive \
  --stereo \
  --bgm "assets/ambient.mp3" \
  -o "outputs/深度播客.mp3"
```

### 案例 C：强制 Qwen Omni 全流程

```bash
python tts/studio_run.py \
  --source "文章.txt" \
  --mode summary \
  --engine qwen \
  --voice ethan \
  -o "outputs/qwen_output.mp3"
```

### 案例 D：MiniMax TTS 独立使用（多角色）

```bash
# 创建对话脚本
cat > dialogue.txt << 'EOF'
[Alex, curious]: 这项技术的核心原理是什么？
[Sam, skeptical]: 老实说，我认为这个方向还很不成熟。
[Alex, excited]: 但最新的实验数据显示...
EOF

python tts/minimax_tts_tool.py \
  -s dialogue.txt \
  -r configs/roles.json \
  --stereo \
  -o "outputs/dialogue.mp3"
```

### 案例 E：Qwen Omni TTS 独立使用

```bash
python tts/qwen_omni_tts_tool.py \
  "今天天气真好，适合出门散步。" \
  -o "outputs/cherry_voice.mp3" \
  -v cherry
```

---

## 十一、依赖与安装

```bash
# 核心依赖
pip install requests tenacity rich cachetools

# FFmpeg（必须）
# macOS
brew install ffmpeg
# Linux
sudo apt install ffmpeg
```

---

## 十二、故障排查

### 引擎不可用

```bash
# 检查引擎状态
python tts/studio_orchestrator.py --check
```

### MiniMax 返回错误码

常见错误码：`2013`（额度耗尽）、`1001`（限流）。系统会自动 fallback 到 Qwen Omni。

### Qwen Omni 生成多余文本

已在 system prompt 中添加严格约束。如仍有问题，可通过 `--engine minimax` 强制使用 MiniMax。

---

*© 2026 AI Content Studio*
