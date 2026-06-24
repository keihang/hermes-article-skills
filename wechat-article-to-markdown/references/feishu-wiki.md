# 飞书文档/Wiki 提取参考

## 端点

```
POST https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal
GET  https://open.feishu.cn/open-apis/docx/v1/documents/{doc_token}/raw_content
POST https://open.feishu.cn/open-apis/docs_ai/v1/documents/{doc_token}/fetch
GET  https://open.feishu.cn/open-apis/docx/v1/documents/{doc_token}/blocks?page_size=500
GET  https://open.feishu.cn/open-apis/drive/v1/medias/{media_token}/download
```

## 从 URL 提取 token

```
https://waytoagi.feishu.cn/wiki/ByypwsWa4iWwMYke19xc0ewMnac
                                         ^^^^^^^^^^^^^^^^^^^^^^^^
                                         doc_token
```

- `wiki/` 和 `docx/` 后面的 token 都可用
- `raw_content` 和 `docs_ai` API 对两种 token 都适用

## 认证

需要 `tenant_access_token`，从 FEISHU_APP_ID + FEISHU_APP_SECRET 获取：

```bash
curl -sL -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d "{\"app_id\":\"$FEISHU_APP_ID\",\"app_secret\":\"$FEISHU_APP_SECRET\"}"
```

## 图片提取

### 推荐：docs_ai API（无需 drive 权限）

```bash
curl -sL -X POST "https://open.feishu.cn/open-apis/docs_ai/v1/documents/{doc_token}/fetch" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"export_option":{"export_block_id":false,"export_cite_extra_data":false,"export_style_attrs":false},"format":"xml"}'
```

返回 JSON 中 `data.document.content` 是 unicode-escaped XML，包含 `<img>` 标签。

关键字段：
- `href="https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=REAL_CODE"` — 可直接下载
- `src="MEDIA_TOKEN"` — 飞书 media token
- `name="filename.png"` — 原始文件名

提取步骤：
1. `json.load` 解析 JSON
2. `content.encode().decode('unicode_escape')` 解码 unicode
3. `re.findall(r'<img[^>]+/>', decoded)` 提取所有 img 标签
4. 从每个 img 的 `href` 属性提取下载 URL（含 auth code）
5. `curl -sL -o output.png URL` 下载

### 备选：blocks API + medias download（需要 drive 权限）

```bash
curl -sL "https://open.feishu.cn/open-apis/docx/v1/documents/$DOC_TOKEN/blocks?page_size=500" \
  -H "Authorization: Bearer $TOKEN"
```

图片下载需要 `drive:drive:readonly` 或 `docs:doc:readonly` 权限。

## 已验证案例

| 来源 | 类型 | 结果 |
|------|------|------|
| waytoagi wiki | 20 个 AI 概念 | ✅ 正文 8493 字，21 图（X 原帖下载） |
| waytoagi wiki | Codex DeepSeek 教程 | ✅ 正文 6456 字，25 图（docs_ai API 下载） |
| waytoagi wiki | AI Agents 完整课程 | ✅ 正文 7445 字，15 图（fxtwitter + 代理下载） |

## 回退策略：bot 缺 drive 权限 + docs_ai 返回空内容

当 docs_ai API 返回空 content 且 bot 缺少 `drive:drive` 权限时：

1. 从 `raw_content` 中查找原帖链接（X/Twitter 等）
2. 如果找到，用 fxtwitter API 获取图片 URL
3. 用代理下载图片（`pbs.twimg.com` 需要 `--proxy http://127.0.0.1:7890`）
4. 替换文章中的图片链接为本地 wiki-link 格式

```bash
# 查找原帖链接
curl -sL "https://open.feishu.cn/open-apis/docx/v1/documents/$DOC_TOKEN/raw_content" \
  -H "Authorization: Bearer $TENANT_TOKEN" | grep -o 'https://x.com/[^ ]*status/[0-9]*'

# 用 fxtwitter API 获取图片
curl -sL "https://api.fxtwitter.com/{username}/status/{tweet_id}" > /tmp/x_tweet.json

# 用代理下载图片
curl -sL --proxy http://127.0.0.1:7890 "https://pbs.twimg.com/media/xxx.jpg" -o output.jpg
```

图片链接替换正则（注意 wiki-link 用双括号）：

```python
# ![图片](https://...) → ![[filename.jpg]]
content = re.sub(r'!\[图片\]\(https?://[^)]+\)', lambda m: f'![[{filename}]]', content)
```

已验证：waytoagi wiki AI Agents 课程（15 图，fxtwitter + 代理下载）

## Pitfalls

1. **客户端渲染**：飞书页面 HTML 不含正文内容，必须走 API。
2. **lark-cli 未绑定 hermes**：报错 `hermes context detected but lark-cli is not bound`。直接用 curl + Open API 绕过。
3. **medias download 权限不足**：返回 99991672。用 `docs_ai` API 绕过，其返回的 href 包含真实 auth code。
4. **unicode-escaped content**：`docs_ai` 返回的 content 中 `<` 变成 `\u003c`，`"` 变成 `\"`，需 `decode('unicode_escape')` 后再正则提取。
5. **raw_content = 纯文本**：`raw_content` API 返回纯文本，无图片信息。要图片必须用 `docs_ai` API。
6. **wiki vs docx token**：两种 token 都能用，无需转换。
7. **docs_ai 返回空内容**：部分文档（特别是从外部转发的）`docs_ai` API 返回空 content。此时检查 `raw_content` 中是否有外部原帖链接，用 fxtwitter API 获取图片。
8. **X/Twitter 图片需要代理**：`pbs.twimg.com` 在国内无法直连，curl 返回 exit code 35。必须加 `--proxy http://127.0.0.1:7890`。
