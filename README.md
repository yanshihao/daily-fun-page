# Daily Fun Page

一个面向中文用户、只依赖 GitHub Pages 和 GitHub Actions 的“每日趣味”静态网页。

## 功能

- 每天自动生成 `data/today.json`
- 首页展示今日趣味卡片
- 自动保留 `data/versions/YYYY-MM-DD-HH-MM-SS.json` 多版本快照
- 同时保留 `data/archive/YYYY-MM-DD.json` 作为当天最新版兼容入口
- 使用 GitHub Actions 定时更新
- 使用 GitHub Pages 静态托管

## 内容来源

当前版本会优先尝试从中文来源获取内容：

- 微博热搜
- 中文维基日期摘要
- Solidot 中文科技 RSS
- V2EX RSS
- 少数派 RSS
- 中文开源项目搜索
- 内置中文冷知识与灵感短句兜底

> 如果某个外部 API 暂时不可用，脚本仍会用兜底内容生成页面，避免页面空白。

## 本地运行

```bash
python3 scripts/collect_daily.py
python3 -m http.server 8011
```

然后访问：

```text
http://localhost:8011
```

## 自动更新

`.github/workflows/daily.yml` 会在每天 UTC 00:20 自动运行，也可以在 GitHub Actions 页面手动触发。
