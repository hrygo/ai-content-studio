#!/usr/bin/env python3
"""
音色测试工具
探测 MiniMax TTS API 支持的音色列表
"""
import os
import sys
import time
from pathlib import Path

# 添加 src 到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.api_client import MiniMaxClient


def test_voice(client: MiniMaxClient, voice_id: str, text: str = "测试") -> bool:
    """
    测试单个音色是否可用

    Args:
        client: MiniMax 客户端
        voice_id: 音色 ID
        text: 测试文本

    Returns:
        True 表示音色可用，False 表示不可用
    """
    try:
        result = client.text_to_speech(
            text=text,
            voice_id=voice_id,
            speed=1.0,
            vol=1.0,
            pitch=0,
            emotion="neutral"
        )
        return result is not None
    except Exception as e:
        error_msg = str(e)
        if "voice id not exist" in error_msg.lower():
            return False
        elif "status_code: 2056" in error_msg:
            # 速率限制，等待后重试
            print(f"  ⚠ 速率限制，等待 5 秒...")
            time.sleep(5)
            return test_voice(client, voice_id, text)
        else:
            print(f"  ✗ 错误: {error_msg}")
            return False


def main():
    """主函数"""
    api_key = os.getenv("MINIMAX_API_KEY")
    if not api_key:
        print("✗ 错误: 未设置 MINIMAX_API_KEY 环境变量")
        sys.exit(1)

    group_id = os.getenv("MINIMAX_GROUP_ID", "default")

    print(f"API Key: {api_key[:10]}...")
    print(f"Group ID: {group_id}")
    print("")

    client = MiniMaxClient(api_key=api_key)

    # 从角色库中提取音色列表
    import json
    roles_file = Path(__file__).parent.parent / "references" / "configs" / "studio_roles.json"

    with open(roles_file) as f:
        roles = json.load(f)

    # 提取唯一音色 ID
    voice_ids = set()
    for role_name, role_config in roles.items():
        if role_name.startswith("_"):
            continue
        voice_id = role_config.get("voice_id")
        if voice_id:
            voice_ids.add(voice_id)

    voice_ids = sorted(voice_ids)

    print(f"待测试音色 ({len(voice_ids)} 个):")
    for voice_id in voice_ids:
        print(f"  - {voice_id}")
    print("")

    # 测试每个音色
    available = []
    unavailable = []

    for i, voice_id in enumerate(voice_ids, 1):
        print(f"[{i}/{len(voice_ids)}] 测试 {voice_id}...", end=" ")

        if test_voice(client, voice_id):
            print("✓")
            available.append(voice_id)
        else:
            print("✗")
            unavailable.append(voice_id)

        # 避免速率限制
        time.sleep(0.5)

    # 输出结果
    print("")
    print("=" * 60)
    print("测试结果")
    print("=" * 60)
    print(f"✓ 可用音色 ({len(available)} 个):")
    for voice_id in available:
        print(f"  - {voice_id}")

    print("")
    print(f"✗ 不可用音色 ({len(unavailable)} 个):")
    for voice_id in unavailable:
        print(f"  - {voice_id}")
        # 找到使用该音色的角色
        for role_name, role_config in roles.items():
            if role_name.startswith("_"):
                continue
            if role_config.get("voice_id") == voice_id:
                print(f"      (角色: {role_name})")

    print("")
    print("建议替换映射:")
    if unavailable and available:
        # 简单建议：使用第一个可用的音色
        fallback = available[0]
        for voice_id in unavailable:
            print(f"  {voice_id} → {fallback}")


if __name__ == "__main__":
    main()
