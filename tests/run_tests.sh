#!/bin/bash
# TTS 工具集完整测试脚本

set -e

echo "=== TTS V5.0 完整测试 ==="
echo ""

# 1. 检查依赖
echo "1. 检查 Python 依赖..."
pip3 install -q tenacity rich cachetools requests
echo "   ✓ 依赖已安装"

# 2. 测试 LLM 脚本生成（使用缓存测试）
echo ""
echo "2. 测试 LLM 脚本生成..."
python3 content_studio.py \
    --source "人工智能正在改变世界" \
    --mode summary \
    --output tests/test_script.txt
echo "   ✓ 脚本生成成功"

# 3. 测试 TTS 单段合成
echo ""
echo "3. 测试 TTS 单段合成..."
python3 minimax_tts_tool.py \
    "这是一个测试音频" \
    -o tests/test_single.mp3
echo "   ✓ 单段合成成功"

# 4. 测试 TTS 多段合成（使用测试数据）
echo ""
echo "4. 测试 TTS 多段合成..."
python3 minimax_tts_tool.py \
    -s tests/demo_segments.json \
    -o tests/test_multi.mp3
echo "   ✓ 多段合成成功"

# 5. 测试完整管道
echo ""
echo "5. 测试完整管道 (LLM → TTS)..."
python3 studio_run.py \
    --source tests/debate.txt \
    --mode deep_dive \
    --stereo \
    -o tests/test_final.mp3
echo "   ✓ 完整管道成功"

# 6. 验证输出文件
echo ""
echo "6. 验证输出文件..."
ls -lh tests/*.mp3 tests/test_script.txt 2>/dev/null | awk '{print "   " $9 ": " $5}'

echo ""
echo "=== 测试完成 ==="
