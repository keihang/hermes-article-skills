# Hermes Article Skills

两个 Hermes Agent 技能，用于文章抓取和转换。

## 技能列表

| 技能 | 说明 | 适用范围 |
|------|------|----------|
| `wechat-article-to-markdown` | 微信公众号/飞书/网页文章转 Markdown | 微信、飞书、通用网页 |
| `x-article-processor` | X/Twitter 文章一键处理 | X/Twitter |

## 安装

```bash
# 方式一：通过 URL 安装（推荐）
hermes skills install https://raw.githubusercontent.com/keihang/hermes-article-skills/main/wechat-article-to-markdown/SKILL.md
hermes skills install https://raw.githubusercontent.com/keihang/hermes-article-skills/main/x-article-processor/SKILL.md

# 方式二：手动复制到 ~/.hermes/skills/
git clone https://github.com/keihang/hermes-article-skills.git
cp -r hermes-article-skills/wechat-article-to-markdown ~/.hermes/skills/
cp -r hermes-article-skills/x-article-processor ~/.hermes/skills/
```

## 使用

- 发送微信文章链接（`mp.weixin.qq.com/s/...`）→ 自动触发 `wechat-article-to-markdown`
- 发送飞书文档链接（`*.feishu.cn/wiki/...`）→ 自动触发 `wechat-article-to-markdown`
- 发送 X/Twitter 链接（`x.com/.../status/...`）→ 自动触发 `x-article-processor`

## 配置

两个 skill 默认保存路径需要根据你的环境修改，详见各自 SKILL.md 中的「保存路径」章节。
