#!/usr/bin/env python3
"""
迭代优化示例：COBOL 到 Java 重构

此示例演示了一个迭代优化工作流程：
1. 重构代理将 COBOL 文件转换为 Java 文件
2. 评审代理评估每次转换的质量并提供评分
3. 如果平均分低于 90%，则使用反馈重复该过程

工作流程将持续进行，直到重构达到质量阈值。

源 COBOL 文件可从以下位置获取：
https://github.com/aws-samples/aws-mainframe-modernization-carddemo/tree/main/app/cbl
"""

import os
import re
import tempfile
from pathlib import Path

from pydantic import SecretStr

from openhands.sdk import LLM, Conversation
from openhands.tools.preset.default import get_default_agent


QUALITY_THRESHOLD = float(os.getenv("QUALITY_THRESHOLD", "90.0"))
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "5"))


def setup_workspace() -> tuple[Path, Path, Path]:
    """为重构工作流程创建工作空间目录。"""
    workspace_dir = Path(tempfile.mkdtemp())
    cobol_dir = workspace_dir / "cobol"
    java_dir = workspace_dir / "java"
    critique_dir = workspace_dir / "critiques"

    cobol_dir.mkdir(parents=True, exist_ok=True)
    java_dir.mkdir(parents=True, exist_ok=True)
    critique_dir.mkdir(parents=True, exist_ok=True)

    return workspace_dir, cobol_dir, java_dir


