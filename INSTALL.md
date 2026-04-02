# AI Content Studio Skill 安装指南

本目录为 **ai-content-studio** skill 的源码仓库。`SKILL.md` 定义了 skill 的全部内容，包括架构说明、命令索引、代码模式和故障排查指南。

---

## 安装方式一：install.sh 脚本（推荐）

```bash
# 安装
./install_skill.sh

# 卸载
./install_skill.sh --uninstall

# 重装（重新运行 install.sh 即可，自动备份旧版本）
```

安装后重启 Claude Code 会话，新 agent 进入 `ai-content-studio` 项目目录时会自动激活此 skill。

---

## 安装方式二：手动复制

skill 源码仓库位置：`SKILL.md` 所在目录

目标安装路径：`~/.claude/skills/ai-content-studio/`

```bash
# 克隆/进入 ai-content-studio 目录后：
cp SKILL.md ~/.claude/skills/ai-content-studio/SKILL.md
```

---

## 安装方式三：git clone 到 skills 目录

如果希望直接用 git 管理 skill 版本，可将 skill 仓库 clone 到 skills 目录：

```bash
git clone <your-skill-repo-url> ~/.claude/skills/ai-content-studio
```

---

## 验证安装

重启 Claude Code 会话后，在 `ai-content-studio` 项目目录执行：

```
/skill:ai-content-studio
```

或直接发起任务，agent 应能识别并激活此 skill。

---

## Skill 内容概览

| 模块 | 内容 |
|------|------|
| **架构总览** | 三引擎链路图（MiniMax → Qwen TTS → Qwen Omni） |
| **常用命令** | orchestrator / 独立 TTS 工具 / 测试命令 |
| **对话脚本格式** | `[role, emotion]: text` 格式说明 |
| **配置文件速查** | 4 个 JSON 角色库对照表 |
| **API 配置** | opencode.json 读取逻辑 + 环境变量覆盖 |
| **关键代码模式** | audio_utils 共享工具、SHA256 缓存、API 端点 |
| **扩展项目** | 新增音色/角色/引擎的步骤指引 |
| **故障排查** | Rich 标签错误、FFmpeg 依赖、错误码处理 |
| **文件索引** | 所有核心文件用途速查表 |

---

## 依赖前提

skill 本身零依赖，但 ai-content-studio 项目运行时需要：

```bash
pip install -r requirements.txt
brew install ffmpeg   # macOS
# sudo apt install ffmpeg  # Linux
```

详见 [`README.md`](./README.md)。
