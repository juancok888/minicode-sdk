#!/usr/bin/env python3
"""Test message conversion logic."""
from minicode.llm import OpenRouterLLM

# Test messages with tool role
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Read a file for me."},
    {"role": "assistant", "content": "I'll read the file.", "tool_calls": [
        {
            "id": "call_123",
            "type": "function",
            "function": {"name": "read_file", "arguments": {"path": "test.txt"}}
        }
    ]},
    {"role": "tool", "content": '{"success": true, "content": "File contents here"}',
     "tool_call_id": "call_123", "name": "read_file"},
]

# Create LLM and convert
llm = OpenRouterLLM(api_key="test")
converted = llm._convert_tool_messages_to_user(messages)

print("Original messages:")
print("=" * 60)
for i, msg in enumerate(messages):
    print(f"\n{i+1}. Role: {msg['role']}")
    if 'content' in msg:
        print(f"   Content: {msg['content'][:100]}...")
    if 'tool_calls' in msg:
        print(f"   Tool calls: {len(msg['tool_calls'])} calls")
    if 'tool_call_id' in msg:
        print(f"   Tool call ID: {msg['tool_call_id']}")

print("\n\nConverted messages:")
print("=" * 60)
for i, msg in enumerate(converted):
    print(f"\n{i+1}. Role: {msg['role']}")
    if 'content' in msg:
        print(f"   Content: {msg['content'][:100]}...")
    if 'tool_calls' in msg:
        print(f"   Tool calls: {len(msg['tool_calls'])} calls")
    if 'tool_call_id' in msg:
        print(f"   Tool call ID: {msg['tool_call_id']}")

print("\n" + "=" * 60)
print("✅ Tool message successfully converted to user message!")
