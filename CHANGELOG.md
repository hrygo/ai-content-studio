# Changelog

## [1.1.1] - 2026-04-05

### Changed
- **备份机制优化**: 将备份目录从 skills 目录迁移到 `/tmp/voiceforge-backups/`，避免污染 skills 目录。
- **自动备份清理**: 备份文件保留 7 天后自动清理，减少磁盘占用。
- **安装脚本增强**: 添加 `--cleanup-backups` 选项，支持手动清理所有备份文件。

### Fixed
- **遗留备份清理**: 自动清理旧版本安装在 skills 目录中的遗留备份文件。

## [1.1.0] - 2026-04-05

### Added
- **故障排查文档**: 新增 `docs/TROUBLESHOOTING.md`，详细记录安装和运行时问题的解决方案。
- **音色测试工具**: 新增 `scripts/test_voices.py`，用于测试和验证 TTS 音色可用性。
- **性能优化指南**: 在 SKILL.md 中添加速率限制处理和批量处理建议章节。

### Changed
- **依赖注入优化**: 重构 QwenTTSEngineAdapter 的初始化方式，改用延迟加载模式。
- **文档结构优化**: 将故障排查内容从 SKILL.md 整合到独立文档，提升可维护性。

### Fixed
- **CLI 命令注册**: 修复 `voiceforge` 命令在 pip install 后无法找到的问题。
- **Python 依赖安装**: 添加镜像回退机制，解决国内镜像 403 错误。
- **系统包保护绕过**: 自动添加 `--break-system-packages` 标志，解决 macOS Python 3.14+ 的安装限制。

## [1.0.2] - 2026-04-02

### Added
- **安装自动化增强**: `scripts/install.sh` 脚本现在会自动安装 Python 依赖。
- **Skill Bundle 结构补全**: 在安装包中补齐了 `requirements.txt`，确保 Agent 环境依赖完整。
- **文档校准**: 更新 `INSTALL.md` 中的 API 配置说明，使其与 `opencode.json` 的实际 JSON 路径一致。

## [1.0.1] - 2026-04-02

### Added
- **正式化表述**: 全面改写 `README.md`，采用专业的中立视角。
- **Token Plan 价值提升**: 优化了 MiniMax 套餐复用的引导描述，明确 Builder 权益。
- **GitHub 链接优化**: 将文档中的本地路径替换为完整的 GitHub 路径，确保外部访问准确性。

## [1.0.0] - 2026-04-02

### Added
- **VoiceForge Skill**: 本地工具正式重构为多 Agent 兼容的 Skill (支持 Claude Code, OpenCode, OpenClaw)。
- **存储整合**: 将所有临时文件和缓存统一至 `work/` 目录，简化结构。
- **结构优化**: 核心逻辑移至 `scripts/studio/`，文档移至 `references/`，提升 AI 检索效率。
- **MiniMax 优先策略**: 默认使用 MiniMax T2A V2，支持自动故障转移至 Qwen 模型。
- **套餐复用 (Token Plan) 赋能**: 深度整合 MiniMax Token Plan，支持复用“编码套餐”以大幅度降低生成成本。
- **全新文档体系**: 包含 `README.md`、`INSTALL.md` (含全流程 Agent 自动安装脚本) 及针对 Agent 优化的说明。

### Changed
- 重构项目文件布局，对齐 AI Agent Skill 目录标准。
- 简化 `.gitignore` 配置，仅忽略 `work/` 目录。
- 更新 `README.md`，使用更正式的非第一人称表述。