def create_sample_cobol_files(cobol_dir: Path) -> list[str]:
    """创建示例 COBOL 文件用于演示。

    在实际场景中，您应该从以下位置克隆文件：
    https://github.com/aws-samples/aws-mainframe-modernization-carddemo/tree/main/app/cbl
    """
    sample_files = {
        "CBACT01C.cbl": """       IDENTIFICATION DIVISION.
       PROGRAM-ID. CBACT01C.
      *****************************************************************
      * Program: CBACT01C - Account Display Program
      * Purpose: Display account information for a given account number
      *****************************************************************
       ENVIRONMENT DIVISION.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-ACCOUNT-ID          PIC 9(11).
       01  WS-ACCOUNT-STATUS      PIC X(1).
       01  WS-ACCOUNT-BALANCE     PIC S9(13)V99.
       01  WS-CUSTOMER-NAME       PIC X(50).
       01  WS-ERROR-MSG           PIC X(80).

       PROCEDURE DIVISION.
           PERFORM 1000-INIT.
           PERFORM 2000-PROCESS.
           PERFORM 3000-TERMINATE.
           STOP RUN.

       1000-INIT.
           INITIALIZE WS-ACCOUNT-ID
           INITIALIZE WS-ACCOUNT-STATUS
           INITIALIZE WS-ACCOUNT-BALANCE
           INITIALIZE WS-CUSTOMER-NAME.

       2000-PROCESS.
           DISPLAY "ENTER ACCOUNT NUMBER: "
           ACCEPT WS-ACCOUNT-ID
           IF WS-ACCOUNT-ID = ZEROS
               MOVE "INVALID ACCOUNT NUMBER" TO WS-ERROR-MSG
               DISPLAY WS-ERROR-MSG
           ELSE
               DISPLAY "ACCOUNT: " WS-ACCOUNT-ID
               DISPLAY "STATUS: " WS-ACCOUNT-STATUS
               DISPLAY "BALANCE: " WS-ACCOUNT-BALANCE
           END-IF.

       3000-TERMINATE.
           DISPLAY "PROGRAM COMPLETE".
""",
        "CBCUS01C.cbl": """       IDENTIFICATION DIVISION.
       PROGRAM-ID. CBCUS01C.
      *****************************************************************
      * Program: CBCUS01C - Customer Information Program
      * Purpose: Manage customer data operations
      *****************************************************************
       ENVIRONMENT DIVISION.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-CUSTOMER-ID         PIC 9(9).
       01  WS-FIRST-NAME          PIC X(25).
       01  WS-LAST-NAME           PIC X(25).
       01  WS-ADDRESS             PIC X(100).
       01  WS-PHONE               PIC X(15).
       01  WS-EMAIL               PIC X(50).
       01  WS-OPERATION           PIC X(1).
           88 OP-ADD              VALUE 'A'.
           88 OP-UPDATE           VALUE 'U'.
           88 OP-DELETE           VALUE 'D'.
           88 OP-DISPLAY          VALUE 'V'.

       PROCEDURE DIVISION.
           PERFORM 1000-MAIN-PROCESS.
           STOP RUN.

       1000-MAIN-PROCESS.
           DISPLAY "CUSTOMER MANAGEMENT SYSTEM"
           DISPLAY "A-ADD U-UPDATE D-DELETE V-VIEW"
           ACCEPT WS-OPERATION
           EVALUATE TRUE
               WHEN OP-ADD
                   PERFORM 2000-ADD-CUSTOMER
               WHEN OP-UPDATE
                   PERFORM 3000-UPDATE-CUSTOMER
               WHEN OP-DELETE
                   PERFORM 4000-DELETE-CUSTOMER
               WHEN OP-DISPLAY
                   PERFORM 5000-DISPLAY-CUSTOMER
               WHEN OTHER
                   DISPLAY "INVALID OPERATION"
           END-EVALUATE.

       2000-ADD-CUSTOMER.
           DISPLAY "ADDING NEW CUSTOMER"
           ACCEPT WS-CUSTOMER-ID
           ACCEPT WS-FIRST-NAME
           ACCEPT WS-LAST-NAME
           DISPLAY "CUSTOMER ADDED: " WS-CUSTOMER-ID.

       3000-UPDATE-CUSTOMER.
           DISPLAY "UPDATING CUSTOMER"
           ACCEPT WS-CUSTOMER-ID
           DISPLAY "CUSTOMER UPDATED: " WS-CUSTOMER-ID.

       4000-DELETE-CUSTOMER.
           DISPLAY "DELETING CUSTOMER"
           ACCEPT WS-CUSTOMER-ID
           DISPLAY "CUSTOMER DELETED: " WS-CUSTOMER-ID.

       5000-DISPLAY-CUSTOMER.
           DISPLAY "DISPLAYING CUSTOMER"
           ACCEPT WS-CUSTOMER-ID
           DISPLAY "ID: " WS-CUSTOMER-ID
           DISPLAY "NAME: " WS-FIRST-NAME " " WS-LAST-NAME.
""",
        "CBTRN01C.cbl": """       IDENTIFICATION DIVISION.
       PROGRAM-ID. CBTRN01C.
      *****************************************************************
      * Program: CBTRN01C - Transaction Processing Program
      * Purpose: Process financial transactions
      *****************************************************************
       ENVIRONMENT DIVISION.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-TRANS-ID            PIC 9(16).
       01  WS-TRANS-TYPE          PIC X(2).
           88 TRANS-CREDIT        VALUE 'CR'.
           88 TRANS-DEBIT         VALUE 'DB'.
           88 TRANS-TRANSFER      VALUE 'TR'.
       01  WS-TRANS-AMOUNT        PIC S9(13)V99.
       01  WS-FROM-ACCOUNT        PIC 9(11).
       01  WS-TO-ACCOUNT          PIC 9(11).
       01  WS-TRANS-DATE          PIC 9(8).
       01  WS-TRANS-STATUS        PIC X(10).

       PROCEDURE DIVISION.
           PERFORM 1000-INITIALIZE.
           PERFORM 2000-PROCESS-TRANSACTION.
           PERFORM 3000-FINALIZE.
           STOP RUN.

       1000-INITIALIZE.
           MOVE ZEROS TO WS-TRANS-ID
           MOVE SPACES TO WS-TRANS-TYPE
           MOVE ZEROS TO WS-TRANS-AMOUNT
           MOVE "PENDING" TO WS-TRANS-STATUS.

       2000-PROCESS-TRANSACTION.
           DISPLAY "ENTER TRANSACTION TYPE (CR/DB/TR): "
           ACCEPT WS-TRANS-TYPE
           DISPLAY "ENTER AMOUNT: "
           ACCEPT WS-TRANS-AMOUNT
           EVALUATE TRUE
               WHEN TRANS-CREDIT
                   PERFORM 2100-PROCESS-CREDIT
               WHEN TRANS-DEBIT
                   PERFORM 2200-PROCESS-DEBIT
               WHEN TRANS-TRANSFER
                   PERFORM 2300-PROCESS-TRANSFER
               WHEN OTHER
                   MOVE "INVALID" TO WS-TRANS-STATUS
           END-EVALUATE.

       2100-PROCESS-CREDIT.
           DISPLAY "PROCESSING CREDIT"
           ACCEPT WS-TO-ACCOUNT
           MOVE "COMPLETED" TO WS-TRANS-STATUS
           DISPLAY "CREDIT APPLIED TO: " WS-TO-ACCOUNT.

       2200-PROCESS-DEBIT.
           DISPLAY "PROCESSING DEBIT"
           ACCEPT WS-FROM-ACCOUNT
           MOVE "COMPLETED" TO WS-TRANS-STATUS
           DISPLAY "DEBIT FROM: " WS-FROM-ACCOUNT.

       2300-PROCESS-TRANSFER.
           DISPLAY "PROCESSING TRANSFER"
           ACCEPT WS-FROM-ACCOUNT
           ACCEPT WS-TO-ACCOUNT
           MOVE "COMPLETED" TO WS-TRANS-STATUS
           DISPLAY "TRANSFER FROM " WS-FROM-ACCOUNT " TO " WS-TO-ACCOUNT.

       3000-FINALIZE.
           DISPLAY "TRANSACTION STATUS: " WS-TRANS-STATUS.
""",
    }

    created_files = []
    for filename, content in sample_files.items():
        file_path = cobol_dir / filename
        file_path.write_text(content)
        created_files.append(filename)

    return created_files


