import os
import sys

# 将当前脚本所在目录加入 Python 搜索路径，以便导入正式脚本
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    from minimax_tts_tool import text_to_speech, load_api_key
except ImportError:
    print("错误：无法找到正式脚本 minimax_tts_tool.py，请确保两个文件在同一目录下。")
    sys.exit(1)

def run_suite():
    """测试套件：验证正式脚本的核心功能"""
    print("正在启动 MiniMax TTS 正式脚本集成测试...\n")
    
    test_results = []

    # 测试案例 1: 基础合成功能
    print("[测试 1] 验证基础文字转语音功能...")
    out1 = os.path.join(current_dir, "test_basic.mp3")
    res1 = text_to_speech("集成测试：验证正式脚本的基础合成逻辑。", out1)
    if res1 and os.path.exists(out1):
        test_results.append(("基础合成", "通过"))
        print(f"  - 产出文件已验证: {out1}")
    else:
        test_results.append(("基础合成", "失败"))

    # 测试案例 2: 配置加载逻辑
    print("\n[测试 2] 验证 opencode.json 配置加载...")
    key = load_api_key()
    if key and key.startswith("sk-cp-"):
        test_results.append(("配置加载", "通过"))
        print(f"  - 成功获取 API Key: {key[:10]}******{key[-4:]}")
    else:
        test_results.append(("配置加载", "失败"))

    # 测试案例 3: 音色指定
    print("\n[测试 3] 验证指定音色 (male-qn-qingse) 参数传递...")
    out3 = os.path.join(current_dir, "test_voice.mp3")
    res3 = text_to_speech("测试音色切换逻辑是否正常。", out3, voice_id="male-qn-qingse")
    if res3 and os.path.exists(out3):
        test_results.append(("音色指定", "通过"))
    else:
        test_results.append(("音色指定", "失败"))

    # 总结输出
    print("\n" + "="*30)
    print("测试结果汇总：")
    for name, status in test_results:
        print(f" {name}: [{status}]")
    print("="*30)

    # 清理测试产出 (可选，为了确国产出存在，本次保留)
    # os.remove(out1)
    # os.remove(out3)

if __name__ == "__main__":
    run_suite()
