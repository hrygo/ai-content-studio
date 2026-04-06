---
name: ai-content-studio
description: |
  AI Content Studio — 专业级 AI 音频内容创作工具（v1.2.0）。
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
version: 1.2.0
last_updated: 2026-04-06
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

### MiniMax 配置

```bash
# 必需：API Key
export MINIMAX_API_KEY="your-minimax-api-key"

# 可选：Group ID（不设置时使用默认值 "default"）
export MINIMAX_GROUP_ID="your-group-id"
```

> **注意**：
> - `MINIMAX_GROUP_ID` 现在支持默认值，不设置时自动使用 "default"
> - 某些 Anthropic 兼容代理可能不需要 Group ID

### Qwen / DashScope 配置

```bash
# 方式 1: 使用 QWEN_API_KEY
export QWEN_API_KEY="your-qwen-api-key"

# 方式 2: 使用 DASHSCOPE_API_KEY（等效，推荐）
export DASHSCOPE_API_KEY="your-dashscope-api-key"

# 可选：自定义 Base URL
export DASHSCOPE_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
```

> **重要**：
> - **DASHSCOPE_API_KEY** 现已完全支持（TTS 侧和 LLM 侧均支持 fallback）
> - Qwen TTS 使用 OpenAI 兼容接口（`/chat/completions`），而非 `/audio/speech` 端点
> - Qwen Omni 必须使用流式 API（stream=True），已自动处理

### 从 opencode.json 读取（向后兼容）

`opencode.json` 结构：
```json
{
  "provider": {
    "minimax": {
      "options": {
        "apiKey": "your-minimax-api-key",
        "groupId": "your-group-id"
      }
    },
    "bailian": {
      "options": {
        "apiKey": "your-dashscope-api-key",
        "baseURL": "https://dashscope.aliyuncs.com/compatible-mode/v1"
      }
    }
  }
}
```

### 配置验证

```bash
# 验证环境变量
echo $MINIMAX_API_KEY
echo $DASHSCOPE_API_KEY

# 测试 API 连接
python3 -c "
import os
from src.services.api_client import MiniMaxClient
client = MiniMaxClient(api_key=os.getenv('MINIMAX_API_KEY'))
result = client.text_to_speech('测试', voice_id='male-qn-qingse')
print('✓ MiniMax API 连接成功' if result else '✗ MiniMax API 连接失败')
"
```

---

## 故障排查

### 常见问题

| 问题 | 解决方案 |
|------|---------|
| `ffmpeg: command not found` | `brew install ffmpeg`（macOS）或 `sudo apt install ffmpeg`（Linux）|
| `ai-studio: command not found` | 运行 `pip install -e . --break-system-packages` 重新安装 CLI |
| `ModuleNotFoundError: src.xxx` | 重新安装：`pip install -e .` |
| `ContainerInitializationError` | 检查 API Key 环境变量是否设置 |
| TTS 返回 1001/1013/1021/2056 | **速率限制** - 已自动重试 5 次，指数退避（最大 60 秒）|
| 音色 ID 不可用 | 运行 `python3 scripts/test_voices.py` 测试音色，更新 roles.json |
| Qwen Omni 输出含多余文本 | Omni 全模态模型附带非音频元数据，已自动过滤 |
| 脚本解析失败 | 确保格式为 `[Speaker]: 文本`，方括号要紧邻冒号 |

### 速率限制处理

当遇到 2056 错误（usage limit exceeded）时：
- ✅ **自动重试**：最多 5 次
- ✅ **指数退避**：2秒 → 4秒 → 8秒 → 16秒 → 32秒（最大 60 秒）
- ✅ **详细日志**：显示重试次数和等待时间

### 音色测试

部分音色 ID 可能不可用，使用测试工具验证：

```bash
# 测试所有音色
python3 scripts/test_voices.py

# 输出示例：
# ✓ 可用音色: male-qn-qingse, female-yujie, presenter_male
# ✗ 不可用音色: male-qn-K, female-tianmei_v2
# 建议替换: male-qn-K → presenter_male
```

### 详细故障排查

查阅 **[完整故障排查指南](docs/TROUBLESHOOTING.md)** 了解：
- 安装问题（ffmpeg sudo 权限、apt update hook 报错）
- 运行时问题（CLI 未安装、API Key 缺失、端点 404）
- 性能优化建议
- 问题提交流程

---

## 性能优化建议

### 速率限制处理
- **自动重试**：遇到速率限制（1001/1013/1021/2056）时自动重试最多 5 次
- **指数退避**：每次重试等待时间翻倍（最大 60 秒）
- **建议**：批量合成时建议每段之间间隔 0.5-1 秒，避免触发速率限制

### 批量处理建议
- **并发控制**：批量合成时建议限制并发数（3-5 个并发）
- **内存优化**：大批量音频处理时建议分批进行，避免内存溢出
- **缓存策略**：重复文本可考虑缓存已合成的音频片段

---

## 参考文档

| 文档 | 用途 |
|------|------|
| `references/user_manual.md` | 面向终端用户的完整场景引导（安装、四大场景、FAQ） |
| `references/configs_guide.md` | 角色库配置详解（36+ 音色、自定义角色、高级参数） |
| `references/troubleshooting.md` | 故障排查（错误码、API 问题、FFmpeg） |
| `references/configs/` | 预置角色库 JSON 文件 |

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
