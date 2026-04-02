# `configs/` — 配置文件说明

> 完整使用说明（含安装、场景、FAQ）请参阅 [`USER_MANUAL.md`](../USER_MANUAL.md)。

AI Content Studio 使用 JSON 配置文件控制多角色音频生成的音色、音质和行为。四个文件各司其职，分别对应不同的引擎和使用场景。

---

## 文件总览

| 文件 | 引擎 | 用途 |
|------|------|------|
| `studio_roles.json` | **MiniMax T2A V2** | 工作角色库（36个角色，演示全部高级参数） |
| `roles.json` | **MiniMax T2A V2** | 轻量角色库（3个角色，快速上手） |
| `minimax_voices.json` | MiniMax T2A V2 | 音色参考文档 + 参数指南（纯查阅） |
| `qwen_voices.json` | **Qwen TTS** | Qwen TTS Studio 角色库（24个角色，49种音色） |

---

## `studio_roles.json` — MiniMax 工作角色库（推荐使用）

**适用引擎**: `minimax` / `auto`

完整的角色库，覆盖播客、播报、教育、儿童、英文、辩论六大场景，演示 T2A V2 所有高级参数。

### 角色分组

| group | 说明 | 典型角色 |
|-------|------|---------|
| `podcast` | 播客对话（deep_dive / debate） | Alex, Sam, Jordan, Casey |
| `narration` | 专业播报（summary） | Narrator, NewsAnchor, DocumentaryHost |
| `educational` | 教育培训 | Professor, ScienceExplainer, MathTeacher |
| `childrens` | 儿童内容 | Storyteller, FriendlyMonster, WiseGrandpa |
| `english` | 英文国际内容 | EnglishNarrator, BritishHost, AussieGuide |
| `special` | 特殊音效（高级参数演示） | GhostVoice, RadioVoice, DeepOracle |

### 核心参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `voice_id` | MiniMax 音色 ID | `"male-qn-qingse"`, `"female-yujie"` |
| `speed` | 语速倍率（0.5–2.0） | `0.9`（偏慢） / `1.2`（偏快） |
| `pitch` | 音调偏移（半音程，-12–12） | `-3`（低沉） / `5`（高亢） |
| `emotion` | 情感（需 speech-2.8-hd/turbo） | `"happy"`, `"calm"`, `"angry"`, `"sad"` |

### 高级参数（仅 speech-2.8-hd/turbo）

| 参数 | 说明 | 使用场景 |
|------|------|---------|
| `english_normalization` | 英文数字规范化 | 财经/学术内容含英文数字时设为 `true` |
| `latex_read` | LaTeX 公式朗读（需用 `$$` 包裹） | 数学/物理教程 |
| `language_boost` | 语种优先识别 | `"Chinese"` / `"English"` / `"Japanese"` |
| `pronunciation_dict` | 自定义读音词典 | 技术播客中的专业术语读法 |
| `voice_modify` | 声音修饰（pitch/intensity/timbre/sound_effects） | 幽灵音、电台音效等特殊效果 |

### 使用方法

```bash
# 指定角色库
python studio_orchestrator.py --source "内容.txt" --roles configs/studio_roles.json --stereo

# MiniMax 引擎独立使用
python minimax_tts_tool.py -s dialogue.txt -r configs/studio_roles.json --stereo -o out.mp3
```

> **参数优先级**: `segment 台词级` > `role 角色库` > `global 命令行默认值`
>
> 角色名需与脚本中 `[role]` 标签完全匹配，例如 `[Alex, happy]:` 对应 `"Alex": {...}`

---

## `roles.json` — MiniMax 轻量角色库（快速上手）

**适用引擎**: `minimax` / `auto`

包含 3 个基础角色的极简配置，适合快速测试和简单双人对话场景。

