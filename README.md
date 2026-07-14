# Xiaohongshu Public Profile Reader

一个只读取小红书公开主页快照的 Codex Skill。它从公开页面内嵌的 `window.__INITIAL_STATE__` 中提取资料、页面展示的互动数、首屏笔记和封面元数据，并输出结构化 JSON。

## 使用

```bash
python3 scripts/read_profile.py "https://www.xiaohongshu.com/user/profile/<user-id>" --pretty
```

也可以解析已下载的 HTML：

```bash
python3 scripts/read_profile.py \
  --html-file /path/to/profile.html \
  --source-url "https://www.xiaohongshu.com/user/profile/<user-id>" \
  --pretty
```

## 数据边界

- 只读取公开网页中已经暴露的信息。
- 不登录、不使用 Cookie、不调用私有 API，也不绕过访问控制。
- 互动数是页面展示值，可能经过缩写、隐藏或为空。
- 笔记仅代表公开首屏快照，不是完整历史。
- 不提供曝光、点击率、收藏、完播率、粉丝转化或收入等创作者后台数据。

## 目录

```text
.
├── SKILL.md
├── agents/openai.yaml
└── scripts/read_profile.py
```

## 依赖

- Python 3
- `curl`（仅在线读取公开主页时需要）
