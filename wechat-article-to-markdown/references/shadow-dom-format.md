# 微信文章 Shadow DOM 新格式

## 背景

2025年起，部分微信公众号文章采用新的 HTML 结构，使用 Shadow DOM 渲染内容，导致传统的 `js_content` 提取方法失效。

## 特征识别

检查 HTML 是否为 Shadow DOM 格式：

```bash
# 检查 Shadow DOM 标志
grep -c "shadow" /tmp/wechat_article.html
# 返回 > 0 表示可能是 Shadow DOM 格式

# 检查是否有 js_content
grep -c "js_content" /tmp/wechat_article.html
# 返回 0 或只有 JS 变量引用（非 div 标签）表示需要备用方案
```

## 内容位置

Shadow DOM 格式的文章内容通常嵌入在 JavaScript 变量中：

```javascript
content: '最近我越来越确信：AI唯一正确的用法...\x0a\x0a很多人对自己总是...'
```

特征：
- 使用单引号或双引号包裹
- 换行符为 `\x0a`（而非 `\n`）
- 可能包含 HTML 实体编码（`\x26lt;` 等）
- 可能包含内联链接的 HTML 代码

## 提取方法

### 方法 1：正则提取 content 变量（推荐）

```python
import re
import html as html_module

with open('/tmp/wechat_article.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 匹配 content: '...' 或 content: "..."
pattern = r'content:\s*[\'"](.+?)[\'"]'
matches = re.findall(pattern, content, re.DOTALL)

# 取最长的匹配（通常是正文）
longest_match = max(matches, key=len) if matches else ""

# 解码
decoded = longest_match.replace('\\x0a', '\n').replace('\\x09', '\t')
decoded = decoded.replace('\\n', '\n').replace('\\t', '\t')
decoded = html_module.unescape(decoded)
```

### 方法 2：Shell 快速提取

```bash
# 提取 content 字段（单引号版本）
grep -o "content: '[^']*'" /tmp/wechat_article.html | head -1 | sed "s/content: '//;s/'$//" | sed 's/\\x0a/\n/g'

# 提取 content 字段（双引号版本）
grep -o 'content: "[^"]*"' /tmp/wechat_article.html | head -1 | sed 's/content: "//;s/"$//' | sed 's/\\x0a/\n/g'
```

## 后处理

提取后需要处理：

1. **去除内联链接 HTML**
   ```
   \x26lt;a class=\x26quot;normal_text_link...\x26gt;链接文字\x26lt;/a\x26gt;
   ```
   转换为 Markdown 链接格式或直接提取链接文字。

2. **清理转义字符**
   - `\x0a` → 换行
   - `\x09` → Tab
   - `\x26lt;` → `<`
   - `\x26gt;` → `>`
   - `\x26quot;` → `"`

3. **段落整理**
   - 连续空行合并为单个空行
   - 去除首尾空白

## 元数据提取

Shadow DOM 格式的元数据通常仍在 meta 标签中，可使用标准方法：

```bash
# 标题
grep -o 'og:title" content="[^"]*"' /tmp/wechat_article.html | sed 's/.*content="//;s/"//'

# 作者
grep -o 'og:article:author" content="[^"]*"' /tmp/wechat_article.html | sed 's/.*content="//;s/"//'
```

## 完整提取脚本

见 `scripts/extract_shadow_dom.py`
