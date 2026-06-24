# Translation Best Practices for AI Content

## Core Principle: Keep It Simple

**User preference**: Do NOT over-engineer terminology management. A simple one-line instruction is sufficient.

❌ **Don't do this**:
- Maintain a static glossary.json
- Run learning scripts to extract terms
- Build complex terminology management systems

✅ **Do this instead**:
```
delegate_task(
    goal="翻译文章，AI技术术语保留英文原文",
    context="文章内容..."
)
```

## Why Simple Works

1. **delegate_task already knows AI terms**: The model (mimo-v2.5-pro) is familiar with LLM, Agent, RAG, Token, etc.
2. **Conservative principle works**: "不确定的保留英文" lets the model make good judgments
3. **User feedback is easy**: If a term is mistranslated, just tell the model once

## Tested and Verified

**Test case 1**: "How to Build a Multi-Agent System That Actually Finishes the Job"
- Date: 2026-06-20
- Result: All terms preserved (Agent, Researcher, Builder, Judge, Manager, Prompt, RAG)
- Translation time: ~110 seconds

**Test case 2**: "How to Build a GTM Team on Claude Code You Can Run Alone"
- Date: 2026-06-20
- Result: All terms preserved (GTM, Agent, Claude Code, Pipeline, API, ICP, cron, standup, no-show, Overloop AI, LinkedIn)
- Translation time: ~63 seconds

## Translation Instruction Template

```
将以下英文文章翻译为中文，要求：
1. AI领域的技术术语保留英文原文（如：Agent, LLM, RAG, Token等）
2. 不确定的技术术语也保留英文，不要强行翻译
3. 保留所有Markdown格式（标题、加粗、列表、代码块）
4. 代码块、命令、变量名保留英文
5. 图片引用保持不变
```

## Post-Translation Checklist

- [ ] `translated: true` in frontmatter
- [ ] Technical terms in English
- [ ] Code blocks unchanged
- [ ] Image references intact
- [ ] Chinese text reads naturally

## User Feedback Loop

If user reports a mistranslation:
1. Note the term
2. Add it to the instruction for that specific article
3. Don't create a global glossary

Example: "Agentic Loop 被错误翻译了" → Add "Agentic Loop 保留英文" to next instruction
