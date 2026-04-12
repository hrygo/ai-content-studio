# 配置文件速查

| 文件 | 引擎 | 用途 |
|------|------|------|
| `configs/studio_roles.json` | MiniMax | 推荐工作角色库（36 角色，6 大场景） |
| `configs/roles.json` | MiniMax | 轻量角色库（3 角色，快速测试） |
| `configs/minimax_voices.json` | MiniMax | 音色参考文档 + 参数指南（纯查阅） |
| `configs/qwen_voices.json` | Qwen TTS | Qwen 角色库（24 角色 + 29 音色轮询池） |

详见 `configs/README.md`。

---

## studio_roles.json — MiniMax 工作角色库（推荐）

**适用引擎**: `minimax` / `auto`

### 角色分组

| group | 说明 | 典型角色 |
|-------|------|---------|
| `podcast` | 播客对话（deep_dive / debate） | Alex, Sam, Jordan, Casey |
| `narration` | 专业播报（summary） | Narrator, NewsAnchor, DocumentaryHost |
| `educational` | 教育培训 | Professor, ScienceExplainer, MathTeacher |
| `childrens` | 儿童内容 | Storyteller, FriendlyMonster, WiseGrandpa |
| `english` | 英文国际内容 | EnglishNarrator, BritishHost, AussieGuide |
| `special` | 特殊音效（高级参数演示） | GhostVoice, RadioVoice, DeepOracle |

### 核心参数

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

> **参数优先级**: `segment 台词级` > `role 角色库` > `global 命令行默认值`

---

## roles.json — MiniMax 轻量角色库

包含 3 个基础角色的极简配置，适合快速测试和简单双人对话场景：

```json
{
    "主持人": { "voice_id": "male-qn-qingse", "speed": 1.0, "emotion": "neutral" },
    "乐观派": { "voice_id": "male-qn-qingse", "speed": 1.2, "pitch": 2,  "emotion": "happy" },
    "怀疑论者": { "voice_id": "male-qn-qingse", "speed": 0.9, "pitch": -2, "emotion": "calm" }
}
```

---

## minimax_voices.json — MiniMax 音色参考文档

**不参与引擎调用**，仅供查阅：
- `_voice_pools`: 各音色 ID 的风格描述
- `_model_guide`: 各 T2A V2 模型能力对比
- `_parameter_guide`: 所有参数取值范围
- `_sound_effects`: 可用音效列表（`spacious_echo` / `room_reverb` / `radio` 等）

---

## qwen_voices.json — Qwen TTS Studio 角色库

**适用引擎**: `qwen_tts`

| 字段 | 说明 |
|------|------|
| `roles` | 24 个预定义角色（人名 → 音色映射） |
| `role_defaults` | LLM 生成脚本中常见角色名 → 默认音色（兜底映射） |
| `voice_pool` | 29 个音色组成的轮询池（超出角色数时自动循环） |

### 使用方法

```bash
voiceforge dialogue --source "内容.txt" --engine qwen_tts -o out.mp3
voiceforge dialogue --source "内容.txt" --roles configs/qwen_voices.json -o out.mp3
```

> **自动音色分配**: LLM 生成的脚本中角色超出 `role_defaults` 范围时，会自动从 `voice_pool` 轮询分配。

---

## 自定义角色库

以 `configs/studio_roles.json` 为模板添加角色：

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

> `voice_id` 必须来自对应引擎支持的音色列表（参考 `configs/minimax_voices.json` 或 Qwen 官方文档）。高级参数（`english_normalization` / `latex_read` 等）仅 `speech-2.8-hd/turbo` 模型支持。
