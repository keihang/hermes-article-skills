---
name: wechat-article-to-markdown
description: "网页文章、微信公众号文章、飞书文档抓取并转换为 Markdown 文件，保留图片、表格、链接等完整内容。触发词：发送微信/飞书链接、grab article、save as md、convert to markdown"
triggers:
  - 用户发送微信公众号文章链接（mp.weixin.qq.com/s/...）
  - 用户发送飞书文档/Wiki链接（*.feishu.cn/wiki/... 或 *.feishu.cn/docx/...，包括自定义域名如 waytoagi.feishu.cn）
  - 用户要求抓取/保存微信文章
  - 用户分享网页链接要求转为 Markdown  - grab this article / save as md / convert to markdown
---

# 微信公众号文章转 Markdown

## 触发条件

当用户发送以下链接时：
- **微信文章** `mp.weixin.qq.com/s/...`
- **飞书文档/Wiki** `*.feishu.cn/wiki/...` 或 `*.feishu.cn/docx/...`（包括自定义子域名如 `waytoagi.feishu.cn`）

行为规则：
- **如果没有附带其他内容**，直接自动转换并保存，不需要询问
- **如果附带了其他内容**（比如问问题、要求总结等），先处理其他内容，再询问是否需要保存

> 🔴 **CHECKPOINT：链接附带其他内容时，必须先完成其他请求，再询问是否保存。不可跳过用户意图判断。**
- **如果内容是英文或其他非中文语言**，先翻译正文为中文再保存（代码块、提示词、命令等技术内容保留英文原文）。翻译后的文章在 frontmatter 加 `translated: true` 字段。用户明确说"翻译后存"或内容明显是英文时自动执行，不需要询问。

> ⚠️ **翻译是必选步骤，不是可选步骤。** 提取内容后必须先判断语言，英文内容必须翻译再保存。不要跳过这一步。详见下方"语言检测与翻译"章节。

## 保存路径

通过环境变量配置，安装后需根据你的目录结构设置：

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `ARTICLE_OUTPUT_DIR` | 文章保存目录 | `~/articles/inbox/` |
| `ARTICLE_ASSETS_DIR` | 图片保存目录 | `~/articles/assets/` |
| `ARTICLE_PUBLISH_DIR` | 发布目录 | `~/articles/publish/` |
| `ARTICLE_DRAFT_DIR` | 草稿目录 | `~/articles/drafts/` |

```bash
# 在 ~/.hermes/.env 或 shell profile 中设置
export ARTICLE_OUTPUT_DIR="/path/to/your/inbox"
export ARTICLE_ASSETS_DIR="/path/to/your/assets"
export ARTICLE_PUBLISH_DIR="/path/to/your/publish"
export ARTICLE_DRAFT_DIR="/path/to/your/drafts"
```

用户路由偏好（根据关键词判断）：
- 用户说"发表"/"发布"/"发表文章" → `$ARTICLE_PUBLISH_DIR`
- 用户说"草稿"/"草稿箱" → `$ARTICLE_DRAFT_DIR`
- 无明确指示 → `$ARTICLE_OUTPUT_DIR`

## 转换要求

**必须保留所有元素：**
- 🖼️ 图片（从 `data-src` 提取真实 URL）
- 🔗 链接（转为 `[text](url)` 格式）
- 📊 表格（转为 Markdown 表格格式）
- 代码块、列表、引用等

## 语言检测与翻译（必选步骤）

> ⚠️ **每次处理都必须执行此步骤，在组装文件和写盘之前。**

### 判断方法

- 标题含英文单词、正文首段是英文 → 英文文章，必须翻译
- 正文含大量中文 → 中文文章，跳过翻译
- 不确定时读前 5 行判断

> 🔴 **CHECKPOINT：语言判断决定后续流程分支。判断为英文后必须执行翻译，不可跳过。**

### 翻译要求

- 正文翻译为中文，**保留所有 markdown 格式**（标题、加粗、列表、链接）
- **代码块、提示词、命令、变量名、API 名称等技术内容保留英文原文**
- 图片注释翻译为中文
- frontmatter 中 `translated: true`
- frontmatter 的 `title` 字段保留英文原标题（不翻译标题）

### 翻译方式

**简化方法（推荐，已验证）**：一句话指令，不需要维护术语表：

