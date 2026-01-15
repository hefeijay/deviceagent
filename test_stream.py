#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试流式和非流式API
"""
import requests
import json
import time
from typing import Iterator


def test_non_stream():
    """测试非流式API"""
    print("=" * 60)
    print("【非流式API测试】")
    print("=" * 60)
    
    url = "http://localhost:8000/api/v1/chat"
    
    payload = {
        "query": "帮我给AI2喂食1份",
        "session_id": "test-non-stream-001"
    }
    
    print(f"\n📤 发送请求: {payload['query']}")
    print("⏳ 等待响应...\n")
    
    start_time = time.time()
    
    response = requests.post(url, json=payload, timeout=60)
    
    end_time = time.time()
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 响应成功 (耗时: {end_time - start_time:.2f}秒)")
        print(f"\n📊 结果:")
        print(f"  - Success: {data['success']}")
        print(f"  - Device Type: {data['device_type']}")
        
        if data['result'] and 'messages' in data['result']:
            content = data['result']['messages'][0].get('content', '')
            print(f"\n💬 AI回复:\n{content}\n")
    else:
        print(f"❌ 请求失败: {response.status_code}")
        print(response.text)


def test_stream():
    """测试流式API"""
    print("=" * 60)
    print("【流式API测试】")
    print("=" * 60)
    
    url = "http://localhost:8000/api/v1/chat/stream"
    
    payload = {
        "query": "帮我给AI2喂食1份",
        "session_id": "test-stream-001"
    }
    
    print(f"\n📤 发送流式请求: {payload['query']}")
    print("📡 开始接收流式数据...\n")
    
    start_time = time.time()
    
    try:
        with requests.post(url, json=payload, stream=True, timeout=60) as response:
            if response.status_code == 200:
                print("✅ 连接成功，开始接收事件:\n")
                
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        
                        # SSE 格式: "data: {json}"
                        if line.startswith('data: '):
                            data_str = line[6:]  # 移除 "data: " 前缀
                            
                            try:
                                event = json.loads(data_str)
                                event_type = event.get('type', 'unknown')
                                
                                current_time = time.time() - start_time
                                
                                if event_type == 'start':
                                    print(f"[{current_time:.2f}s] 🚀 开始处理任务")
                                    print(f"           Session ID: {event.get('session_id')}")
                                
                                elif event_type == 'node_update':
                                    node = event.get('node', 'unknown')
                                    print(f"[{current_time:.2f}s] 🔄 节点更新: {node}")
                                
                                elif event_type == 'message':
                                    content = event.get('content', '')
                                    source = event.get('source', 'unknown')
                                    print(f"[{current_time:.2f}s] 💬 消息来自 {source}:")
                                    # 只显示前100个字符
                                    preview = content[:100] + "..." if len(content) > 100 else content
                                    print(f"           {preview}")
                                
                                elif event_type == 'done':
                                    print(f"[{current_time:.2f}s] ✅ 任务完成")
                                    print(f"           Success: {event.get('success')}")
                                    print(f"           Device Type: {event.get('device_type')}")
                                    
                                    # 显示完整的最终回复
                                    if event.get('result') and event['result'].get('messages'):
                                        content = event['result']['messages'][0].get('content', '')
                                        print(f"\n💬 完整AI回复:\n{content}\n")
                                
                                elif event_type == 'error':
                                    print(f"[{current_time:.2f}s] ❌ 错误: {event.get('error')}")
                            
                            except json.JSONDecodeError:
                                print(f"⚠️ 无法解析JSON: {data_str[:100]}")
                
                end_time = time.time()
                print(f"\n⏱️ 总耗时: {end_time - start_time:.2f}秒")
            
            else:
                print(f"❌ 请求失败: {response.status_code}")
                print(response.text)
    
    except Exception as e:
        print(f"❌ 流式请求异常: {e}")


def main():
    print("\n" + "🎯" * 30)
    print("设备管理Agent - 流式 vs 非流式 API 对比测试")
    print("🎯" * 30 + "\n")
    
    # 测试非流式API
    # test_non_stream()
    
    print("\n" + "-" * 60 + "\n")
    
    # 等待一下
    time.sleep(2)
    
    # 测试流式API
    test_stream()
    
    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)
    print("\n💡 总结:")
    print("  - 非流式API: 一次性返回所有结果，适合同步场景")
    print("  - 流式API: 实时推送进度和结果，适合长时间任务和需要实时反馈的场景")
    print("")


if __name__ == "__main__":
    main()

