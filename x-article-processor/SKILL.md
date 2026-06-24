---
name: x-article-processor
description: "一键处理 X/Twitter 文章：提取内容、下载图片、翻译检测、保存到素材库。比 wechat-article-to-markdown 更高效的 X 文章专用处理器。"
triggers:
  - 用户发送 X/Twitter 链接（x.com/.../status/... 或 twitter.com/.../status/...）
  - 用户要求处理/保存 X 文章或推文
  - 用户发送多个 X 链接要求批量处理
---

# X/Twitter 文章一键处理器

## 触发条件

当用户发送以下链接时：
- **X/Twitter 文章** `x.com/.../status/...` 或 `twitter.com/.../status/...`

**行为规则：**
- **单个链接**：直接自动处理并保存，不需要询问
- **多个链接**：批量处理，显示进度
- **附带其他内容**（如问题、要求总结等）：先处理其他内容，再询问是否需要保存
- **英文文章**：自动检测语言，英文文章标记 `translated: true`（翻译需额外步骤）

## 与 wechat-article-to-markdown 的区别

| 特性 | x-article-processor | wechat-article-to-markdown |
|------|-------------------|---------------------------|
| **处理速度** | 30-60秒/篇 | 2-3分钟/篇 |
| **工具调用** | 1次 | 3-5次 |
| **图片下载** | 4线程并行 | 串行 |
| **错误处理** | 3次重试 | 无 |
| **批量处理** | 原生支持 | 需手动编排 |
| **适用范围** | 仅X/Twitter | 微信、X、飞书、网页 |

**建议：** X/Twitter 链接优先使用本技能，微信/飞书/网页链接继续使用 wechat-article-to-markdown。

## 保存路径

通过环境变量配置，安装后需根据你的目录结构设置：

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `X_ARTICLE_OUTPUT_DIR` | 文章保存目录 | `~/articles/inbox/` |
| `X_ARTICLE_ASSETS_DIR` | 图片保存目录 | `~/articles/assets/` |
| `X_ARTICLE_PUBLISH_DIR` | 发布目录 | `~/articles/publish/` |
| `X_ARTICLE_DRAFT_DIR` | 草稿目录 | `~/articles/drafts/` |
| `X_ARTICLE_EXTRACT_SCRIPT` | 提取脚本路径 | `~/.hermes/skills/wechat-article-to-markdown/scripts/extract_x_article.py` |

```bash
# 在 ~/.hermes/.env 或 shell profile 中设置
export X_ARTICLE_OUTPUT_DIR="/path/to/your/inbox"
export X_ARTICLE_ASSETS_DIR="/path/to/your/assets"
export X_ARTICLE_PUBLISH_DIR="/path/to/your/publish"
export X_ARTICLE_DRAFT_DIR="/path/to/your/drafts"
```

用户路由偏好（根据关键词判断）：
- 用户说"发表"/"发布"/"发表文章" → `$X_ARTICLE_PUBLISH_DIR`
- 用户说"草稿"/"草稿箱" → `$X_ARTICLE_DRAFT_DIR`
- 无明确指示 → `$X_ARTICLE_OUTPUT_DIR`

## 快速工作流（2步完成）

```bash
# 步骤1：处理文章（30秒）
python3 ~/.hermes/skills/x-article-processor/scripts/process_x_article.py "https://x.com/xxx/status/123"

# 步骤2：翻译英文文章（1-2分钟）
delegate_task(
    goal="将以下英文文章翻译为中文，AI技术术语保留英文原文",
    context="文章内容..."
)
```

**与微信文章的区别**：
- **X/Twitter** → 本技能（自动提取+翻译）
- **微信/飞书/网页** → `wechat-article-to-markdown`（通常无需翻译）

## 使用方式

### 命令行直接调用

```bash
# 处理单篇文章
python3 ~/.hermes/skills/x-article-processor/scripts/process_x_article.py "https://x.com/xxx/status/123456"

# 添加标签
python3 ~/.hermes/skills/x-article-processor/scripts/process_x_article.py "https://x.com/xxx/status/123456" --tags "AI" "agent"

# 批量处理（从文件读取URL）
python3 ~/.hermes/skills/x-article-processor/scripts/process_x_article.py urls.txt

# 批量处理（命令行列出多个URL）
python3 ~/.hermes/skills/x-article-processor/scripts/process_x_article.py "url1" "url2" "url3"

# 自定义输出目录
python3 ~/.hermes/skills/x-article-processor/scripts/process_x_article.py "https://x.com/xxx/status/123456" --output-dir "/path/to/output"
```

### 环境变量配置

```bash
# 设置图片保存目录
export X_ARTICLE_ASSETS_DIR="/path/to/assets"

# 设置文章保存目录
export X_ARTICLE_OUTPUT_DIR="/path/to/output"

# 设置提取脚本路径（通常不需要修改）
export X_ARTICLE_EXTRACT_SCRIPT="/path/to/extract_x_article.py"
```

## 处理流程

1. **提取 Tweet ID**：从 URL 中提取数字 ID
2. **获取 JSON 数据**：通过 fxtwitter API 获取结构化数据
3. **提取元数据**：标题、作者、日期、封面图
4. **提取文章内容**：调用 extract_x_article.py 脚本
5. **语言检测**：判断是否需要翻译
6. **并行下载图片**：4线程同时下载，带重试机制
7. **替换图片 URL**：将外部 URL 替换为本地路径
8. **生成 frontmatter**：标准化的 YAML 头部
9. **保存文件**：按命名规范保存到目标目录