```python
delegate_task(
    goal="将以下英文文章翻译为中文，要求：AI领域的技术术语保留英文原文，不确定的也保留英文",
    context="文章内容..."
)
```

实测效果：Agent, RAG, Prompt, Token, Context Window 等术语都正确保留英文。用户明确表示不要过度工程化（维护术语表会让工作流累赘）。

**⚠️ 关键坑：delegate_task 返回的翻译内容中图片仍是原始外部 URL，必须在组装阶段替换为本地路径。** 不要忘了这一步。

**微信公众号文章的翻译流程：**
用相同的 delegate_task 模式，但图片 URL 替换逻辑不同（mmbiz.qpic.cn → ../assets/）。

### 验证

翻译完成后检查：
- `grep -c 'translated: true' 文件` → 应为 1
- 正文是否为中文（读前 10 行确认）
- 代码块是否保留英文原文

## 转换流程

### Step 1: 下载 HTML

```bash
curl -sL -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" "URL" -o /tmp/wechat_article.html
```

### Step 2: 提取元数据（用 grep/sed，不用 Python）

微信文章 HTML 通常 3MB+，内联 Python 会 timeout。元数据用 shell 提取。

**注意：微信文章的 HTML 结构不统一，必须准备 fallback 链。**

```bash
# === 标题（按优先级尝试）===
# 方法1: js_title_inner
sed -n '/activity-name/,/<\/h1>/p' /tmp/wechat_article.html | grep 'js_title_inner' | sed 's/.*>//;s/<.*//' | head -1
# 方法2: msg_title JS 变量
grep -o 'var msg_title = "[^"]*"' /tmp/wechat_article.html | sed 's/var msg_title = "//;s/"$//'
# 方法3: og:title meta 标签
grep -o 'og:title" content="[^"]*"' /tmp/wechat_article.html | sed 's/.*content="//;s/"//'

# === 作者（按优先级尝试）===
# 方法1: js_author_name_text
sed -n '/js_author_name_text/p' /tmp/wechat_article.html | sed 's/.*>//;s/<.*//' | tr -d ' \t'
# 方法2: nickname JS 变量
grep -o 'var nickname = "[^"]*"' /tmp/wechat_article.html | sed 's/var nickname = "//;s/"$//'
# 方法3: og:article:author meta 标签
grep -o 'og:article:author" content="[^"]*"' /tmp/wechat_article.html | sed 's/.*content="//;s/"//'

# === 时间戳 ===
# var ct = "1777778841"
grep -o 'var ct = "[0-9]*"' /tmp/wechat_article.html | grep -o '[0-9]*'
# 然后用 date -r <ts> '+%Y-%m-%d %H:%M:%S' 转换（macOS）
```

### Step 3: 写 Python 脚本到文件再执行

**关键：不要用 `python3 -c "..."` 内联执行，3MB+ HTML 会导致 timeout。**

将提取脚本写入 `/tmp/extract_wechat.py`，然后 `python3 /tmp/extract_wechat.py > /tmp/wechat_content.md`。

**重要：先检测 HTML 格式，再选择脚本。** 部分新文章使用 Shadow DOM，需用 `extract_shadow_dom.py`。如果传统脚本报错 `Could not find js_content`，回退到 Shadow DOM 脚本。详见 Pitfalls 第 0 条。

脚本应包含以下处理逻辑（详见 `scripts/extract_wechat.py`）：
- 定位 `id="js_content"` 到 `class="rich_media_tool"` 之间的内容
- 图片：从 `data-src` 提取真实 URL
- 链接：转 `[text](url)`
- 标题/加粗/斜体/列表/引用/代码块
- **后处理**：去除尾部 JS 代码、清理多余空行

### Step 4: 后处理清理

提取后的内容通常有噪音，需要清理：

```bash
# 去除尾部从 "var first_sceen__time" 开始的 JS 代码和无关内容
# 去除开头的 CSS style 属性残留
# 合并连续空行为最多两个
```

### Step 5: 组装最终文件

按下方文件格式组装 frontmatter + 正文内容，保存到目标路径。

## 文件命名

统一格式：`YYYY-MM-DD-标题slug.md`

- 日期取保存当天日期（即 ingest 日期）
- slug：中文标题转拼音或直接用中文，去除特殊字符，空格用 `-` 连接
- 示例：`2026-06-02-codex接入deepseek完全指南.md`

