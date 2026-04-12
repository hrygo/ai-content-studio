# VoiceForge - 已知问题与解决方案

> 最后更新：2026-04-05 v1.1.1

## 🔧 安装问题

### 1. ffmpeg 需要 sudo 权限

**症状**：
```bash
E: Could not open lock file /var/lib/dpkg/lock-frontend - open (13: Permission denied)
```

**原因**：当前环境无 sudo 密码，无法通过 apt 安装系统包

**解决方案**：
```bash
# 方式 1: 联系管理员安装
sudo apt update && sudo apt install ffmpeg

# 方式 2: 使用 conda 安装（推荐）
conda install -c conda-forge ffmpeg

# 方式 3: 使用静态编译版本
wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
tar xf ffmpeg-release-amd64-static.tar.xz
export PATH="$PWD/ffmpeg-*-amd64-static:$PATH"
```

### 2. apt update hook 报错

**症状**：
```bash
/usr/bin/cnf-update-db: error while loading shared libraries: libapt-pkg.so.6.0: cannot open shared object file
```

**原因**：python3 通过 alternatives 指向 3.12，但 python3-apt 只为 3.10 编译

**解决方案**：
```bash
# 修改 cnf-update-db shebang，强制使用 Python 3.10
sudo sed -i '1s|^#!/usr/bin/python3$|#!/usr/bin/python3.10|' /usr/bin/cnf-update-db
```

---

## 🚀 运行时问题

### 1. voiceforge CLI 未安装

**症状**：
```bash
$ voiceforge --help
command not found: voiceforge
```

**原因**：clone 后未安装 Python 包，CLI 入口点未注册

**解决方案**：
```bash
# 方式 1: pip 可编辑安装（推荐）
cd voiceforge
python3 -m pip install -e . --break-system-packages

# 方式 2: 使用 PYTHONPATH
export PYTHONPATH="$PWD/src:$PYTHONPATH"
python3 -m infrastructure.cli --help

# 方式 3: 运行安装脚本（自动安装）
bash scripts/install.sh
```

### 2. MINIMAX_GROUP_ID 缺失

**症状**：
```bash
ValueError: MiniMax 引擎未配置，请设置 MINIMAX_API_KEY 和 MINIMAX_GROUP_ID
```

**原因**：opencode.json 中使用 Anthropic 兼容代理格式，不含 groupId

**解决方案**：
```bash
# 方式 1: 设置环境变量
export MINIMAX_GROUP_ID="your-group-id"

# 方式 2: 在 opencode.json 中添加 groupId
{
  "provider": {
    "minimax": {
      "options": {
        "apiKey": "your-api-key",
        "groupId": "your-group-id"  // 添加此行
      }
    }
  }
}

# 方式 3: 使用默认值（v1.1.0+ 已支持）
# 如果不设置，会自动使用 "default"
```

### 3. DashScope TTS 端点 404

**症状**：
```bash
ERROR: API 请求失败 (404): {"error": "Not Found"}
```

**原因**：DashScope OpenAI 兼容端点 `/audio/speech` 在当前 API Key 下不可用

**解决方案**：
```bash
# 使用 Qwen Omni TTS 引擎（基于 /chat/completions）
voiceforge synthesize --source "测试" --output test.mp3 --engine qwen_omni

# 或在角色库中指定 engine: qwen_omni
```

### 4. QWEN_API_KEY vs DASHSCOPE_API_KEY

**症状**：
```bash
ValueError: Qwen 引擎未配置，请设置 QWEN_API_KEY
```

**原因**：容器代码只检查 QWEN_API_KEY，不识别 DASHSCOPE_API_KEY

**解决方案**（v1.1.0+ 已修复）：
```bash
# 现在支持两种环境变量名称
export DASHSCOPE_API_KEY="your-key"  # 阿里云百炼 API Key
# 或
export QWEN_API_KEY="your-key"       # 通义千问 API Key（优先级更高）
```

### 5. 音色 ID 不匹配

**症状**：
```bash
ERROR: API 返回错误码: 1027, 消息: voice id not exist
```

**原因**：角色库中的部分音色 ID 在 speech-2.8-hd 模型下不可用

**不可用音色**：
- `male-qn-K`
- `female-tianmei_v2`
- `male-qn-bai`

**解决方案**：
```bash
# 运行音色测试脚本
python3 scripts/test_voices.py

# 查看可用音色列表
# 根据测试结果更新 references/configs/studio_roles.json
```

**推荐替换**：
```json
{
  "Casey": {
    "voice_id": "presenter_male",  // 原: male-qn-K
    ...
  },
  "Storyteller": {
    "voice_id": "female-tianmei",  // 原: female-tianmei_v2
    ...
  }
}
```

### 6. API 速率限制

**症状**：
```bash
ERROR: API 返回错误码: 2056, 消息: usage limit exceeded
```

**原因**：短时间内连续调用触发速率限制

**解决方案**（v1.1.0+ 已优化）：
- ✅ 自动检测 2056 错误码
- ✅ 指数退避重试（最多 5 次，最大等待 60 秒）
- ✅ 详细日志输出

**手动处理**：
```bash
# 方式 1: 减少并发（批量合成时）
# 将长文本拆分为多个小批次

# 方式 2: 增加延迟
# 在脚本中添加 time.sleep() 调用

# 方式 3: 升级 API 套餐
# 联系 MiniMax 客服提升配额
```

---

## 🛠 诊断工具

### 检查环境配置

```bash
# 检查 Python 版本
python3 --version

# 检查 pip
python3 -m pip --version

# 检查 ffmpeg
ffmpeg -version

# 检查环境变量
echo $MINIMAX_API_KEY
echo $MINIMAX_GROUP_ID
echo $DASHSCOPE_API_KEY
```

### 测试 API 连接

```bash
# 测试 MiniMax TTS
python3 -c "
import os
from src.services.api_client import MiniMaxClient
client = MiniMaxClient(api_key=os.getenv('MINIMAX_API_KEY'))
result = client.text_to_speech('测试', voice_id='male-qn-qingse')
print('✓ MiniMax API 连接成功' if result else '✗ MiniMax API 连接失败')
"

# 测试 Qwen TTS
python3 -c "
import os
from src.core.tts_engines.qwen_omni import QwenOmniTTSEngine
engine = QwenOmniTTSEngine(api_key=os.getenv('DASHSCOPE_API_KEY'))
print('✓ Qwen API 配置正确' if engine.is_available() else '✗ Qwen API 未配置')
"
```

### 测试音色

```bash
# 运行音色测试脚本
python3 scripts/test_voices.py
```

---

## 📝 提交问题

如果遇到其他问题，请提供以下信息：

1. **系统信息**：
   ```bash
   uname -a
   python3 --version
   pip show voiceforge
   ```

2. **错误日志**：
   ```bash
   # 完整的错误堆栈
   # API 响应内容
   # 环境变量（脱敏）
   ```

3. **复现步骤**：
   - 具体命令
   - 配置文件
   - 预期行为 vs 实际行为

提交地址：https://github.com/hrygo/voiceforge/issues

---

## 📚 相关文档

- [安装指南](INSTALL.md)
- [配置参考](../references/configs/)
- [API 文档](../docs/)
- [更新日志](../CHANGELOG.md)
