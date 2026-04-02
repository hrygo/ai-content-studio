#!/usr/bin/env bash
#────────────────────────────────────────────────────────────────────────────
# ai-content-studio Skill 安装脚本
#────────────────────────────────────────────────────────────────────────────
# 功能：将 ai-content-studio skill 安装到多个 AI Agent 的 skills 目录
# 用法：bash scripts/install.sh [OPTIONS]
#
# OPTIONS:
#   --uninstall              卸载 skill
#   --agent <name>           安装到指定 Agent（默认: all）
#                            可选值: all, claude-code, opencode, openclaw
#   --help                   显示帮助
#
# 安装路径矩阵：
#   ~/.agents/skills/ai-content-studio/       主路径（通用标准，Codex/Cursor/Cline 原生支持）
#   ~/.claude/skills/ai-content-studio       Claude Code 兼容（符号链接）
#   ~/.config/opencode/skills/ai-content-studio  OpenCode 兼容（符号链接）
#   ~/.openclaw/skills/ai-content-studio     OpenClaw 兼容（符号链接）
#
# Skill Bundle 结构：
#   SKILL.md        ← 主入口（含 OpenClaw metadata）
#   scripts/        ← 安装脚本、TTS 引擎源码
#   references/     ← 参考文档（配置文件、故障排查）
#   tests/          ← 测试脚本
#────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SKILL_NAME="ai-content-studio"

#────────────────────────────────────────────────────────────────────────────
# 安装路径变量
#────────────────────────────────────────────────────────────────────────────
SKILL_DEST="${HOME}/.agents/skills/${SKILL_NAME}"                    # 主路径（通用标准）
LINK_CLAUDE="${HOME}/.claude/skills/${SKILL_NAME}"                   # Claude Code
LINK_OPENCODE="${HOME}/.config/opencode/skills/${SKILL_NAME}"        # OpenCode
LINK_OPENCLAW="${HOME}/.openclaw/skills/${SKILL_NAME}"               # OpenClaw

INSTALL_MARKER="${SKILL_DEST}/.installed_from_ai_content_studio_repo"

#────────────────────────────────────────────────────────────────────────────
# 参数解析
#────────────────────────────────────────────────────────────────────────────
UNINSTALL=false
TARGET_AGENT="all"

show_help() {
    cat << 'EOF'
ai-content-studio Skill 安装脚本

用法：bash scripts/install.sh [OPTIONS]

OPTIONS:
  --uninstall              卸载 skill（从所有 Agent）
  --agent <name>           安装到指定 Agent（默认: all）
                           可选值:
                             all          安装到所有支持的 Agent
                             claude-code  仅 Claude Code
                             opencode     仅 OpenCode
                             openclaw     仅 OpenClaw
  --help                   显示此帮助

安装路径：
  ~/.agents/skills/ai-content-studio/         主路径（通用标准）
  ~/.claude/skills/ai-content-studio          Claude Code 符号链接
  ~/.config/opencode/skills/ai-content-studio OpenCode 符号链接
  ~/.openclaw/skills/ai-content-studio        OpenClaw 符号链接

示例：
  bash scripts/install.sh                      # 安装到所有 Agent
  bash scripts/install.sh --agent claude-code # 仅安装到 Claude Code
  bash scripts/install.sh --uninstall          # 卸载所有 Agent 的安装
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --uninstall)
            UNINSTALL=true
            ;;
        --agent)
            TARGET_AGENT="$2"
            case "$TARGET_AGENT" in
                all|claude-code|opencode|openclaw) ;;
                *)
                    echo "✗ 错误：未知 Agent: ${TARGET_AGENT}"
                    echo "  可选值: all, claude-code, opencode, openclaw"
                    exit 1
                    ;;
            esac
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "✗ 错误：未知参数: $1"
            echo "  使用 --help 查看用法"
            exit 1
            ;;
    esac
    shift
done

#────────────────────────────────────────────────────────────────────────────
# 工具函数
#────────────────────────────────────────────────────────────────────────────

# 备份已有文件/目录
backup_existing() {
    local path="$1"
    local desc="${2:-已存在的路径}"

    if [[ -L "$path" ]]; then
        # 符号链接：备份链接本身
        local link_target
        link_target="$(readlink "$path")"
        echo "  ! 备份已有符号链接 ${path} → ${link_target}"
        mv "$path" "${path}.backup_$(date +%Y%m%d_%H%M%S)"
    elif [[ -d "$path" ]]; then
        # 实体目录（非符号链接）：可能是旧版安装，备份后替换
        echo "  ! 检测到旧安装（实体目录）：${path}"
        echo "    备份到：${path}.legacy_$(date +%Y%m%d_%H%M%S)"
        mv "$path" "${path}.legacy_$(date +%Y%m%d_%H%M%S)"
    elif [[ -f "$path" ]]; then
        # 普通文件：备份
        echo "  ! 备份已有文件：${path}"
        mv "$path" "${path}.backup_$(date +%Y%m%d_%H%M%S)"
    fi
}

# 创建符号链接（幂等：先备份已存在的）
create_link() {
    local link_path="$1"
    local target="$2"
    local desc="${3:-符号链接}"

    # 确保父目录存在
    mkdir -p "$(dirname "$link_path")"

    # 备份已存在的路径
    if [[ -e "$link_path" || -L "$link_path" ]]; then
        backup_existing "$link_path" "$desc"
    fi

    # 创建符号链接
    ln -sf "$target" "$link_path"
    echo "✓ ${desc}：${link_path} → ${target}"
}

