"""
Agent 委托示例

此示例演示了 Agent 委托功能，主 Agent 将任务委托给子 Agent 进行并行处理。
每个子 Agent 独立运行并将结果返回给主 Agent，
主 Agent 然后将两个分析合并成一个统一的报告。
"""

import os

from pydantic import SecretStr

from openhands.sdk import (
    LLM,
    Agent,
    AgentContext,
    Conversation,
    Tool,
    get_logger,
)
from openhands.sdk.context import Skill
from openhands.sdk.tool import register_tool
from openhands.tools.delegate import (
    DelegateTool,
    DelegationVisualizer,
    register_agent,
)
from openhands.tools.preset.default import get_default_tools


ONLY_RUN_SIMPLE_DELEGATION = False

logger = get_logger(__name__)

# 配置 LLM 和 agent
# 你可以从 https://app.all-hands.dev/settings/api-keys 获取 API key
api_key = os.getenv("LLM_API_KEY")
assert api_key is not None, "LLM_API_KEY 环境变量未设置。"
model = os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929")
llm = LLM(
    model=model,
    api_key=SecretStr(api_key),
    base_url=os.environ.get("LLM_BASE_URL", None),
    usage_id="agent",
)

cwd = os.getcwd()

register_tool("DelegateTool", DelegateTool)
tools = get_default_tools(enable_browser=False)
tools.append(Tool(name="DelegateTool"))

main_agent = Agent(
    llm=llm,
    tools=tools,
)
conversation = Conversation(
    agent=main_agent,
    workspace=cwd,
    visualizer=DelegationVisualizer(name="Delegator"),
)

task_message = (
    "忘掉编程吧，让我们切换到旅行规划。"
    "让我们规划一次伦敦之旅。我有两个问题需要解决："
    "住宿：在考虑预算的情况下，最好的住宿区域是哪里？"
    "活动：前 5 个必看景点和隐藏宝藏有哪些？"
    "请使用委托工具并行处理这两个任务。"
    "确保子 Agent 使用自己的知识，"
    "不要依赖互联网访问。"
    "他们应该保持简短。获得结果后，将两个分析合并成一个统一报告。\n\n"
)
conversation.send_message(task_message)
conversation.run()

conversation.send_message(
    "询问住宿子 Agent 对科文特花园的看法。"
)
conversation.run()

# 报告简单委托示例的成本
cost_1 = conversation.conversation_stats.get_combined_metrics().accumulated_cost
print(f"示例成本（简单委托）: {cost_1}")

print("简单委托示例完成！", "\n" * 20)


# -------- Agent 委托第二部分：用户自定义 Agent 类型 --------

if ONLY_RUN_SIMPLE_DELEGATION:
    exit(0)


def create_lodging_planner(llm: LLM) -> Agent:
    """创建专注于伦敦住宿的规划 Agent。"""
    skills = [
        Skill(
            name="lodging_planning",
            content=(
                "你专门寻找伦敦的优质住宿地点。"
                "提供 3-4 个酒店推荐，包括社区、快速的优缺点分析，"
                "以及交通便利性说明。按预算提供多样化的选择。"
            ),
            trigger=None,
        )
    ]
    return Agent(
        llm=llm,
        tools=[],
        agent_context=AgentContext(
            skills=skills,
            system_message_suffix="仅专注于伦敦住宿推荐。",
        ),
    )


def create_activities_planner(llm: LLM) -> Agent:
    """创建专注于伦敦行程的活动规划 Agent。"""
    skills = [
        Skill(
            name="activities_planning",
            content=(
                "你设计简洁的伦敦行程。建议每天 2-3 个亮点，"
                "按临近程度分组以减少旅行时间。"
                "包括美食/咖啡停留点，"
                "并注明所需门票/预订信息。"
            ),
            trigger=None,
        )
    ]
    return Agent(
        llm=llm,
        tools=[],
        agent_context=AgentContext(
            skills=skills,
            system_message_suffix="在伦敦规划实用、高效的一日行程。",
        ),
    )


# 注册用户自定义的 Agent 类型（默认 Agent 类型始终可用）
register_agent(
    name="lodging_planner",
    factory_func=create_lodging_planner,
    description="查找伦敦住宿选项，提供交通便利的推荐。",
)
register_agent(
    name="activities_planner",
    factory_func=create_activities_planner,
    description="创建高效的伦敦活动行程安排。",
)

# 使主 Agent 可以使用委托工具
register_tool("DelegateTool", DelegateTool)

main_agent = Agent(
    llm=llm,
    tools=[Tool(name="DelegateTool")],
)
conversation = Conversation(
    agent=main_agent,
    workspace=cwd,
    visualizer=DelegationVisualizer(name="Delegator"),
)

task_message = (
    "规划一次 3 天的伦敦之旅。"
    "1) 启动两个子 Agent：lodging_planner（酒店选项）和 "
    "activities_planner（行程安排）。"
    "2) 向 lodging_planner 询问 3-4 个伦敦市中心酒店推荐，包括 "
    "社区、快速优缺点分析、以及按预算的交通说明。"
    "3) 向 activities_planner 询问简洁的 3 天行程，包括附近停留点、"
    "   美食/咖啡建议，以及任何门票/预订说明。"
    "4) 分享两个子 Agent 的结果，并提出综合计划。"
)

print("=" * 100)
print("演示伦敦旅行委托（住宿 + 活动）...")
print("=" * 100)

conversation.send_message(task_message)
conversation.run()

conversation.send_message(
    "询问住宿子 Agent 对科文特花园的看法。"
)
conversation.run()

# 报告用户自定义 Agent 类型示例的成本
cost_2 = conversation.conversation_stats.get_combined_metrics().accumulated_cost
print(f"示例成本（用户自定义 Agent）: {cost_2}")

print("全部完成！")

# CI 工作流的完整示例成本报告
print(f"示例总成本: {cost_1 + cost_2}")