---
name: ai-content-studio
description: |
  AI Content Studio — 专业级 AI 音频内容创作工具。
  **立即激活本 skill**，当用户请求以下任何操作时：
  - 把文字做成播客音频 / 对话节目 / 专家访谈
  - 生成 TTS 语音 / 文本转语音 / 文字转音频
  - 多角色对话脚本 + 语音合成
  - 辩论节目 / 新闻播报 / 摘要播客
  - 上传文章/报告生成语音播客
  - 批量文本转语音
  触发词：播客、TTS、语音合成、文本转音频、文字转语音、对话音频、辩论节目、语音播客、Podcast、多角色语音、AI播客、批量语音
compatibility:
  tools:
    - ffmpeg
  env:
    - MINIMAX_API_KEY + MINIMAX_GROUP_ID
    - QWEN_API_KEY (或 DASHSCOPE_API_KEY)
---

# AI Content Studio

专业级 AI 音频内容创作工具。基于 Clean Architecture（三引擎编排），支持单文本 TTS、多角色对话脚本、AI 播客全流程生成。

**架构层次**：
- `entities/` — 核心数据实体（TTSRequest、AudioSegment、EngineResult）
- `use_cases/` — 业务用例（合成、对话、播客、批量）
- `adapters/` — 引擎适配器（MiniMax / Qwen TTS / Qwen Omni / LLM）
- `infrastructure/` — CLI、依赖注入容器、配置管理

---

## 快速开始

安装后即可使用 `ai-studio` CLI：

```bash
# 安装 skill
bash scripts/install.sh

# 一句话跑通（AI 播客）
ai-studio studio --topic "人工智能的未来" -o podcast.mp3

# 对话脚本 TTS
ai-studio dialogue --source dialogue.txt -o dialogue.mp3

# 单文本 TTS
ai-studio synthesize --source "你好世界" -o hello.mp3

# 批量合成
ai-studio batch --segments "你好|cherry,世界|ethan" -o batch.mp3
```

---

## 命令参考

### ai-studio synthesize

单文本 TTS 合成（绕过 LLM，直接合成已有文本）。

```bash
ai-studio synthesize --source "待合成文本" -o output.mp3 [OPTIONS]

OPTIONS:
  --engine {minimax|qwen_tts|qwen_omni|qwen}  引擎，默认 minimax
  --voice VOICE_ID                                   音色 ID
  --speed 0.5-2.0                                   语速，默认 1.0
  --emotion {neutral|happy|sad|angry|calm|surprised|fearful|disgusted|fluent}
  --format {mp3|wav}                                 默认 mp3
```

**示例**：
```bash
# MiniMax 指定音色
ai-studio synthesize --source "欢迎收听本期节目" --voice female-tianmei --speed 1.2 -o intro.mp3

# Qwen Omni
ai-studio synthesize --source "这是一段测试音频" --engine qwen_omni --voice cherry -o test.mp3
```

### ai-studio dialogue

对话脚本解析 + 多角色 TTS 合成。自动分配立体声声道（不同角色左右分离）。

```bash
ai-studio dialogue --source DIALOGUE.txt -o output.mp3 [OPTIONS]

OPTIONS:
  --source FILE                   对话脚本文件（支持文件路径或直接文本）
  --engine {minimax|qwen_tts|...} TTS 引擎
  --roles ROLES.json              角色音色映射（可选）
  --bgm MUSIC.mp3                  背景音乐（可选）
```

**对话脚本格式**：
```
[Speaker]: 文本内容
[Speaker, emotion]: 带情感标记的文本
```

支持同行多角色（无换行分隔）：
```
[Alex]: 你好[Sam]: 你好 Alex
```

- `Speaker` — 角色名，自动映射到音色
- `emotion` — 可选，MiniMax 支持情感参数

**示例**：
```bash
# 自动音色分配（轮询 cherry/ethan/chelsie）
ai-studio dialogue --source podcast.txt -o podcast.mp3

# 自定义角色音色
ai-studio dialogue --source podcast.txt --roles roles.json -o podcast.mp3

# 加背景音乐
ai-studio dialogue --source podcast.txt --bgm ambient.mp3 -o podcast_bgm.mp3
```

**roles.json 示例**：
```json
{
  "Alex": {"voice": "cherry", "speed": 1.1},
  "Sam": {"voice": "ethan", "speed": 0.95}
}
```

### ai-studio studio

LLM 生成播客脚本 → TTS 合成 → FFmpeg 混音，全自动一条龙。

```bash
ai-studio studio --topic "播客主题" -o output.mp3 [OPTIONS]

OPTIONS:
  --llm {minimax|qwen}           LLM 引擎（生成脚本），默认 minimax
  --tts {minimax|qwen_tts|...}  TTS 引擎（合成语音），默认 minimax
  --roles ROLES.json             角色音色映射
  --bgm MUSIC.mp3                背景音乐
```

**示例**：
```bash
# 最常用：MiniMax 全套
ai-studio studio --topic "人工智能的未来" -o ai_podcast.mp3

# Qwen LLM + MiniMax TTS
ai-studio studio --topic "量子计算原理" --llm qwen --tts minimax -o quantum.mp3

# 加背景音乐
ai-studio studio --topic "产品发布会" --bgm ambient.mp3 -o launch.mp3
```

### ai-studio batch

批量文本片段 TTS + FFmpeg 自动合并为单一音频文件。

```bash
ai-studio batch --segments "文本1|音色1,文本2|音色2,..." -o output.mp3 [OPTIONS]

OPTIONS:
  --engine {minimax|qwen_tts|...}  TTS 引擎
```

片段之间自动插入 0.5s 静音间隔。

**示例**：
```bash
ai-studio batch \
  --segments "开头语|cherry,主要内容|ethan,结束语|chelsie" \
  -o episode.mp3
```

---

## API 配置

**优先级**：环境变量 > `~/.config/opencode/opencode.json`（向后兼容）

```bash
# MiniMax（需要同时设置两个）
export MINIMAX_API_KEY="..."
export MINIMAX_GROUP_ID="..."

# Qwen / DashScope（二选一）
export QWEN_API_KEY="..."
export DASHSCOPE_API_KEY="..."        # 等效，别名

# 可选：自定义 Base URL
export DASHSCOPE_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
```

`opencode.json` 结构：
```json
{
  "provider": {
    "minimax": {"options": {"apiKey": "...", "groupId": "..."}},
    "bailian": {"options": {"apiKey": "...", "baseURL": "..."}}
  }
}
```

---

## 故障排查

| 问题 | 解决方案 |
|------|---------|
| `ffmpeg: command not found` | `brew install ffmpeg`（macOS）或 `sudo apt install ffmpeg`（Linux）|
| `ContainerInitializationError` | 检查 API Key 环境变量是否设置 |
| TTS 返回 1001/1013/1023 | 业务限流，tenacity 自动重试 3 次 |
| Qwen Omni 输出含多余文本 | Omni 全模态模型附带非音频元数据，已自动过滤 |
| 脚本解析失败 | 确保格式为 `[Speaker]: 文本`，方括号要紧邻冒号 |
| `ModuleNotFoundError: src.xxx` | 重新安装：`pip install -e .` |

---

## 安装与维护

```bash
# 安装 / 更新
bash scripts/install.sh

# 卸载
bash scripts/install.sh --uninstall

# 运行测试
python -m pytest tests/ -q
```

安装后 `ai-studio` 命令全局可用。Python 包安装路径：`pip show ai-content-studio`
