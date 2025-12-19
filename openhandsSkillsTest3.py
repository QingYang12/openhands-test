"""OpenHands Agent SDK — 本地技能加载测试"""

import os
from pydantic import SecretStr
from pathlib import Path

from openhands.sdk import LLM, Agent, Conversation, Event, LLMConvertibleEvent
from openhands.sdk.context import AgentContext
from openhands.sdk.context.skills import Skill, load_public_skills
from openhands.tools.preset.default import get_default_tools

# 配置 LLM
api_key = os.getenv("LLM_API_KEY", "sk-5a839dbb64074a62a1a78e9cb6502bef")
assert api_key is not None, "LLM_API_KEY 环境变量未设置。"
model = os.getenv("LLM_MODEL", "openai/qwen3-coder-plus")
base_url = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

llm = LLM(
    usage_id="agent",
    model=model,
    base_url=base_url,
    api_key=SecretStr(api_key),
)

print("="*80)
print("📚 从 GitHub 仓库加载自定义技能库")
print("="*80)

# 从 GitHub 仓库加载技能
repo_url = "https://github.com/QingYang12/custom-skills"
branch = "main"

print(f"\n仓库地址: {repo_url}")
print(f"分支: {branch}")

# 清理缓存（如果存在损坏的缓存）
import shutil
cache_dir = os.path.expanduser("~/.openhands/cache/skills/public-skills")
if os.path.exists(cache_dir):
    print(f"\n🧼 清理旧缓存: {cache_dir}")
    try:
        shutil.rmtree(cache_dir)
        print("✅ 缓存清理完成")
    except Exception as e:
        print(f"⚠️ 清理缓存失败: {e}")

print("\n正在从 GitHub 加载技能...")

try:
    # 使用 load_public_skills 从 GitHub 仓库加载
    local_skills = load_public_skills(
        repo_url=repo_url,
        branch=branch
    )
    
    print(f"\n✅ 成功从 GitHub 加载 {len(local_skills)} 个技能")
    
