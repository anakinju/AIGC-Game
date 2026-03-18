#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的聊天运行器入口点
"""

import sys
import os

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def main():
    """主函数"""
    print("=" * 50)
    print("聊天环境运行器")
    print("=" * 50)
    print()
    
    try:
        # 导入必要的模块
        from npc.multi_npc.chat_env import ChatEnvironment
        from main.chat_runner import create_chat_runner
        import json
        
        # 固定使用 demo.json 文件
        demo_path = os.path.join(current_dir, "data", "scene_data", "demo.json")
        
        if not os.path.exists(demo_path):
            print(f"错误: 没有找到 demo.json 文件")
            print(f"请确保在 {os.path.dirname(demo_path)} 目录下有 demo.json 文件")
            return 1
        
        # 读取 demo.json 获取场景列表
        try:
            with open(demo_path, 'r', encoding='utf-8') as f:
                scenes = json.load(f)
        except Exception as e:
            print(f"读取 demo.json 失败: {e}")
            return 1
        
        if not scenes or not isinstance(scenes, list):
            print("错误: demo.json 格式不正确或为空")
            return 1
        
        # 主循环：场景选择和游戏运行
        while True:
            # 显示可用场景
            print("\n" + "=" * 50)
            print("可用场景:")
            for i, scene in enumerate(scenes):
                scene_name = scene.get("name", f"场景 {i}")
                scene_location = scene.get("location", "未知位置")
                print(f"  {i}: {scene_name} - {scene_location}")
            print(f"  q: 退出程序")
            print("=" * 50)
            
            # 让用户选择场景
            try:
                choice = input(f"\n请选择场景 (0-{len(scenes)-1}, q退出): ").strip()
                
                if choice.lower() in ['q', 'quit', 'exit']:
                    print("再见！")
                    return 0
                
                scene_index = int(choice)
                
                if not (0 <= scene_index < len(scenes)):
                    print("无效的选择")
                    continue
                
                selected_scene = scenes[scene_index]
                print(f"\n选择场景: {selected_scene.get('name', f'场景 {scene_index}')} - {selected_scene.get('location', '未知位置')}")
                
            except (ValueError, KeyboardInterrupt):
                print("\n取消操作")
                continue
            
            # 初始化聊天环境
            print("\n正在初始化聊天环境...")
            try:
                # 修复：直接使用原始 demo_path 和选中的 index，而不是创建临时文件
                chat_env = ChatEnvironment(
                    scene_path=demo_path,
                    scene_index=scene_index,  # 使用用户选中的索引
                    chat_mode="player_involved",
                    enable_memory_system=False,
                    enable_player_validation=True
                )
                print("聊天环境初始化成功！\n")
                
            except Exception as e:
                print(f"初始化失败: {e}")
                print("\n提示: 可能是场景文件格式问题")
                import traceback
                traceback.print_exc()
                continue
            
            # 创建运行器并运行场景
            runner = create_chat_runner(chat_env)
            
            print("=" * 50)
            print("开始场景游戏")
            print("输入 'exit' 可退出当前场景并返回场景选择")
            print("=" * 50)
            
            # 运行场景
            scene_result = runner.run_scene()
            
            # 显示场景结果
            if scene_result.get("worldstate_summary"):
                print("\n" + "=" * 50)
                print("WorldState 结算报告:")
                print(scene_result["worldstate_summary"])
                print("=" * 50)
            
            print(f"\n场景结束，原因: {scene_result.get('exit_reason', '未知')}")
            input("\n按回车键返回场景选择...")
        
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
        return 0
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())