#────────────────────────────────────────────────────────────────────────────
# 卸载
#────────────────────────────────────────────────────────────────────────────
uninstall_skill() {
    echo "→ 卸载 ai-content-studio skill..."
    echo ""

    local links_removed=0

    # 删除各 Agent 符号链接
    for link_path in "$LINK_CLAUDE" "$LINK_OPENCODE" "$LINK_OPENCLAW"; do
        if [[ -L "$link_path" ]]; then
            echo "  → 删除符号链接：${link_path}"
            rm "$link_path"
            ((links_removed++)) || true
        elif [[ -e "$link_path" ]]; then
            # 非符号链接的实体（可能是旧安装残留）
            echo "  ! 检测到实体路径（非符号链接）：${link_path}"
            echo "    移动到备份目录..."
            mv "$link_path" "${link_path}.legacy_$(date +%Y%m%d_%H%M%S)"
            ((links_removed++)) || true
        fi
    done

    # 删除主安装
    if [[ -d "$SKILL_DEST" ]]; then
        echo "  → 删除主安装：${SKILL_DEST}"
        rm -rf "$SKILL_DEST"
        echo "✓ 已卸载主安装"
    fi

    # 清理备份目录
    for backup_dir in "${HOME}/.agents/skills/${SKILL_NAME}.backup_"* "${HOME}/.agents/skills/${SKILL_NAME}.legacy_"*; do
        if [[ -d "$backup_dir" ]]; then
            echo "  ℹ 保留备份：${backup_dir}"
        fi
    done

    echo ""
    if [[ $links_removed -eq 0 && ! -d "$SKILL_DEST" ]]; then
        echo "✓ 未找到已安装的 skill"
    else
        echo "✓ 卸载完成"
    fi
}

#────────────────────────────────────────────────────────────────────────────
# 安装
#────────────────────────────────────────────────────────────────────────────
install_skill() {
    if [[ ! -f "${REPO_ROOT}/SKILL.md" ]]; then
        echo "✗ 错误：找不到 ${REPO_ROOT}/SKILL.md"
        echo "  请确保在 ai-content-studio 项目根目录运行此脚本。"
        exit 1
    fi

    echo "→ 安装 ai-content-studio skill..."
    echo "  源目录：${REPO_ROOT}/"
    echo "  目标 Agent：${TARGET_AGENT}"
    echo ""

    # 备份主安装（如果存在）
    if [[ -d "$SKILL_DEST" ]]; then
        local backup="${HOME}/.agents/skills/${SKILL_NAME}.backup_$(date +%Y%m%d_%H%M%S)"
        echo "  ! 已存在主安装，备份到：${backup}"
        mv "$SKILL_DEST" "$backup"
    fi

    # 创建主目录
    mkdir -p "$SKILL_DEST"

    # 复制 skill bundle
    echo "  → 复制 skill bundle..."
    cp "${REPO_ROOT}/SKILL.md" "${SKILL_DEST}/SKILL.md"

    for subdir in scripts references tests; do
        if [[ -d "${REPO_ROOT}/${subdir}" ]]; then
            cp -r "${REPO_ROOT}/${subdir}" "${SKILL_DEST}/${subdir}"
        fi
    done

    # 标记安装来源
    touch "$INSTALL_MARKER"

    echo ""
    echo "✓ 主安装完成：${SKILL_DEST}/"
    echo ""

    # 根据 TARGET_AGENT 创建符号链接
    case "$TARGET_AGENT" in
        all)
            create_link "$LINK_CLAUDE" "$SKILL_DEST" "Claude Code"
            create_link "$LINK_OPENCODE" "$SKILL_DEST" "OpenCode"
            create_link "$LINK_OPENCLAW" "$SKILL_DEST" "OpenClaw"
            ;;
        claude-code)
            create_link "$LINK_CLAUDE" "$SKILL_DEST" "Claude Code"
            ;;
        opencode)
            create_link "$LINK_OPENCODE" "$SKILL_DEST" "OpenCode"
            ;;
        openclaw)
            create_link "$LINK_OPENCLAW" "$SKILL_DEST" "OpenClaw"
            ;;
    esac

    echo ""
    echo "─────────────────────────────────────────────"
    echo "安装摘要"
    echo "─────────────────────────────────────────────"
    echo "  主路径：${SKILL_DEST}/"
    echo "  Skill 文件："
    ls -la "${SKILL_DEST}/" | grep -v "^total" | grep -v "^\." | head -10
    echo ""
    echo "  符号链接："
    [[ -L "$LINK_CLAUDE" ]] && echo "    Claude Code: $(readlink "$LINK_CLAUDE")"
    [[ -L "$LINK_OPENCODE" ]] && echo "    OpenCode: $(readlink "$LINK_OPENCODE")"
    [[ -L "$LINK_OPENCLAW" ]] && echo "    OpenClaw: $(readlink "$LINK_OPENCLAW")"
    echo ""
    echo "✓ 安装完成！重启 Agent 会话即可使用此 skill。"
}

#────────────────────────────────────────────────────────────────────────────
# 入口
#────────────────────────────────────────────────────────────────────────────
if [[ "$UNINSTALL" == "true" ]]; then
    uninstall_skill
else
    install_skill
fi