## 文件格式

```markdown
---
title: "文章标题"
author: "作者"
date: YYYY-MM-DD HH:MM:SS
source: "https://mp.weixin.qq.com/s/..."  # ← 必须填实际 URL
---
```

**注意：`source` 字段必须填原始文章 URL，不要写死 `"微信公众号"`。** URL 是溯源的关键信息。
# 文章标题

正文内容...
```

## 脚本

- `scripts/extract_wechat.py` — 从下载的 HTML 中提取正文并转 Markdown 的 Python 脚本

## Pitfalls

### 特殊HTML结构

0. **Shadow DOM 文章**：部分微信文章使用 Shadow DOM，`extract_wechat.py` 脚本会报 `ERROR: Could not find js_content`。此时内容在 JavaScript 变量 `content: '...'` 中，用 `\x0a` 分隔段落。解决方案：
```python
import re, html as html_module
with open('/tmp/wechat_article.html', 'r') as f:
    content = f.read()
pattern = r"content:\s*[\'\"](.+?)[\'\"]"
matches = re.findall(pattern, content, re.DOTALL)
longest = max(matches, key=len)
decoded = longest.replace('\\x0a', '\n').replace('\\x09', '\t')
decoded = html_module.unescape(decoded)
```
判断方法：如果 `grep 'js_content' /tmp/wechat_article.html` 无结果，且 `grep 'shadow' /tmp/wechat_article.html` 有结果，则为 Shadow DOM 文章。

### 网络与环境

0. **/tmp 下的脚本会被清理**：macOS 会定期清理 /tmp 目录。如果 cp 到 /tmp/extract_wechat.py 报 "No such file or directory"，直接用 skill 目录下的原版脚本：`python3 ~/.hermes/skills/wechat-article-to-markdown/scripts/extract_wechat.py /tmp/wechat_article.html`。不要重复 cp，直接调源路径即可。
00. **需要代理**：当前环境下载微信文章需要代理，curl 必须加 `--proxy http://127.0.0.1:7890`。不加代理会 timeout（exit code 28）。

### 微信文章

0. **Shadow DOM 新格式**：2025年起部分微信文章使用 Shadow DOM 渲染，`js_content` div 不存在。症状：`extract_wechat.py` 报 `ERROR: Could not find js_content`。解决方案：检测 HTML 是否含 `shadow` 关键字且无 `id="js_content"` div，若有则使用 `scripts/extract_shadow_dom.py` 提取。内容通常在 JS 变量 `content:` 字段中，使用 `\x0a` 作为换行符。详见 `references/shadow-dom-format.md`。
1. **Python timeout**：微信文章 HTML 通常 3-4MB，内联 `python3 -c "..."` 会 timeout。必须将脚本写入文件再执行。
2. **curl 下载超时**：国内网络环境下 curl 直连微信 CDN 可能超时（exit code 28）。需加 `--proxy http://127.0.0.1:7890` 走本地代理。如果仍失败，加大 `--max-time 60`。
3. **macOS grep 不支持 -P**：不能用 `grep -oP`，用 `grep -o` 配合 `sed` 替代。
3. **尾部噪音**：提取的内容末尾通常包含 `var first_sceen__time` 等 JS 代码和 "预览时标签不可点" 等无关文本，必须在后处理中截断。
4. **开头噪音**：`js_content` div 的 `style` 属性有时会残留在正文开头。
5. **代码块格式**：微信文章的 `<pre><code>` 块内可能有嵌套 `<span>`（语法高亮），转换时需先去除 span 标签再提取纯文本。
6. **内联代码 vs 围栏代码**：微信文章通常不区分，提取脚本需根据上下文（是否在 `<pre>` 内）决定用 `` ` `` 还是 ` ``` `。
7. **空列表项残留**：微信 HTML 中 `<ul>` 嵌套 `<li>` 有时会产生孤立的 `- ` 行（无文本内容）。后处理时用 `re.sub(r'^- \s*$', '', line)` 或逐行过滤清理。
8. **元数据提取不稳定**：不同公众号的 HTML 结构差异大，标准 `js_title_inner` / `js_author_name_text` 经常匹配失败（实测 og:title / og:article:author 的 meta 标签反而是最可靠的来源）。必须按 fallback 链依次尝试（见 Step 2）。如果所有方法都失败，标题/作者设为"未知"，不要阻塞流程。
8. **批量处理用 delegate_task**：多个文章链接时，用 delegate_task 并行处理比逐个执行效率高得多。每个子任务的指令要包含完整的 fallback 元数据提取步骤。
9. **标题含引号导致 SyntaxError**：微信标题常含中文引号（`"`、`"`），直接拼入 Python f-string 会报 `SyntaxError: invalid syntax`。用 `title.replace('"', '\\"')` 转义后再拼入 f-string 的 `"""` 区域，或改用单引号字符串 + unicode 转义（`\u201c` / `\u201d`）。
9. **开头孤立 `>`**：微信文章 HTML 中 section/div 嵌套 blockquote 会导致提取内容开头出现孤立的 `>` 字符。已在 `extract_wechat.py` 中添加自动清理（匹配 `^\s*>\s*\n`），如遇新情况请检查脚本是否生效。
### 飞书文档

