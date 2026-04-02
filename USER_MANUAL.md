# AI Content Studio 用户手册

## 目录

1. [这是什么工具](#1-这是什么工具)
2. [安装与配置](#2-安装与配置)
3. [快速开始](#3-快速开始)
4. [四大使用场景](#4-四大使用场景)
5. [进阶定制](#5-进阶定制)
6. [常见问题](#6-常见问题)

---

## 1. 这是什么工具

AI Content Studio 可以把**文字内容**变成**专业播客音频**。

你输入一篇文章、一段新闻或一份报告，它会自动生成一段像广播节目一样的对话音频——有多个角色、有讨论、有节奏感，就像两个人在聊天。

**它能做什么**

| 场景 | 说明 | 效果 |
|------|------|------|
| 深度播客 | 自动生成两人或多人对话，模拟真实讨论 | 适合公众号、播客节目 |
| 专业摘要 | 将长文压缩为一段清晰播报 | 适合新闻简报、周报 |
| 产品评论 | 模拟专家评价，含优点也有缺点 | 适合评测、产品介绍 |
| 辩论节目 | 正反方对辩，有主持人引导 | 适合话题讨论、观点碰撞 |

**输出是什么样的**

```
[Alex, curious]: 今天我们聊聊最新的 AI 技术突破。
[Sam, skeptical]: 我觉得这里面有泡沫，得冷静看。
[Alex, excited]: 但数据不会骗人，GPT-5 的测试结果...
[Sam, calm]: 先别急，我们来看具体场景...
```

---

## 2. 安装与配置

### 系统要求

- Python 3.9+
- macOS / Linux（Windows 通过 WSL 也可运行）
- FFmpeg（音频处理工具）

### 第一步：安装 Python 依赖

```bash
cd ai-content-studio
pip install -r requirements.txt
```

### 第二步：安装 FFmpeg

**macOS**
```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian)**
```bash
sudo apt install ffmpeg
```

### 第三步：配置 API Key

AI Content Studio 需要两个 AI 服务账号（都是国内服务，支付宝/阿里云账号即可开通）：

#### MiniMax（主要引擎，推荐开通）

1. 访问 [MiniMax 开放平台](https://platform.minimax.io)
2. 注册账号并充值（播客生成成本很低，10 元够用很久）
3. 在控制台获取 API Key

#### 阿里云百炼 Qwen（备用引擎）

1. 访问 [阿里云百炼](https://bailian.console.aliyun.com)
2. 开通 DashScope 服务（新用户有免费额度）
3. 获取 API Key

#### 配置方式（二选一）

**方式 A：环境变量（推荐）**

```bash
export MINIMAX_API_KEY="your-minimax-key"
export DASHSCOPE_API_KEY="your-dashscope-key"
```

**方式 B：配置文件**

工具自动从 `~/.config/opencode/opencode.json` 读取，配置格式如下：

```json
{
  "provider": {
    "bailian": {
      "options": { "apiKey": "your-dashscope-key" }
    },
    "minimax": {
      "options": { "apiKey": "your-minimax-key" }
    }
  }
}
```

### 验证配置

```bash
python studio_orchestrator.py --check
```

看到类似输出即为配置成功：
```
引擎状态:
  MiniMax Studio:     ✅ 已配置
  Qwen TTS Studio:    ✅ 已配置
  Qwen Omni Studio:   ✅ 已配置
```

---

## 3. 快速开始

### 最简命令

```bash
python studio_orchestrator.py --source "你的内容.txt" -o my_podcast.mp3
```

工具会自动：
1. 读取你的文本内容
2. 生成多人对话脚本
3. 选择最合适的音色进行合成
4. 输出 MP3 文件

### 命令结构解析

```bash
python studio_orchestrator.py \
  --source "源文本.txt"      \   # 要转换的内容（必填）
  --mode deep_dive          \   # 生成模式（默认 deep_dive）
  -o output.mp3             \   # 输出文件名
  --stereo                  \   # 开启立体声（可选）
  --bgm music.mp3           \   # 添加背景音乐（可选）
  --roles configs/studio_roles.json  # 指定角色音色（可选）
```

### 支持的输入格式

**方式一：文本文件**
```bash
--source "文章.txt"
```

**方式二：直接输入文本**
```bash
--source "今天发布了一款新产品..."
```

> 注意：内容越长，生成时间越长。建议单次不超过 5000 字。超长内容建议分段处理。

---

## 4. 四大使用场景

### 场景 A：深度播客（最常用）

适合将长文章转化为有深度讨论感的音频节目。

```bash
python studio_orchestrator.py \
  --source "技术文章.txt" \
  --mode deep_dive \
  --stereo \
  --bgm ambient.mp3 \
  -o "深度播客.mp3"
```

**效果**：两个角色围绕主题展开讨论，有提问、有反驳、有总结，模拟真实播客节奏。

**可选背景音乐**：准备一个 MP3 文件作为背景音乐。工具会在人声出现时自动降低背景音量（称为 Ducking），不会喧宾夺主。

---

### 场景 B：快速摘要

适合将报告、新闻、公告快速转化为可听的简报。

```bash
python studio_orchestrator.py \
  --source "周报.txt" \
  --mode summary \
  -o "周报摘要.mp3"
```

**效果**：单一专业主播音色，语速适中，清晰播报核心内容。类似新闻广播风格。

**适用内容**：新闻、公告、周报、财报、政策解读。

---

### 场景 C：产品评论

模拟专家视角，对产品/事件进行评价，有赞有弹。

```bash
python studio_orchestrator.py \
  --source "产品评测.txt" \
  --mode review \
  --stereo \
  -o "产品评论.mp3"
```

**效果**：专家角色会分析优点和不足，观点平衡，适合帮助听众全面了解事物。

---

### 场景 D：辩论节目

适合将争议性话题做成正反方对辩节目。

```bash
python studio_orchestrator.py \
  --source "AI是否会取代人类工作.txt" \
  --mode debate \
  --stereo \
  -o "辩论节目.mp3"
```

**效果**：正方和反方各自陈述观点，主持人引导节奏，最终给出综合结论。模拟辩论赛结构。

---

## 5. 进阶定制

### 定制角色音色

默认情况下，工具会自动选择音色。如果你想控制每个角色的声音，可以通过角色库文件定制。

#### MiniMax 音色一览

| 音色 ID | 风格 | 适合场景 |
|--------|------|---------|
| `male-qn-qingse` | 青年男性，清亮活泼 | 主播、提问者 |
| `male-qn-K` | 中年男性，沉稳磁性 | 专家、总结者 |
| `female-yujie` | 青年女性，专业知性 | 分析者、反驳者 |
| `female-tianmei` | 青年女性，甜美柔和 | 补充观点、轻松话题 |
| `female-tianmei_v2` | 青年女性，柔和细腻 | 旁白、叙述 |

> 完整音色列表建议在 MiniMax 控制台查看，以官方返回为准。

#### Qwen TTS 特色音色（方言/英文）

| 音色 ID | 语言 | 说明 |
|--------|------|------|
| `dylan` | 北京话 | 地道的北京腔 |
| `jada` | 上海话 | 软糯吴语风格 |
| `sunny` | 四川话 | 诙谐幽默 |
| `aurora` / `emma` | 英文 | 自然英文发音 |

#### 创建自定义角色库

在 `configs/` 目录下创建新的 JSON 文件，例如 `my_roles.json`：

```json
{
    "主播小王": {
        "voice_id": "male-qn-qingse",
        "speed": 1.1,
        "pitch": 2,
        "emotion": "happy"
    },
    "专家老李": {
        "voice_id": "male-qn-K",
        "speed": 0.9,
        "pitch": -2,
        "emotion": "calm"
    }
}
```

使用自定义角色库：

```bash
python studio_orchestrator.py \
  --source "内容.txt" \
  --roles my_roles.json \
  -o "定制播客.mp3"
```

**注意**：角色名需要与脚本中的标签匹配。脚本会生成类似 `[主播小王, happy]:` 的标签，确保 JSON 中的键名一致。

---

### 定制语速和情感

在角色库中为每个角色设置：

```json
{
    "Alex": {
        "voice_id": "male-qn-qingse",
        "speed": 1.2,          # 语速：1.0=标准，>1.0=快，<1.0=慢
        "pitch": 3,             # 音调：正数=高亢，负数=低沉
        "emotion": "happy"      # 情感：happy/sad/angry/calm/fearful/surprised
    }
}
```

---

### 高级参数

#### 英文数字规范化

如果内容包含英文数字（如 `API v2.0`、`GDP 5%`），建议开启：

```json
{
    "播音员": {
        "voice_id": "female-yujie",
        "english_normalization": true
    }
}
```

#### LaTeX 公式朗读

如果内容包含数学公式（需用 `$$` 包裹）：

```json
{
    "数学老师": {
        "voice_id": "male-qn-qingse",
        "latex_read": true
    }
}
```

#### 语种优先

内容为中英混杂时，指定优先语言：

```json
{
    "技术主播": {
        "voice_id": "female-yujie",
        "language_boost": "Chinese"    # 或 "English"
    }
}
```

#### 特殊音效

| 音效 | 效果 | 场景 |
|------|------|------|
| `spacious_echo` | 空旷回声 | 幽灵、神秘旁白 |
| `room_reverb` | 房间混响 | 纪录片 |
| `radio` | 电台效果 | 复古风格 |

```json
{
    "旁白": {
        "voice_id": "female-tianmei_v2",
        "voice_modify": {
            "sound_effects": "spacious_echo"
        }
    }
}
```

---

### 直接合成对话脚本

如果你已经有写好的对话内容，可以跳过 LLM 脚本生成，直接合成音频。

创建对话文件 `dialogue.txt`：

```
[Alex, curious]: 今天聊一个很有争议的话题。
[Sam, skeptical]: 先别下结论，我们看看数据。
[Alex, excited]: 数据很有意思，你看这里...
```

运行合成：

```bash
python minimax_tts_tool.py \
  -s dialogue.txt \
  -r configs/studio_roles.json \
  --stereo \
  -o "对话音频.mp3"
```

---

## 6. 常见问题

### Q：生成的声音像真人吗？

**A**：MiniMax T2A V2 的效果已经非常接近真人播音员，情感丰富、音色自然。Qwen TTS 性价比高，音色各有特色。建议先用短文本测试，选择最喜欢的音色。

### Q：如何提高合成质量？

1. **内容本身要结构清晰**：段落分明、逻辑连贯的内容生成效果更好
2. **使用 `deep_dive` 模式**：对话形式比纯叙述更有表现力
3. **开启立体声**：不同角色在左右声道，空间感更强
4. **添加背景音乐**：选择轻柔的纯音乐，效果提升明显

### Q：API 额度用完了怎么办？

**A**：系统会自动 Fallback。如果 MiniMax 额度耗尽，会自动切换到 Qwen TTS；如果 Qwen 也不可用，最后尝试 Qwen Omni。也可以手动指定引擎：

```bash
# 强制使用 Qwen（最便宜，有免费额度）
python studio_orchestrator.py --source "内容.txt" --engine qwen
```

### Q：生成时间很长怎么办？

**A**：
- 短文本（1000字以内）：通常 1-3 分钟
- 长文本（5000字）：可能需要 5-10 分钟
- 可以分段处理：将长文拆成 2-3 段，分别生成后用音频编辑软件拼接

### Q：背景音乐从哪里找？

**A**：
- Pixabay Music（免费）：https://pixabay.com/music/
- Free Music Archive：https://freemusicarchive.org/
- 选择轻柔的纯音乐、Ambient、Piano 类，避免人声干扰

### Q：声音太小/太大？

**A**：工具内置响度归一化（`loudnorm`），会自动调整到标准响度。如仍需调整，可使用音频编辑工具（如 Audacity、GarageBand）进行后处理。

### Q：能生成视频吗？

**A**：目前仅支持音频生成。如需视频，可将 MP3 导入剪映、CapCut 等工具，自动对口型生成视频。

### Q：内容是中文还是英文？

**A**：自动跟随输入文本语言。输入中文生成中文播客，输入英文生成英文播客，中英混杂时根据内容自动判断。

---

## 快速命令速查

```bash
# 深度播客（推荐）
python studio_orchestrator.py --source "内容.txt" --stereo -o out.mp3

# 快速摘要
python studio_orchestrator.py --source "内容.txt" --mode summary -o summary.mp3

# 辩论节目
python studio_orchestrator.py --source "内容.txt" --mode debate --stereo -o debate.mp3

# 加背景音乐
python studio_orchestrator.py --source "内容.txt" --bgm music.mp3 -o with_bgm.mp3

# 自定义角色
python studio_orchestrator.py --source "内容.txt" --roles my_roles.json -o custom.mp3

# 检查状态
python studio_orchestrator.py --check
```