def get_refactoring_prompt(
    cobol_dir: Path,
    java_dir: Path,
    cobol_files: list[str],
    critique_file: Path | None = None,
) -> str:
    """生成重构代理的提示词。"""
    files_list = "\n".join(f"  - {f}" for f in cobol_files)

    base_prompt = f"""将以下 COBOL 文件转换为 Java：

COBOL 源目录：{cobol_dir}
Java 目标目录：{java_dir}

待转换文件：
{files_list}

要求：
1. 为每个 COBOL 程序创建一个 Java 类
2. 保留业务逻辑和数据结构
3. 使用适当的 Java 命名约定（方法使用 camelCase，类使用 PascalCase）
4. 将 COBOL 数据类型转换为适当的 Java 类型
5. 使用 try-catch 块实现适当的错误处理
6. 添加 JavaDoc 注释，解释每个类和方法的用途
7. 在 JavaDoc 注释中，使用以下格式包含对原始 COBOL 源代码的可追溯性：
   @source <程序名>:<行号>（例如：@source CBACT01C.cbl:73-77）
8. 创建简洁、可维护的面向对象设计
9. 每个 Java 文件都应该可编译并遵循 Java 最佳实践

读取每个 COBOL 文件并在目标目录中创建相应的 Java 文件。
"""

    if critique_file and critique_file.exists():
        base_prompt += f"""

重要提示：之前的重构尝试已被评估，需要改进。
请查看评审报告：{critique_file}
解决评审中提到的所有问题，以提高转换质量。
"""

    return base_prompt


def get_critique_prompt(
    cobol_dir: Path,
    java_dir: Path,
    cobol_files: list[str],
) -> str:
    """生成评审代理的提示词。"""
    files_list = "\n".join(f"  - {f}" for f in cobol_files)

    return f"""评估 COBOL 到 Java 重构的质量。

COBOL 源目录：{cobol_dir}
Java 目标目录：{java_dir}

原始 COBOL 文件：
{files_list}

请根据原始 COBOL 源代码评估每个转换后的 Java 文件。

对于每个文件，评估：
1. 正确性：Java 代码是否保留了原始业务逻辑？（0-25 分）
2. 代码质量：代码是否简洁、可读，遵循 Java 约定？（0-25 分）
3. 完整性：所有 COBOL 功能是否正确转换？（0-25 分）
4. 最佳实践：是否使用了适当的面向对象编程、错误处理、文档？（0-25 分）

按照以下准确格式创建评审报告：

# COBOL 到 Java 重构评审报告

## 总结
[简要的总体评估]

## 文件评估

### [原始 COBOL 文件名]
- **Java 文件**：[相应的 Java 文件名或 "未找到"]
- **正确性**：[得分]/25 - [简要说明]
- **代码质量**：[得分]/25 - [简要说明]
- **完整性**：[得分]/25 - [简要说明]
- **最佳实践**：[得分]/25 - [简要说明]
- **文件得分**：[总分]/100
- **需要解决的问题**：
  - [具体问题 1]
  - [具体问题 2]
  ...

[为每个文件重复]

## 总体得分
- **平均得分**：[所有文件得分的计算平均值]
- **建议**：[如果平均分 >= 90 则通过，否则需要改进]

## 优先改进项
1. [最关键的改进需求]
2. [第二优先级]
3. [第三优先级]

将此报告保存到：{java_dir.parent}/critiques/critique_report.md
"""


