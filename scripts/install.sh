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
# Skill Bundle 结构（Clean Architecture 重构后）：
#   SKILL.md           ← Skill 主入口（Claude Code skill 识别文件）
#   pyproject.toml     ← Python 包配置（pip install -e .）
#   requirements.txt   ← pip 依赖清单（可选）
#   scripts/install.sh ← 安装脚本（安装到目标后保留，用于卸载/重装）
#   README.md / INSTALL.md / CHANGELOG.md ← 文档
#   src/               ← Clean Architecture 源码
#   tests/             ← 测试套件
#   docs/              ← 文档
#   references/        ← 角色库配置
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
CLEANUP_BACKUPS=false

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
  --cleanup-backups        清理所有备份文件（在 /tmp 中）
  --help                   显示此帮助

安装路径：
  ~/.agents/skills/ai-content-studio/         主路径（通用标准）
  ~/.claude/skills/ai-content-studio          Claude Code 符号链接
  ~/.config/opencode/skills/ai-content-studio OpenCode 符号链接
  ~/.openclaw/skills/ai-content-studio        OpenClaw 符号链接

备份位置：
  /tmp/ai-content-studio-backups/             所有备份文件
  （自动清理 7 天前的备份）

安装后可用：
  ai-studio synthesize ...   # 单段 TTS
  ai-studio dialogue ...     # 对话脚本 TTS
  ai-studio studio ...       # AI 播客（全流程）
  ai-studio batch ...         # 批量 TTS

示例：
  bash scripts/install.sh                      # 安装到所有 Agent
  bash scripts/install.sh --agent claude-code # 仅安装到 Claude Code
  bash scripts/install.sh --uninstall          # 卸载所有 Agent 的安装
  bash scripts/install.sh --cleanup-backups    # 清理所有备份文件
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
        --cleanup-backups)
            CLEANUP_BACKUPS=true
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

# 备份到 /tmp 目录（避免污染 skills 目录）
backup_to_tmp() {
    local source_path="$1"
    local backup_type="${2:-generic}"  # 类型：link, dir, file, main_install, legacy_link
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)

    # 创建备份目录
    local backup_base="/tmp/ai-content-studio-backups"
    mkdir -p "$backup_base"

    # 生成备份文件名（包含类型、原路径哈希、时间戳）
    local path_hash
    path_hash=$(echo "$source_path" | cksum | cut -d' ' -f1)
    local backup_name="backup_${backup_type}_${path_hash}_${timestamp}"

    local backup_path="${backup_base}/${backup_name}"

    # 备份到 /tmp
    if [[ -d "$source_path" ]]; then
        # 目录：打包压缩
        tar -czf "${backup_path}.tar.gz" -C "$(dirname "$source_path")" "$(basename "$source_path")" 2>/dev/null
        echo "  ! 备份目录到：${backup_path}.tar.gz"
        # 删除原目录
        rm -rf "$source_path"
    elif [[ -f "$source_path" ]] || [[ -L "$source_path" ]]; then
        # 文件或符号链接：直接移动
        mv "$source_path" "$backup_path"
        echo "  ! 备份到：${backup_path}"
    fi

    # 自动清理 7 天前的备份
    find "$backup_base" -name "backup_*" -mtime +7 -type f -delete 2>/dev/null || true
}

# 清理所有备份
cleanup_all_backups() {
    local backup_base="/tmp/ai-content-studio-backups"

    if [[ -d "$backup_base" ]]; then
        local backup_count
        backup_count=$(ls -1 "$backup_base" 2>/dev/null | wc -l | tr -d ' ')

        if [[ "$backup_count" -gt 0 ]]; then
            echo "→ 清理备份目录：${backup_base}"
            echo "  找到 ${backup_count} 个备份文件"
            rm -rf "$backup_base"
            echo "✓ 备份已清理"
        else
            echo "✓ 无备份文件需要清理"
        fi
    else
        echo "✓ 备份目录不存在"
    fi
}

# 备份已有文件/目录（使用 /tmp）
backup_existing() {
    local path="$1"
    local desc="${2:-已存在的路径}"

    if [[ -L "$path" ]]; then
        # 符号链接：备份链接本身
        local link_target
        link_target="$(readlink "$path")"
        echo "  ! 备份已有符号链接 ${path} → ${link_target}"
        backup_to_tmp "$path" "link"
    elif [[ -d "$path" ]]; then
        # 实体目录（非符号链接）：打包备份
        echo "  ! 检测到旧安装（实体目录）：${path}"
        backup_to_tmp "$path" "dir"
    elif [[ -f "$path" ]]; then
        # 普通文件：备份
        echo "  ! 备份已有文件：${path}"
        backup_to_tmp "$path" "file"
    fi
}

