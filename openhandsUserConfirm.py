"""OpenHands Agent SDK — 确认模式示例"""

import os
import signal
import sys
from collections.abc import Callable

from pydantic import SecretStr

from openhands.sdk import LLM, BaseConversation, Conversation
from openhands.sdk.conversation.state import (
    ConversationExecutionStatus,
    ConversationState,
)
from openhands.sdk.security.confirmation_policy import AlwaysConfirm, NeverConfirm
from openhands.sdk.security.llm_analyzer import LLMSecurityAnalyzer
from openhands.tools.preset.default import get_default_agent


# 使 ^C 干净退出而不是显示堆栈跟踪
signal.signal(signal.SIGINT, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))


def _print_action_preview(pending_actions) -> None:
    print(f"\n🔍 代理创建了 {len(pending_actions)} 个等待确认的操作：")
    for i, action in enumerate(pending_actions, start=1):
        snippet = str(action.action)[:100].replace("\n", " ")
        print(f"  {i}. {action.tool_name}: {snippet}...")


def confirm_in_console(pending_actions) -> bool:
    """
    使用直接读取方式，避免 PyCharm Console 自动补全干扰。
    返回 True 表示批准，False 表示拒绝。
    """
    _print_action_preview(pending_actions)
    
    print("\n" + "="*60)
    print("请选择操作:")
    print("  输入 1 或 y 或 yes - 批准执行")
    print("  输入 0 或 n 或 no  - 拒绝执行")
    print("="*60)
    
    while True:
        try:
            # 使用 sys.stdin.readline() 直接读取，避免 input() 的问题
            sys.stdout.write("\n请输入你的选择: ")
            sys.stdout.flush()
            ans = sys.stdin.readline().strip().lower()
            
            if not ans:  # 空输入
                print("❌ 输入为空，请重新输入")
                continue
                
            print(f"[接收] 你输入了: {ans}")
            
            # 批准
            if ans in ("1", "y", "yes", "是", "好"):
                print("\n✅ 已批准 — 正在执行操作…\n")
                return True
            # 拒绝
            elif ans in ("0", "n", "no", "否", "不"):
                print("\n❌ 已拒绝 — 跳过操作…\n")
                return False
            else:
                print(f"❌ 无效输入: '{ans}'，请输入 1/y/yes 或 0/n/no")
                
        except (EOFError, KeyboardInterrupt):
            print("\n❌ 操作被中断，默认拒绝。")
            return False


def run_until_finished(conversation: BaseConversation, confirmer: Callable) -> None:
    """
    驱动对话直到完成。
    如果处于 WAITING_FOR_CONFIRMATION 状态，询问确认者；
    拒绝时，调用 reject_pending_actions()。
    如果代理等待但不存在操作，则保留原始错误。
    """
    while conversation.state.execution_status != ConversationExecutionStatus.FINISHED:
        if (
            conversation.state.execution_status
            == ConversationExecutionStatus.WAITING_FOR_CONFIRMATION
        ):
            pending = ConversationState.get_unmatched_actions(conversation.state.events)
            if not pending:
                raise RuntimeError(
                    "⚠️ 代理正在等待确认，但未找到待处理的操作。"
                    "这不应该发生。"
                )
            if not confirmer(pending):
                conversation.reject_pending_actions("用户拒绝了这些操作")
                # 让代理产生新的步骤或完成
                continue

        print("▶️  正在运行 conversation.run()…")
        conversation.run()


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

agent = get_default_agent(llm=llm)
conversation = Conversation(agent=agent, workspace=os.getcwd())

# 根据环境变量有条件地添加安全分析器
add_security_analyzer = bool(os.getenv("ADD_SECURITY_ANALYZER", "").strip())
if add_security_analyzer:
    print("已添加代理安全分析器。")
    conversation.set_security_analyzer(LLMSecurityAnalyzer())

# 1) 确认模式开启   （演示需要操作）
conversation.set_confirmation_policy(AlwaysConfirm())
print(" 用例1.可能会创建操作的命令…")
conversation.send_message("请使用 ls -la 列出当前目录中的文件")
run_until_finished(conversation, confirm_in_console)

# 2) 用户可能选择拒绝的命令 （演示需要操作）
print(" 用例2.用户可能选择拒绝的命令…")
conversation.send_message("请创建一个名为 'dangerous_file.txt' 的文件")
run_until_finished(conversation, confirm_in_console)

# 3) 简单问候（演示不需要用户有操作）
print(" 用例3.简单问候（不期望有操作）…")
conversation.send_message("跟我打个招呼吧")
run_until_finished(conversation, confirm_in_console)

# 4) 禁用确认模式并直接运行命令 （演示不需要用户有操作）
print(" 用例4.禁用确认模式并运行命令…")
conversation.set_confirmation_policy(NeverConfirm())
conversation.send_message("请回显 '来自确认模式示例的问候！'")
conversation.run()

conversation.send_message(
    "请删除在此对话期间创建的任何文件。"
)
conversation.run()

print("\n=== 示例完成 ===")
print("要点：")
print(
    "- conversation.run() 创建操作；确认模式 "
    "设置 execution_status=WAITING_FOR_CONFIRMATION"
)
print("- 用户确认通过单个可重用函数处理")
print("- 拒绝使用 conversation.reject_pending_actions()，循环继续")
print("- 简单响应在没有操作的情况下正常工作")
print("- 确认策略通过 conversation.set_confirmation_policy() 切换")