19. **飞书页面客户端渲染**：curl 抓到的 HTML 是空壳，正文在 JS 中。必须走 Open API（`raw_content` 端点）。
20. **lark-cli 未绑定 hermes**：报错 `hermes context detected but lark-cli is not bound`。解决：`lark-cli config bind --source hermes --identity bot-only`。绑定后 lark-cli 共享 hermes 的 FEISHU_APP_ID/SECRET，无需额外配置。
21. **图片下载权限不足（99991672）**：bot 缺少 `drive:drive` 等 scope 时，`medias/{token}/download` 会失败。**解决方案**：用 `docs_ai` API（`POST /open-apis/docs_ai/v1/documents/{token}/fetch`），返回的 XML content 中 `<img href="...authcode/?code=REAL_CODE">` 包含带真实 auth code 的下载 URL，无需额外权限。content 是 unicode-escaped，需 `decode('unicode_escape')` 后提取。
22. **飞书 wiki 正文字段**：API 返回的 `data.content` 是纯文本，不是 Markdown。图片以文件名形式引用（如 `img01.jpg`），需从 blocks API 获取实际图片 token 并映射。
23. **lark-cli +fetch 带图片 URL**：绑定后 `lark-cli docs +fetch --doc TOKEN` 输出 XML 格式，`<img>` 标签的 `href` 属性包含带 authcode 的下载 URL。但 bot 无权限时这些 URL 也返回 400。
24. **自定义域名飞书文档**：部分组织使用自定义域名（如 `waytoagi.feishu.cn/wiki/...`），而非标准 `feishu.cn`。触发条件需扩展为 `*.feishu.cn/wiki/...` 和 `*.feishu.cn/docx/...`（通配子域名）。API 调用方式相同，tenant_access_token 和 endpoints 不变，只需从 URL 中正确提取 doc_token。
25. **docs_ai API 返回空 content**：部分文档调用 `docs_ai` fetch API 可能返回 `content: ""`（长度为 0）。此时应回退到 `raw_content` API 获取正文，图片则通过 blocks API 获取 token 列表。docs_ai 不是万能的，遇到空内容不要卡住。
26. **execute_code 读不到 /tmp 飞书 JSON**：与 pitfall 19 同理，execute_code 沙箱的 /tmp 与 terminal 的 /tmp 不共享。解决方案：在 execute_code 内部用 subprocess 调 curl 获取 API 响应，或写到用户目录。

23. **飞书文档图片回退策略**：bot 缺 `drive:drive` 权限且 `docs_ai` 返回空内容时，回退到 `raw_content` API 获取正文，图片通过 blocks API 获取 token 列表。详见 `references/feishu-wiki.md`。
24. **图片链接替换格式错误**：将外部 URL 替换为本地 wiki-link 时，常见错误是生成 `![图片](![[filename.jpg]])`（双层嵌套）。正确格式是 `![[filename.jpg]]`。用正则 `!\[图片\]\(https?://[^)]+\)` 匹配原始 URL，替换为 `![[filename.jpg]]`。不要用 sed 的简单字符串替换，容易出错。
26. **替换 URL 后必须验证图片文件**：用 `os.path.exists(local_path) and os.path.getsize(local_path) > 1000` 检查每个图片文件是否实际存在且非空。常见坑：curl 失败但 URL 已被替换，导致 markdown 引用不存在的本地文件。替换后用 `re.findall(r'https://pbs\\.twimg\\.com/', content)` 检查残留外部 URL，必须为 0。
### 适用范围