# 创建符号链接（幂等：先备份已存在的）
create_link() {
    local link_path="$1"
    local target="$2"
    local desc="${3:-符号链接}"

    # 确保父目录存在
    mkdir -p "$(dirname "$link_path")"

    # 备份已存在的路径（-e 对符号链接返回 true，无需额外 -L）
    if [[ -e "$link_path" ]]; then
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
            backup_to_tmp "$link_path" "legacy_link"
            ((links_removed++)) || true
        fi
    done

    # 备份并删除主安装
    if [[ -d "$SKILL_DEST" ]]; then
        echo "  → 备份主安装：${SKILL_DEST}"
        backup_to_tmp "$SKILL_DEST" "main_install"
        echo "✓ 主安装已备份到 /tmp"
    fi

    # 显示备份信息
    local backup_base="/tmp/ai-content-studio-backups"
    if [[ -d "$backup_base" ]]; then
        local backup_count
        backup_count=$(ls -1 "$backup_base" 2>/dev/null | wc -l | tr -d ' ')
        if [[ "$backup_count" -gt 0 ]]; then
            echo ""
            echo "  ℹ 备份位置：${backup_base}/"
            echo "  ℹ 备份文件：${backup_count} 个"
            echo "  ℹ 清理命令：rm -rf ${backup_base}"
        fi
    fi

    echo ""
    if [[ $links_removed -eq 0 && ! -d "$SKILL_DEST" ]]; then
        echo "✓ 未找到已安装的 skill"
    else
        echo "✓ 卸载完成"
    fi
}

#────────────────────────────────────────────────────────────────────────────
# 依赖检测
#────────────────────────────────────────────────────────────────────────────
check_dependencies() {
    echo "→ 检查系统依赖..."

    local missing_deps=()

    # 检查 Python 3
    if ! command -v python3 &>/dev/null; then
        missing_deps+=("python3")
        echo "  ✗ Python 3 未安装"
    else
        local python_version
        python_version=$(python3 --version 2>&1 | awk '{print $2}')
        echo "  ✓ Python ${python_version}"
    fi

    # 检查 pip
    if ! python3 -m pip --version &>/dev/null; then
        missing_deps+=("pip")
        echo "  ✗ pip 未安装"
    else
        echo "  ✓ pip 可用"
    fi

    # 检查 ffmpeg（可选，用于音频处理）
    if ! command -v ffmpeg &>/dev/null; then
        echo "  ⚠ ffmpeg 未安装（音频处理功能将受限）"
        echo "    安装命令："
        echo "      macOS:  brew install ffmpeg"
        echo "      Linux:  sudo apt install ffmpeg"
    else
        local ffmpeg_version
        ffmpeg_version=$(ffmpeg -version 2>&1 | head -1 | awk '{print $3}')
        echo "  ✓ ffmpeg ${ffmpeg_version}"
    fi

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        echo ""
        echo "✗ 缺少必需依赖：${missing_deps[*]}"
        echo "  请先安装这些依赖后再运行安装脚本。"
        exit 1
    fi

    echo ""
}

