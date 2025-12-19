# OpenHands 技能库

[OpenHands](https://github.com/OpenHands/OpenHands) 的**技能（Skills）**公共注册表 - 可重用的指南，用于自定义代理行为。
查看[文档](https://docs.openhands.dev/overview/skills)了解更多信息。

> **注意**：技能以前称为 Microagents。`.openhands/microagents/` 文件夹路径仍然有效以保持向后兼容性。

## 什么是技能？

技能是包含指令和最佳实践的 Markdown 文件，用于指导 OpenHands 代理。它们提供领域专业知识（git、docker、kubernetes），编码最佳实践（代码审查、安全），并消除重复性指令。

## 技能类型

### 通用技能
始终作为上下文加载。不需要前言（frontmatter）。

```markdown
# 仓库指南
本项目使用 React 和 Node.js。运行 `npm install` 进行设置...
```

### 关键词触发技能
仅当用户提示中出现触发词时才加载。需要前言。

```markdown
---
triggers:
  - docker
  - dockerfile
---

# Docker 指南
使用 Docker 容器时...
```

## 贡献技能

要贡献技能：

1. Fork 本仓库
2. 在 `skills/` 目录添加 `.md` 文件
3. 对于关键词触发技能，在前言中包含 `triggers` 列表
4. 提交 Pull Request

**好的技能应该：**
- 具体且可操作
- 专注于单一领域或任务
- 包含具体示例
- 使用相关的触发关键词（针对关键词触发技能）

## 前言参考

**通用技能**：不需要前言

**关键词触发技能**：必需的前言
```yaml
---
triggers:
  - keyword1
  - keyword2
agent: CodeActAgent  # 可选，默认为 CodeActAgent
---
```

## 示例

查看 [`skills/`](skills/) 目录中的示例，如 [`github.md`](skills/github.md)、[`docker.md`](skills/docker.md)、[`code-review.md`](skills/code-review.md)。

## 了解更多

- [OpenHands 文档](https://docs.openhands.dev)
- [OpenHands 仓库](https://github.com/OpenHands/OpenHands)
- [软件代理 SDK](https://github.com/OpenHands/software-agent-sdk)