```json
{
    "主持人": { "voice_id": "male-qn-qingse", "speed": 1.0, "emotion": "neutral" },
    "乐观派": { "voice_id": "male-qn-qingse", "speed": 1.2, "pitch": 2,  "emotion": "happy" },
    "怀疑论者": { "voice_id": "male-qn-qingse", "speed": 0.9, "pitch": -2, "emotion": "calm" }
}
```

```bash
python studio_orchestrator.py --source "内容.txt" --roles configs/roles.json
```

---

## `minimax_voices.json` — MiniMax 音色参考文档（纯查阅）

**适用引擎**: MiniMax T2A V2（参考文档）

此文件**不参与引擎调用**，仅供查阅 MiniMax 支持的音色和参数：

- **`_voice_pools`**: 各音色 ID 的风格描述（中文男声/女声/英文声）
- **`_model_guide`**: 各 T2A V2 模型的能力对比（speech-2.8-hd / turbo / 2.6 / 02 / 01）
- **`_parameter_guide`**: 所有参数的取值范围和说明
- **`_sound_effects`**: 可用的音效列表（`spacious_echo` / `room_reverb` / `radio` 等）

完整音色列表建议调用 MiniMax 音色查询 API 获取，以 API 返回为准。

---

## `qwen_voices.json` — Qwen TTS Studio 角色库

**适用引擎**: `qwen_tts`（通过 `qwen_tts_studio.py` 使用）

qwen3-tts-flash 专属角色库，49 种音色覆盖中文、方言和英文场景。

### 结构

| 字段 | 说明 |
|------|------|
| `roles` | 24 个预定义角色（人名 → 音色映射 + 语言/速度描述） |
| `role_defaults` | LLM 生成脚本中常见角色名 → 默认音色（兜底映射） |
| `voice_pool` | 29 个音色组成的轮询池（超出角色数时自动循环） |

### 角色示例

```json
"Aurora": { "voice": "aurora", "language": "中文", "speed": 1.0, "description": "年轻女性，清亮活泼" },
"Terry":  { "voice": "terry",  "language": "中文", "speed": 1.0, "description": "中年男性，磁性低沉" },
"Dylan":  { "voice": "dylan",  "language": "北京话", "speed": 1.0, "description": "北京话男性，地道方言" },
"Sunny":  { "voice": "sunny",  "language": "四川话", "speed": 1.0, "description": "四川话，诙谐幽默" }
```

### 使用方法

```bash
python studio_orchestrator.py --source "内容.txt" --engine qwen_tts -o out.mp3

# 独立使用 Qwen TTS Studio
python qwen_tts_studio.py --source "内容.txt" -r configs/qwen_voices.json -o out.mp3
```

> **自动音色分配**: LLM 生成的脚本中角色超出 `role_defaults` 范围时，会自动从 `voice_pool` 轮询分配，无需手动指定每个角色。

---

## 引擎选择建议

| 场景 | 推荐引擎 | 推荐角色库 |
|------|---------|-----------|
| 高保真专业播客，情感丰富 | `minimax` | `studio_roles.json` |
| 快速测试，最小配置 | `minimax` | `roles.json` |
| 49 种音色，方言/多语言 | `qwen_tts` | `qwen_voices.json` |
| 全自动兜底（MiniMax 优先） | `auto` | `studio_roles.json` |
| 短文本单音色合成 | `qwen`（Omni） | 无需角色库 |

---

## 自定义角色库

以 `studio_roles.json` 为模板，添加/修改角色：

```json
{
    "我的主播": {
        "voice_id": "female-yujie",
        "speed": 1.05,
        "pitch": 2,
        "emotion": "happy",
        "group": "podcast",
        "description": "我的自定义主播音色",
        "language_boost": "Chinese"
    }
}
```

> **注意**: `voice_id` 必须来自对应引擎支持的音色列表（参考 `minimax_voices.json` 或 Qwen 官方文档）。高级参数（`english_normalization` / `latex_read` 等）仅 `speech-2.8-hd/turbo` 模型支持。