#────────────────────────────────────────────────────────────────────────────
# 安装
#────────────────────────────────────────────────────────────────────────────
install_skill() {
    # 检查依赖
    check_dependencies

    if [[ ! -f "${REPO_ROOT}/SKILL.md" ]] || [[ ! -d "${REPO_ROOT}/src" ]]; then
        echo "✗ 错误：找不到 SKILL.md 或 src/ 目录"
        echo "  请确保在 ai-content-studio 项目根目录运行此脚本。"
        exit 1
    fi

    echo "→ 安装 ai-content-studio skill..."
    echo "  源目录：${REPO_ROOT}/"
    echo "  目标 Agent：${TARGET_AGENT}"
    echo ""

    # 检测路径自引用：REPO_ROOT == SKILL_DEST 表示从 skill 目录内直接运行
    # 此时 SKILL_DEST 就是源码本身，backup_to_tmp 会删除源码，导致后续复制失败
    if [[ "$REPO_ROOT" == "$SKILL_DEST" ]]; then
        echo "  ℹ 检测到从 skill 源目录内运行（REPO_ROOT == SKILL_DEST）"
        echo "  ℹ 跳过备份/删除/复制步骤，直接创建符号链接..."
        echo ""

        # 只创建符号链接（其他 agent 的 link）
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
        echo "✓ 安装完成！"
        return
    fi

    # 备份主安装（如果存在）
    if [[ -d "$SKILL_DEST" ]]; then
        echo "  ! 已存在主安装，备份到 /tmp..."
        backup_to_tmp "$SKILL_DEST" "main_install"
    fi

    # 创建主目录
    mkdir -p "$(dirname "$SKILL_DEST")"
    mkdir "$SKILL_DEST"

    # 复制 skill bundle
    echo "  → 复制 skill bundle..."
    cp "${REPO_ROOT}/SKILL.md" "${SKILL_DEST}/SKILL.md"
    cp "${REPO_ROOT}/pyproject.toml" "${SKILL_DEST}/pyproject.toml"

    # requirements.txt（如存在，供 pip install -r 参考）
    [[ -f "${REPO_ROOT}/requirements.txt" ]] && \
        cp "${REPO_ROOT}/requirements.txt" "${SKILL_DEST}/requirements.txt"

    # scripts/（install.sh 用于卸载/重装）
    if [[ -d "${REPO_ROOT}/scripts" ]]; then
        cp -r "${REPO_ROOT}/scripts" "${SKILL_DEST}/scripts"
    fi

    # README/INSTALL/CHANGELOG（如存在）
    for doc in README.md INSTALL.md CHANGELOG.md; do
        [[ -f "${REPO_ROOT}/${doc}" ]] && \
            cp "${REPO_ROOT}/${doc}" "${SKILL_DEST}/${doc}"
    done

    # 复制 Clean Architecture 源码（排除 __pycache__ / .pyc）
    rsync -a --exclude '__pycache__' --exclude '*.pyc' \
        "${REPO_ROOT}/src/" "${SKILL_DEST}/src/"

    for subdir in tests docs references; do
        if [[ -d "${REPO_ROOT}/${subdir}" ]]; then
            rsync -a --exclude '__pycache__' --exclude '*.pyc' \
                "${REPO_ROOT}/${subdir}/" "${SKILL_DEST}/${subdir}/"
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
    ls -1 "${SKILL_DEST}/" | head -10
    echo ""
    echo "  符号链接："
    [[ -L "$LINK_CLAUDE" ]] && echo "    Claude Code: $(readlink "$LINK_CLAUDE")"
    [[ -L "$LINK_OPENCODE" ]] && echo "    OpenCode: $(readlink "$LINK_OPENCODE")"
    [[ -L "$LINK_OPENCLAW" ]] && echo "    OpenClaw: $(readlink "$LINK_OPENCLAW")"
    # 自动安装 Python 依赖
    if [[ -f "${SKILL_DEST}/pyproject.toml" ]]; then
        echo "  → 安装 Python 依赖..."

        # 安装函数：支持镜像回退
        install_deps() {
            local flags="--break-system-packages --quiet"

            # 尝试 1: 使用默认镜像（pip.conf 配置）
            if python3 -m pip install -e "${SKILL_DEST}" $flags 2>/dev/null; then
                return 0
            fi

            # 尝试 2: 回退到官方 PyPI（解决国内镜像 403 问题）
            echo "  ! 默认镜像失败，切换到官方 PyPI..."
            if python3 -m pip install -e "${SKILL_DEST}" $flags \
                --index-url https://pypi.org/simple 2>/dev/null; then
                return 0
            fi

            return 1
        }

        # 执行安装
        if install_deps; then
            echo "  ✓ Python 依赖安装完成（ai-studio CLI 已注册）"
        else
            echo "  ✗ 自动安装失败。请手动执行："
            echo "    python3 -m pip install -e \"${SKILL_DEST}\" \\"
            echo "      --break-system-packages \\"
            echo "      --index-url https://pypi.org/simple"
        fi
    fi

    echo ""
    echo "✓ 安装完成！重启 Agent 会话即可使用此 skill。"
}

#────────────────────────────────────────────────────────────────────────────
# 入口
#────────────────────────────────────────────────────────────────────────────
if [[ "$CLEANUP_BACKUPS" == "true" ]]; then
    cleanup_all_backups
elif [[ "$UNINSTALL" == "true" ]]; then
    uninstall_skill
else
    install_skill
fi
