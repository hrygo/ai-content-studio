# AI Content Studio Skill 安装指南

> **适用对象**：Claude Code、OpenCode、OpenClaw 等 AI Agent
> **安装目标**：将 skill 安装到通用 agent skills 目录，使 Agent 在 `ai-content-studio` 项目工作时自动激活

---

## 安装路径说明

本 skill 遵循 **Agent Skills 通用最佳实践**：

| 路径类型 | 路径 | 用途 |
|---------|------|------|
| **主安装路径** | `~/.agents/skills/ai-content-studio/` | 通用标准路径，所有兼容 Agent 从此读取 |
| **Claude Code 兼容** | `~/.claude/skills/ai-content-studio` → `~/.agents/skills/ai-content-studio` | 符号链接，确保 Claude Code 可访问 |

**为什么这样设计？**
- `~/.agents/skills/` 是 AI Agent 技能的通用标准目录
- Claude Code 使用 `~/.claude/skills/` 作为其专用目录
- 通过符号链接实现一次安装、多 Agent 兼容

---

## 快速安装

### 步骤 1：定位 Skill 源目录

```bash
# 当前目录即为 skill 源码仓库
SKILL_SOURCE="$(pwd)"  # 或显式指定：/path/to/ai-content-studio
```

### 步骤 2：运行安装脚本

```bash
cd "$SKILL_SOURCE"
bash scripts/install.sh
```

安装脚本自动执行：
1. 复制完整 bundle 到 `~/.agents/skills/ai-content-studio/`
2. 创建符号链接 `~/.claude/skills/ai-content-studio` → `~/.agents/skills/ai-content-studio`
3. 如已存在旧安装，自动备份到 `~/.agents/skills/ai-content-studio.backup_<timestamp>/`

### 步骤 3：验证安装

```bash
# 检查主安装
ls -la ~/.agents/skills/ai-content-studio/SKILL.md

# 检查符号链接
ls -la ~/.claude/skills/ai-content-studio

# 预期：显示符号链接指向 ~/.agents/skills/ai-content-studio
```

---

## 卸载 Skill

```bash
cd <skill-source-directory>
bash scripts/install.sh --uninstall
```

卸载会：
1. 删除符号链接 `~/.claude/skills/ai-content-studio`
2. 删除主安装 `~/.agents/skills/ai-content-studio/`

---

## 手动安装（备选）

如果安装脚本不可用，Agent 可直接执行：

```bash
SKILL_SOURCE="$(pwd)"  # skill 源码仓库路径
SKILL_DEST="$HOME/.agents/skills/ai-content-studio"
CLAUDE_LINK="$HOME/.claude/skills/ai-content-studio"

# 创建目标目录
mkdir -p "$(dirname "$SKILL_DEST")"
mkdir -p "$(dirname "$CLAUDE_LINK")"

# 复制核心文件
cp -r "$SKILL_SOURCE/SKILL.md" "$SKILL_DEST/"
cp -r "$SKILL_SOURCE/scripts/" "$SKILL_DEST/"
cp -r "$SKILL_SOURCE/references/" "$SKILL_DEST/"
cp -r "$SKILL_SOURCE/tests/" "$SKILL_DEST/"

# 创建符号链接（Claude Code 兼容）
ln -sf "$SKILL_DEST" "$CLAUDE_LINK"
```

---

## Git Clone 方式（版本管理）

如果 skill 已托管到 Git 仓库：

```bash
# 备份旧安装
if [[ -d ~/.agents/skills/ai-content-studio ]]; then
    mv ~/.agents/skills/ai-content-studio ~/.agents/skills/ai-content-studio.backup_$(date +%Y%m%d_%H%M%S)
fi

# 删除旧符号链接
if [[ -L ~/.claude/skills/ai-content-studio ]]; then
    rm ~/.claude/skills/ai-content-studio
fi

# Clone 新技能
git clone <skill-repo-url> ~/.agents/skills/ai-content-studio

# 创建符号链接
ln -sf ~/.agents/skills/ai-content-studio ~/.claude/skills/ai-content-studio
```

---

## 安装后验证

### 1. 文件结构检查

```bash
tree -L 2 ~/.agents/skills/ai-content-studio/
# 应包含：SKILL.md, scripts/, references/, tests/

# 验证符号链接
readlink ~/.claude/skills/ai-content-studio
# 应输出：<home-path>/.agents/skills/ai-content-studio
```

### 2. Skill 激活测试

在 `ai-content-studio` 项目目录发起任务：

```
生成一段产品公告的 TTS 音频
```

Agent 应能：
- 自动识别 `ai-content-studio` skill
- 引用 `SKILL.md` 中的命令和架构说明
- 正确执行 TTS 合成任务

---

## 故障排查

| 问题 | 解决方案 |
|------|----------|
| Skill 未激活 | 确认当前工作目录为 `ai-content-studio` 项目根目录 |
| 符号链接失效 | 重新运行 `bash scripts/install.sh` 修复链接 |
| 脚本执行失败 | 检查执行权限：`chmod +x scripts/install.sh` |
| 备份冲突 | 手动删除 `~/.agents/skills/ai-content-studio.backup_*` 后重试 |
| 安装后仍无效 | 重启 Claude Code 会话，确保 skill 元数据重新加载 |

---

## 依赖检查

Skill 安装完成后，确保项目运行时依赖已就绪：

```bash
# Python 依赖
pip install -r requirements.txt

# FFmpeg（音频处理必需）
brew install ffmpeg   # macOS
sudo apt install ffmpeg  # Linux

# 环境变量（可选，从 ~/.config/opencode/opencode.json 自动读取）
export DASHSCOPE_API_KEY="..."
export MINIMAX_API_KEY="..."
```

---

## 文件结构说明

安装后的 skill 目录结构：

```
~/.agents/skills/ai-content-studio/
├── SKILL.md                 # Skill 主入口
├── scripts/
│   ├── install.sh           # 安装脚本
│   └── studio/              # TTS 引擎源码
│       ├── paths.py         # 路径配置
│       ├── studio_orchestrator.py
│       ├── minimax_tts_tool.py
│       ├── qwen_tts_tool.py
│       └── ...
├── references/
│   └── configs/             # 角色库配置
└── tests/                   # 测试脚本

~/.claude/skills/ai-content-studio → ~/.agents/skills/ai-content-studio
```

---

## 更新 Skill

如果 skill 源码有更新，重新运行安装脚本：

```bash
cd <skill-source-directory>
bash scripts/install.sh  # 自动备份旧版本
```