- **Wiki 页面** `*.feishu.cn/wiki/{token}`
- **Docx 文档** `*.feishu.cn/docx/{token}`

### 提取流程

#### Step 1: 获取 tenant_access_token

```bash
curl -sL -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d "{\"app_id\":\"$FEISHU_APP_ID\",\"app_secret\":\"$FEISHU_APP_SECRET\"}"
```

#### Step 2: 获取文档正文

```bash
TOKEN="<tenant_access_token>"
DOC_TOKEN="<从URL提取的token>"
curl -sL "https://open.feishu.cn/open-apis/docx/v1/documents/$DOC_TOKEN/raw_content" \
  -H "Authorization: Bearer $TOKEN"
```

返回 JSON 中 `data.content` 即为纯文本正文。

#### Step 3: 获取文档图片（两种方式）

**方式 A：docs_ai API（推荐，无需 drive 权限）**

⚠️ **注意**：docs_ai 对部分文档（尤其是从外部平台转发的 wiki 页面）可能返回空 content。遇到空内容时直接跳到方式 B 或回退到 raw_content + blocks API。

```bash
curl -sL -X POST "https://open.feishu.cn/open-apis/docs_ai/v1/documents/$DOC_TOKEN/fetch" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"export_option":{"export_block_id":false,"export_cite_extra_data":false,"export_style_attrs":false},"format":"xml"}'
```

返回的 XML content 中，`<img>` 标签的 `href` 属性包含带 auth code 的完整下载 URL。注意 content 是 unicode-escaped（`\u003c` 等），需先 decode 再提取。

**方式 B：blocks API + medias download（需要 drive 权限）**

```bash
curl -sL "https://open.feishu.cn/open-apis/docx/v1/documents/$DOC_TOKEN/blocks?page_size=500" \
  -H "Authorization: Bearer $TOKEN"
```

图片下载需要 `drive:drive:readonly` 或 `docs:doc:readonly` 权限。如果 bot 权限不够，用方式 A。

#### Step 4: 绑定 lark-cli（可选但推荐）

绑定后可用 `lark-cli docs +fetch` 获取带图片 href 的 XML 格式内容：

```bash
lark-cli config bind --source hermes --identity bot-only
```

绑定后 lark-cli 的 `+fetch` 输出中 `<img href="...">` 包含图片下载 URL（带 authcode），比纯 raw_content API 更丰富。

#### Step 5: 下载图片

**方式 A：Open API 直接下载**

```bash
curl -sL "https://open.feishu.cn/open-apis/drive/v1/medias/{image_token}/download" \
  -H "Authorization: Bearer $TOKEN" -o output.jpg
```

**方式 B：lark-cli 下载**

```bash
cd /目标目录
lark-cli docs +media-download --token "{image_token}" --type media --output "filename.jpg"
```

⚠️ 两种方式都需要 bot 有以下任一 scope：
- `drive:drive:readonly`（推荐）
- `docs:doc:readonly`
- `docs:document.media:download`

如果返回 99991672 错误，说明 bot 缺少权限。见 Pitfall #21。

#### Step 6: 权限不足时的回退策略

**lark-cli 媒体下载语法**（需先 `cd` 到目标目录，--output 只接受相对路径）：
```bash
cd "$ARTICLE_ASSETS_DIR"
lark-cli docs +media-download --token "IMAGE_TOKEN" --type media --output "filename.png" --as bot
```
如果 bot 缺权限（99991672），此命令会失败。此时：

如果是原创飞书文档（无外部来源），需要在飞书开放平台给 bot 加权限：
https://open.feishu.cn/app/{app_id}/auth → 搜索 scope 开通 → 发版生效

### 通用网页内容提取

本技能同时覆盖一般网页文章的 Markdown 转换。对于非微信、非 X 的普通网页：

1. 用浏览器 User-Agent 的 curl 下载 HTML
2. 用 `html2text`（首选）或 `references/html-to-markdown-regex.md` 中的正则转换器提取正文
3. 清理导航栏、页脚、广告、侧边栏等非正文内容
4. 按相同的 frontmatter 格式组装并保存