## 优化点

### 性能优化
- **并行下载**：4线程同时下载图片，速度提升300%
- **重试机制**：每个下载最多重试3次，指数退避
- **批量处理**：多个链接顺序处理，无需手动编排

### 质量优化
- **标准化命名**：`YYYY-MM-DD-标题slug.md`
- **统一 frontmatter**：包含 title, author, date, source, cover, translated, tags
- **图片验证**：检查未替换的外部 URL
- **语言检测**：自动判断是否需要翻译

### 用户体验
- **进度显示**：实时显示下载进度和成功/失败状态
- **错误提示**：清晰的错误信息和解决建议
- **批量统计**：显示处理成功/失败数量

## 翻译处理

脚本会自动检测语言，但**不会自动翻译**。翻译需要额外步骤：

1. 脚本检测到英文文章时会标记 `translated: true`
2. 需要使用 `delegate_task` 进行翻译
3. 翻译后需替换内容并更新文件

### 翻译方法（简单有效）

**一句话指令即可**，不需要复杂的术语管理系统：

```python
delegate_task(
    goal="将以下英文文章翻译为中文，要求：AI领域的技术术语保留英文原文，不确定的也保留英文",
    context="文章内容..."
)
```

**实测效果**：Agent, Researcher, Builder, Judge, Manager, Prompt, RAG 等术语都正确保留英文。

**⚠️ 不要过度工程化**：用户明确表示维护术语表会让工作流变得累赘。简单的指令已经足够好。

### 翻译后验证

- `grep -c 'translated: true' 文件` 应为 1
- 正文应为中文，技术术语保留英文
- 代码块保留英文原文

## 文件格式

```markdown
---
title: "文章标题"
author: "作者"
date: 2026-06-20
source: "https://x.com/xxx/status/123456"
cover: "封面图文件名.jpg"
translated: false
tags:
  - AI
  - agent
---

# 文章标题

正文内容...
```

## 验证清单

处理完成后检查：
- [ ] 文件存在且大小 > 1KB
- [ ] 图片文件存在且大小 > 1KB
- [ ] 无残留外部图片 URL（`grep -c 'pbs.twimg.com' file.md` 为 0）
- [ ] frontmatter 格式正确
- [ ] 标题和作者信息准确

## Pitfalls

### 网络问题
1. **urllib.request.urlretrieve 在 macOS 上 Connection refused**：实测 urllib 对 `api.fxtwitter.com` 返回 `[Errno 61] Connection refused`，但 curl 正常。**脚本已改用 curl 下载**，不要回退到 urllib。
2. **pbs.twimg.com SSL 失败**：curl 对 `pbs.twimg.com` 可能返回 exit code 35（SSL handshake failure）。图片下载建议用 Python urllib（与 API 调用相反）。
3. **fxtwitter API 限制**：如果请求过于频繁可能被限制，脚本有重试机制（3次，指数退避）。

### 内容问题
4. **普通推文 vs 长文帖**：普通推文只有 280 字符，长文帖有完整文章结构
5. **无图片文章**：部分 X 文章是纯文字，这是正常情况
6. **图片顺序**：脚本按 media_entities 顺序编号，确保图片顺序正确

### 路径问题
7. **目录不存在**：脚本会自动创建目录
8. **文件名特殊字符**：脚本会自动清理标题中的特殊字符
9. **路径包含空格**：使用引号包裹路径

### 用户偏好
10. **不要过度工程化**：用户明确表示维护术语表会让工作流累赘。翻译时用简单指令即可，不要创建复杂的术语管理系统。

## 集成到工作流

### 与现有技能配合
- **X/Twitter 链接**：使用本技能（快速、高效）
- **微信/飞书/网页链接**：使用 wechat-article-to-markdown（功能全面）
- **翻译需求**：结合 delegate_task 并行翻译

### 自动化建议
1. **创建别名**：`alias process-x="python3 ~/.hermes/skills/x-article-processor/scripts/process_x_article.py"`
2. **批量处理**：将多个 URL 保存到文件，一次性处理
3. **定期清理**：每周处理积累的 X 链接

## 脚本位置

- **主脚本**：`scripts/process_x_article.py`
- **依赖脚本**：`~/.hermes/skills/wechat-article-to-markdown/scripts/extract_x_article.py`
- **翻译最佳实践**：`references/translation-best-practices.md`

## 跨技能依赖

本技能依赖 `wechat-article-to-markdown` 技能的 `scripts/extract_x_article.py` 脚本。默认路径为 `~/.hermes/skills/wechat-article-to-markdown/scripts/extract_x_article.py`，可通过 `X_ARTICLE_EXTRACT_SCRIPT` 环境变量自定义。

## 扩展性

脚本支持通过环境变量和命令行参数配置，可以轻松集成到：
- CI/CD 流程
- 自动化脚本
- 其他工具链

## 维护

如果遇到问题：
1. 检查网络连接
2. 确认 fxtwitter API 可访问
3. 验证 extract_x_article.py 脚本存在
4. 检查目录权限