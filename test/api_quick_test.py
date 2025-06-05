#!/usr/bin/env python3
"""
PodLens API 快速测试
Quick test for PodLens API
"""

def test_api():
    """快速测试API功能"""
    try:
        from podlens import process_apple_podcast_auto
        
        print("🧪 测试 PodLens API...")
        
        # 测试 All-in 播客
        result = process_apple_podcast_auto(
            podcast_name="All-in",
            enable_transcription=True,
            enable_summary=True,  # 启用摘要测试完整功能
            enable_visualization=True
        )
        
        # 显示结果
        print(f"✅ 测试完成!")
        print(f"找到频道: {result['channels_found']}")
        print(f"下载成功: {result['downloads_success']}")
        print(f"转录成功: {result['transcripts_success']}")
        
        if result['output_files']:
            print(f"输出文件: {len(result['output_files'])} 个")
        
        if result['errors']:
            print(f"错误: {len(result['errors'])} 个")
        
        return result['downloads_success'] > 0
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    success = test_api()
    print(f"\n🎯 测试结果: {'成功' if success else '失败'}") 