#### 通用网页完整流程（2026-06-02 验证）

```bash
# Step 1: 下载
curl -sL -A "Mozilla/5.0 ..." "URL" -o /tmp/article.html

# Step 2: html2text 转换
cat /tmp/article.html | python3 -c "
import sys, html2text
h = html2text.HTML2Text()
h.ignore_links = False
h.ignore_images = False
h.body_width = 0
print(h.handle(sys.stdin.read()))
" > /tmp/article_raw.md

# Step 3: 清理（去掉 header/footer/nav/广告/页脚等）
# Step 4: 组装 frontmatter + 正文，保存到 00-inbox/new/
```

**图片处理**：通用网页的图片可能是相对路径或 CDN 优化 URL（如 Next.js 的 `/_next/image?url=...`）。需：
1. 从 HTML 提取原始图片路径
2. 拼接完整 URL（基于站点域名）
3. 下载到 `00-inbox/assets/`
4. 替换文章中的图片引用为 `../assets/{filename}`

**图片命名**：统一用 `前缀-序号.ext`，序号两位补零。如 `appstore-ai-01.webp`。

WeChat 文章的 HTML 结构模式详见 `references/wechat-patterns.md`。

## 脚本清单

- `scripts/extract_wechat.py` — 从下载的 HTML 中提取正文并转 Markdown 的 Python 脚本（传统格式）
- `scripts/extract_shadow_dom.py` — 从 Shadow DOM 格式的 HTML 中提取正文的 Python 脚本（新格式）

## 参考文件

- `references/html-to-markdown-regex.md` — 通用 HTML → Markdown 正则转换器（html2text 的 fallback）
- `references/wechat-patterns.md` — 微信文章 HTML 结构模式
- `references/shadow-dom-format.md` — Shadow DOM 新格式的识别和提取方法
- `references/feishu-wiki.md` — 飞书文档/Wiki 提取流程、API 参考和已验证案例
- `references/web-scraping-patterns.md` — 通用网页抓取模式：Next.js 图片、html2text 用法、常见站点结构

## Post-Conversion: 图片本地化

转换完成后，文章中的图片仍指向外部 URL（如 `mmbiz.qpic.cn`）。需本地化：

**推荐做法：用一个 `execute_code` 完成全部图片下载 + URL 替换 + 写入文件**。

手动流程（备用）：

```bash
# 1. 提取所有图片链接
grep -o 'https://[^)]*' /path/to/article.md | grep -E 'mmbiz\.qpic'

# 2. 逐个下载到 00-inbox/assets/，文件名格式：{date}_{slug}_{序号}.{ext}
python3 -c "import urllib.request; urllib.request.urlretrieve('IMAGE_URL', '$ARTICLE_ASSETS_DIR/{filename}')"

# 3. 替换文章中的链接为本地路径
# 用 execute_code 或 Python 脚本做批量替换，不要用 sed（URL 中的特殊字符容易出错）
```

> 这一步必须在建 wiki 页面之前完成（CLAUDE.md Ingest 流程 Step 1b）。

**验证清单**：
- [ ] 所有图片文件存在且 size > 1KB
- [ ] markdown 中无残留外部图片 URL（`grep -c 'mmbiz.qpic' article.md` 为 0）
- [ ] 封面图在 frontmatter 的 `cover` 字段中正确引用
- [ ] **语言检查**：英文文章已翻译为中文，frontmatter 含 `translated: true`，代码块保留英文原文

> 🛑 **STOP：写盘前必须逐项检查以上清单。任一项不通过则回溯修复，不可带问题保存。**

## Post-Conversion: 素材库处理

文章保存到素材库 `00-inbox/new/` 后，素材即进入素材库的处理流水线。后续流程定义在素材库 `AGENTS.md` 中：

1. **Distill** — 从 `00-inbox/new/` 提炼成 `01-sources/` 素材卡（一条来源一张卡）
2. **Topic** — 从多张素材卡组合 `02-topics/` 选题卡（至少引用 2 条素材卡）
3. **Draft** — 确定平台后推进到 `05-draft-seeds/wechat/` 或 `xiaohongshu/`
4. **Review** — 发布后在 `06-review/` 记录复盘
5. **Arsenal** — 经验证的写法沉淀到 `03-arsenal/`

