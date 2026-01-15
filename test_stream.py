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
    """测试流式API（完整版 - 包含所有事件类型）"""
    print("=" * 60)
    print("【流式API测试 - 完整中间过程展示】")
    print("=" * 60)
    
    url = "http://localhost:8000/api/v1/chat/stream"
    
    payload = {
        "query": "帮我查一下最近的喂食记录判断是否需要喂食，需要的话帮我给AI2喂食2份",
        "session_id": "test-stream-001"
    }
    
    print(f"\n📤 发送流式请求: {payload['query']}")
    print("📡 开始接收流式数据...\n")
    
    start_time = time.time()
    event_count = 0
    
    try:
        with requests.post(url, json=payload, stream=True, timeout=120) as response:
            if response.status_code == 200:
                print("✅ 连接成功，开始接收事件:\n")
                print("-" * 60)
                
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        
                        # SSE 格式: "data: {json}"
                        if line.startswith('data: '):
                            data_str = line[6:]  # 移除 "data: " 前缀
                            
                            try:
                                event = json.loads(data_str)
                                event_type = event.get('type', 'unknown')
                                event_count += 1
                                
                                current_time = time.time() - start_time
                                
                                # 格式化事件输出
                                timestamp = f"[{current_time:.2f}s #{event_count:03d}]"
                                
                                if event_type == 'start':
                                    print(f"{timestamp} 🚀 START: {event.get('query', '')[:50]}...")
                                
                                elif event_type == 'node':
                                    print(f"{timestamp} 📋 NODE: {event.get('node', 'unknown')}")
                                    print(f"              {event.get('message', '')}")
                                
                                elif event_type == 'status':
                                    print(f"{timestamp} ℹ️  STATUS: {event.get('message', '')}")
                                
                                elif event_type == 'expert_start':
                                    print(f"{timestamp} 🧑‍🏫 EXPERT START")
                                    print(f"              {event.get('message', '')}")
                                
                                elif event_type == 'expert_stream':
                                    content = event.get('content', '')
                                    preview = content[:80] + "..." if len(content) > 80 else content
                                    print(f"{timestamp} 📡 EXPERT STREAM: {preview}")
                                
                                elif event_type == 'expert_done':
                                    print(f"{timestamp} ✅ EXPERT DONE")
                                    print(f"              {event.get('message', '')}")
                                
                                elif event_type == 'expert_error':
                                    print(f"{timestamp} ❌ EXPERT ERROR: {event.get('error', '')}")
                                
                                elif event_type == 'routing':
                                    print(f"{timestamp} 🔀 ROUTING: {event.get('device_type', '')} → {event.get('target_node', '')}")
                                
                                elif event_type == 'devices_found':
                                    print(f"{timestamp} 🔍 DEVICES FOUND: {event.get('count', 0)} 个设备")
                                
                                elif event_type == 'agent_start':
                                    print(f"{timestamp} 🤖 AGENT START: {event.get('agent', '')}")
                                
                                elif event_type == 'tool_call':
                                    tool = event.get('tool', 'unknown')
                                    args = event.get('args', {})
                                    print(f"{timestamp} 🔧 TOOL CALL: {tool}")
                                    print(f"              Args: {json.dumps(args, ensure_ascii=False)[:80]}")
                                
                                elif event_type == 'tool_result':
                                    result = event.get('result', {})
                                    preview = json.dumps(result, ensure_ascii=False)[:100]
                                    print(f"{timestamp} 📤 TOOL RESULT: {preview}...")
                                
                                elif event_type == 'message':
                                    content = event.get('content', '')
                                    source = event.get('source', 'unknown')
                                    print(f"{timestamp} 💬 MESSAGE from {source}:")
                                    # 显示前150个字符
                                    preview = content[:150] + "..." if len(content) > 150 else content
                                    print(f"              {preview}")
                                
                                elif event_type == 'done':
                                    print(f"\n{timestamp} ✅ DONE")
                                    print(f"              Success: {event.get('success')}")
                                    print(f"              Device Type: {event.get('device_type')}")
                                    
                                    # 显示完整的最终回复
                                    if event.get('result') and event['result'].get('messages'):
                                        final_msg = event['result']['messages'][0]
                                        content = final_msg.get('content', '')
                                        print(f"\n{'=' * 60}")
                                        print("📄 最终AI回复:")
                                        print("=" * 60)
                                        print(content)
                                        print("=" * 60)
                                
                                elif event_type == 'error':
                                    print(f"{timestamp} ❌ ERROR: {event.get('error', '')}")
                                
                                else:
                                    # 其他未知事件类型
                                    print(f"{timestamp} ❓ {event_type.upper()}: {event.get('message', '')}")
                            
                            except json.JSONDecodeError as e:
                                print(f"⚠️ 无法解析JSON: {data_str[:100]}")
                                print(f"   错误: {e}")
                
                end_time = time.time()
                print(f"\n⏱️ 总耗时: {end_time - start_time:.2f}秒")
                print(f"📊 事件总数: {event_count}")
            
            else:
                print(f"❌ 请求失败: {response.status_code}")
                print(response.text)
    
    except Exception as e:
        print(f"❌ 流式请求异常: {e}")
        import traceback
        traceback.print_exc()


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