def parse_critique_score(critique_file: Path) -> float:
    """从评审报告中解析平均分。"""
    if not critique_file.exists():
        return 0.0

    content = critique_file.read_text()

    # 查找 "平均得分: X" 或 "Average Score: X" 模式
    patterns = [
        r"\*\*平均得分\*\*[：:]\s*(\d+(?:\.\d+)?)",
        r"平均得分[：:]\s*(\d+(?:\.\d+)?)",
        r"\*\*Average Score\*\*:\s*(\d+(?:\.\d+)?)",
        r"Average Score:\s*(\d+(?:\.\d+)?)",
        r"average.*?(\d+(?:\.\d+)?)\s*(?:/100|%|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return float(match.group(1))

    return 0.0


def run_iterative_refinement() -> None:
    """运行迭代优化工作流程。"""
    # 设置
    api_key = os.getenv("LLM_API_KEY", "sk-5a839dbb64074a62a1a78e9cb6502bef")
    assert api_key is not None, "LLM_API_KEY 环境变量未设置。"
    model = os.getenv("LLM_MODEL", "openai/qwen3-coder-plus")
    base_url = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    llm = LLM(
        model=model,
        base_url=base_url,
        api_key=SecretStr(api_key),
        usage_id="iterative_refinement",
    )

    workspace_dir, cobol_dir, java_dir = setup_workspace()
    critique_dir = workspace_dir / "critiques"

    print(f"工作空间：{workspace_dir}")
    print(f"COBOL 目录：{cobol_dir}")
    print(f"Java 目录：{java_dir}")
    print(f"评审目录：{critique_dir}")
    print()

    # 创建示例 COBOL 文件
    cobol_files = create_sample_cobol_files(cobol_dir)
    print(f"已创建 {len(cobol_files)} 个示例 COBOL 文件：")
    for f in cobol_files:
        print(f"  - {f}")
    print()

    critique_file = critique_dir / "critique_report.md"
    current_score = 0.0
    iteration = 0

    while current_score < QUALITY_THRESHOLD and iteration < MAX_ITERATIONS:
        iteration += 1
        print("=" * 80)
        print(f"迭代 {iteration}")
        print("=" * 80)

        # 阶段 1：重构
        print("\n--- 阶段 1：重构代理 ---")
        refactoring_agent = get_default_agent(llm=llm, cli_mode=True)
        refactoring_conversation = Conversation(
            agent=refactoring_agent,
            workspace=str(workspace_dir),
        )

        previous_critique = critique_file if iteration > 1 else None
        refactoring_prompt = get_refactoring_prompt(
            cobol_dir, java_dir, cobol_files, previous_critique
        )

        refactoring_conversation.send_message(refactoring_prompt)
        refactoring_conversation.run()
        print("重构阶段完成。")

        # 阶段 2：评审
        print("\n--- 阶段 2：评审代理 ---")
        critique_agent = get_default_agent(llm=llm, cli_mode=True)
        critique_conversation = Conversation(
            agent=critique_agent,
            workspace=str(workspace_dir),
        )

        critique_prompt = get_critique_prompt(cobol_dir, java_dir, cobol_files)
        critique_conversation.send_message(critique_prompt)
        critique_conversation.run()
        print("评审阶段完成。")

        # 解析得分
        current_score = parse_critique_score(critique_file)
        print(f"\n当前得分：{current_score:.1f}%")

        if current_score >= QUALITY_THRESHOLD:
            print(f"\n✓ 达到质量阈值（{QUALITY_THRESHOLD}%）！")
        else:
            print(
                f"\n✗ 得分低于阈值（{QUALITY_THRESHOLD}%）。"
                "继续优化..."
            )

    # 最终摘要
    print("\n" + "=" * 80)
    print("迭代优化完成")
    print("=" * 80)
    print(f"总迭代次数：{iteration}")
    print(f"最终得分：{current_score:.1f}%")
    print(f"工作空间：{workspace_dir}")

    # 列出创建的 Java 文件
    print("\n已创建的 Java 文件：")
    for java_file in java_dir.glob("*.java"):
        print(f"  - {java_file.name}")

    # 显示评审文件位置
    if critique_file.exists():
        print(f"\n最终评审报告：{critique_file}")

    # 报告成本
    cost = llm.metrics.accumulated_cost
    print(f"\n示例成本：{cost}")


if __name__ == "__main__":
    run_iterative_refinement()