> 素材库只负责"能写什么、怎么写"。长期稳定判断（概念、实体、作者）进入知识库 `wiki/output/`，不留在素材库。

### 知识库 Ingest（可选）

如果文章涉及新概念、新工具/产品或新作者，可同步生成知识库 wiki 页面：

1. **源材料摘要页** → `wiki/sources/{date}-{slug}.md`（frontmatter: type=source, title, url, date_published, date_ingested）
2. **实体页** → `wiki/entities/{name}.md`（工具、产品、平台）
3. **作者页** → `wiki/author/{name}.md`（公众号、博主）
4. **概念页** → `wiki/concepts/{name}.md`（仅当涉及新概念时新建）
5. **更新 index.md** — 在对应 section 添加新条目，更新 `updated` 日期
6. **追加 log.md** — 记录本次 ingest 的来源、生成页面、判断依据

> 源材料摘要页的 frontmatter 必须包含 `type: source`，与概念页/实体页区分。

## 注意事项

- 微信图片有懒加载占位符（`data:image/svg+xml`），需从 `data-src` 提取真实 URL
- 保留所有内容，不删除任何元素
- 文件名中的特殊字符需替换为下划线
- 图片本地化是独立步骤，不依赖 skill 脚本，需手动 curl + sed

### Hermes Desktop 使用注意

- **拖拽附件不支持文件夹**：Hermes Desktop 的拖拽功能只支持单个文件，拖入文件夹会报错 `file not found on gateway and no data_url provided`，右侧面板会显示 `path points to a directory`。如需让 AI 读取整个技能目录，直接在聊天框中说明路径即可，不需要拖拽。
- **推荐用法**：直接在聊天中发送链接（微信/飞书），技能会自动触发。如需查看技能文件内容，使用 `/skill wechat-article-to-markdown` 或在对话中提及即可。

## 脚本依赖

- `scripts/extract_x_article.py` 被 `x-article-processor` 技能引用。如果两个技能安装在不同位置，需通过 `X_ARTICLE_EXTRACT_SCRIPT` 环境变量指定脚本路径。

## Pitfalls（图片本地化）

### 用户偏好（重要）
17. **重复图片 URL**：部分文章会重复使用同一图片 URL（如排行榜文章每项配同一张图）。sed 的 `g` flag 会全局替换所有出现，这是正确行为，无需特殊处理。
18. **图片文件名规范**：格式为 `{article-slug}-{序号}.{ext}`，序号两位数补零。示例：文章 `codex-guide.md` 的图片 → `codex-guide-01.png`、`codex-guide-02.png`。禁止用中文文件名、禁止用时间戳作文件名。

## 反例与黑名单（不要做什么）

> 以下是经验证的反模式。违反任一条会导致输出质量下降或流程失败。

| # | 禁止行为 | 后果 | 正确做法 |
|---|---------|------|---------|
| 1 | 用 `python3 -c "..."` 内联执行 3MB+ HTML | timeout，进程卡死 | 写入 `/tmp/extract_*.py` 再 `python3 /tmp/xxx.py` |
| 2 | curl 不加代理直连微信 CDN | exit code 28 timeout | 必须加 `--proxy http://127.0.0.1:7890` |
| 3 | 用 `grep -oP` 在 macOS | 报错 `invalid option` | 用 `grep -o` + `sed` 替代 |
| 4 | 跳过语言检测直接保存 | 英文文章未翻译，素材库质量下降 | 每次必须判断语言，英文必须翻译 |
| 5 | 翻译后忘记替换图片 URL | 图片仍指向外部 URL，后续本地化失败 | delegate_task 返回后必须在组装阶段替换 |
| 6 | `source` 字段写死"微信公众号" | 丢失溯源信息，无法回溯原文 | 必须填实际文章 URL |
| 7 | 用 `git reset --hard` 回滚 | 丢失工作树未提交改动 | 用 `git revert HEAD` 创建反向 commit |
| 8 | 同一个 session 又改又评 | LLM 自评准确率仅 46.4%，乐观偏差 | 评分用独立子 agent |
| 9 | 图片替换用简单 sed 字符串替换 | URL 中特殊字符导致替换失败 | 用 Python 正则批量替换 |
| 10 | 生成 `![图片](![[filename]])` 双层嵌套 | Markdown 渲染错误 | 正确格式是 `![[filename.jpg]]` |