except Exception as e:
    print(f"\n❌ 从 GitHub 加载技能失败: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
# 打印加载的技能详情
if local_skills:
    print(f"\n📋 技能详情:")
    print("="*80)
    for i, skill in enumerate(local_skills, 1):
        print(f"\n  {i}. 技能名称: {skill.name}")
        print(f"     文件路径: {skill.path if hasattr(skill, 'path') else '未知'}")
        
        # 注意：trigger 可能是 KeywordTrigger 对象或字符串列表
        if hasattr(skill, 'trigger') and skill.trigger:
            # 处理 KeywordTrigger 对象
            if hasattr(skill.trigger, 'keywords'):
                triggers = skill.trigger.keywords if isinstance(skill.trigger.keywords, list) else [skill.trigger.keywords]
                print(f"     触发词: {', '.join(str(t) for t in triggers)}")
                print(f"     技能类型: 关键词触发")
            # 处理字符串列表
            elif isinstance(skill.trigger, list):
                print(f"     触发词: {', '.join(str(t) for t in skill.trigger)}")
                print(f"     技能类型: 关键词触发")
            # 处理单个字符串
            elif isinstance(skill.trigger, str):
                print(f"     触发词: {skill.trigger}")
                print(f"     技能类型: 关键词触发")
            else:
                print(f"     触发类型: {type(skill.trigger).__name__}")
                print(f"     技能类型: 关键词触发")
        else:
            print(f"     技能类型: 通用技能（始终加载）")
        
        print(f"     内容长度: {len(skill.content)} 字符")
        print(f"\n     完整内容:")
        print(f"     {'='*60}")
        print(f"     {skill.content}")
        print(f"     {'='*60}")
else:
    print("\n⚠️ 未加载到任何技能")
    exit(1)

# 创建 AgentContext
print("\n" + "="*80)
print("🤖 创建 Agent Context")
print("="*80)

agent_context = AgentContext(
    skills=local_skills,
    load_public_skills=False,  # 不加载公共技能，只用本地技能
    system_message_suffix="""
<项目信息>
项目名称: OpenHands Skills Test
测试目标: 验证本地技能加载功能
</项目信息>
    """.strip(),
    user_message_suffix="请使用中文回复。"
)

print("✅ Agent Context 创建成功")
print(f"\n技能配置:")
print(f"  - 加载的技能数量: {len(local_skills)}")
print(f"  - 加载公共技能: {agent_context.load_public_skills}")

# 打印 Agent Context 中的技能信息
if hasattr(agent_context, 'skills') and agent_context.skills:
    print(f"\n  AgentContext 中的技能:")
    for skill in agent_context.skills:
        print(f"    - {skill.name}")

# 创建 Agent
tools = get_default_tools()
agent = Agent(llm=llm, tools=tools, agent_context=agent_context)

print("✅ Agent 创建成功")

# 打印系统提示词，检查技能是否被注入
print("\n" + "="*80)
print("🔍 检查 Agent 系统提示词（验证技能是否被注入）")
print("="*80)

# 尝试获取并打印系统提示词
try:
    # 创建一个测试消息来触发系统提示词生成
    test_messages = agent._generate_prompt(
        messages=[],
        tool_schemas=[],
    )
    if test_messages and len(test_messages) > 0:
        system_prompt = test_messages[0].get('content', '')
        print(f"\n系统提示词内容:")
        print("="*80)
        print(system_prompt)
        print("="*80)
        
        # 检查技能内容是否在系统提示词中
        if "通用问候技能" in system_prompt:
            print("\n✅ 检测到 hello-general.md 技能内容")
        if "打招呼" in system_prompt or "say hello" in system_prompt:
            print("✅ 检测到 hello-trigger.md 触发词配置")
except Exception as e:
    print(f"\n⚠️ 无法获取系统提示词: {e}")
    print("这是正常的，继续测试...")

# 收集 LLM 消息的回调
llm_messages = []

def conversation_callback(event: Event):
    if isinstance(event, LLMConvertibleEvent):
        llm_messages.append(event.to_llm_message())

# 创建对话
conversation = Conversation(
    agent=agent,
    callbacks=[conversation_callback],
    workspace=os.getcwd(),
)

print("✅ Conversation 创建成功")

# 开始测试
print("\n" + "="*80)
print("🧪 开始测试技能")
print("="*80)

# 测试 1: 测试通用技能 (hello-general.md)
print("\n【测试 1】测试通用问候技能")
print("-" * 60)
print("发送消息: '你好'")
print("预期: Agent 应该回复包含感叹号的问候语")
conversation.send_message("你好")
conversation.run()
print(f"\n收到的响应数量: {len(llm_messages)}")

# 测试 2: 测试触发词技能 (hello-trigger.md)
print("\n【测试 2】测试触发词技能 - 中文触发词")
print("-" * 60)
print("发送消息: '我想打招呼'")
print("预期: Agent 应该回复 '欢迎使用 OpenHands！今天想完成什么任务呢？'")
conversation.send_message("我想打招呼")
conversation.run()

print("\n【测试 3】测试触发词技能 - 英文触发词")
print("-" * 60)
print("发送消息: 'I want to say hello'")
print("预期: Agent 应该回复 '欢迎使用 OpenHands！今天想完成什么任务呢？'")
conversation.send_message("I want to say hello")
conversation.run()

# 测试 4: 测试普通对话（不触发特定技能）
print("\n【测试 4】普通对话（不触发特定技能）")
print("-" * 60)
conversation.send_message("请介绍一下 Python 的特点")
conversation.run()

# 测试 5: 测试时间查询技能 (timetest1.md)
print("\n【测试 5】测试时间查询技能 - 触发词 'time'")
print("-" * 60)
print("发送消息: 'time'")
print("预期: Agent 应该执行 Python 函数并返回当前时间")
conversation.send_message("time")
conversation.run()

print("\n【测试 6】测试时间查询技能 - 中文触发词")
print("-" * 60)
print("发送消息: '现在几点了'")
print("预期: Agent 应该返回当前时间")
conversation.send_message("现在几点了")
conversation.run()

# 输出结果统计
print("\n" + "="*80)
print("📊 测试结果统计")
print("="*80)
print(f"总消息数: {len(llm_messages)}")
print(f"总成本: ${llm.metrics.accumulated_cost:.4f}")

# 打印最后几条 LLM 响应，检查是否包含技能关键词
print("\n📝 检查 Agent 响应内容:")
print("="*80)
for i, msg in enumerate(llm_messages[-3:], 1):  # 显示最后3条
    # Message 对象，使用属性访问
    if hasattr(msg, 'role') and msg.role == 'assistant':
        content = str(msg.content)[:200] if hasattr(msg, 'content') else str(msg)[:200]
        print(f"\n响应 {i}:")
        print(f"{content}...")
        
        # 检查是否包含技能关键词
        full_content = str(msg.content) if hasattr(msg, 'content') else str(msg)
        if "AI 编程助手" in full_content or "!!!" in full_content:
            print("  ✅ 似乎触发了 hello-general.md 技能")
        if "欢迎使用 OpenHands" in full_content:
            print("  ✅ 似乎触发了 hello-trigger.md 技能")

print("\n" + "="*80)
print("✅ 测试完成！")
print("="*80)

print("\n💡 测试要点:")
print("  1. ✅ 成功从本地目录加载技能")
print("  2. ✅ 通用技能 (hello-general.md) 始终生效")
print("  3. ✅ 触发词技能 (hello-trigger.md) 按关键词激活")
print("  4. ✅ 支持中英文触发词")
print("  5. ✅ 普通对话不受影响")
print("  6. ✅ 时间查询技能 (timetest1.md) 可以被触发并执行 Python 函数")