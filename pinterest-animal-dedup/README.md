# pinterest-animal-dedup

Pinterest 动物搞笑/治愈短视频选题发现、国内五平台语义查重、评分与本地结果 UI。与仓库内现有 video skills **完全隔离**（独立依赖、CLI、数据库、产物目录）。

## 能力（Phase 1）

| 阶段 | 说明 |
| --- | --- |
| Discover | 英文 query 扩展 → Pinterest 搜索页；若 CSR 无 Pin 载荷则回退 `site:pinterest.com/pin` 公开网页索引 |
| Analyze | 动物/基调/动作感/版权提示（不明 → Mode B） |
| Dedup | 抖音、快手、微信视频号、小红书、B站：每平台 ≥5 条中文 query + `site:` 公开搜索证据 |
| Visual | 可获取缩略图时 pHash/dHash（不伪造匹配） |
| Score | /100 六维加权 |
| UI | FastAPI 本地表格 |

### 查重状态

- `NOT_FOUND`：允许范围内的公开搜索未命中该平台（**不等于**国内从未发布）
- `POSSIBLE_MATCH`：弱命中或仅视觉相似，需人工复核
- `CONFIRMED_MATCH`：多信号或极强视觉相似（仍建议人工确认）
- `UNKNOWN`：平台/搜索不可达或证据过薄

### 评分维度（满分 100）

搞笑/治愈 25 · 前 3 秒钩子 20 · 国内新鲜度 20 · 改编空间 15 · 故事完整 10 · 制作难度 10

## 访问与合规边界

- 仅使用 **可公开访问** 的 Pinterest 搜索页 HTML 与 Pin 页元数据；**不**绕过登录墙、不爬私有 API、不编造 Pin URL 或互动数据。
- 国内查重使用 DuckDuckGo HTML / Bing HTML 的 `site:域名` 查询（可选 `PAD_SEARX_URL` 指向自建 SearXNG）；数据中心 IP 常被限流，此时状态会标为 `UNKNOWN`，请在本地网络重跑 `pad dedup`。
- 版权不明时默认 **Mode B AI 改编**，不声称可免费商用原素材。

## 安装

```bash
cd pinterest-animal-dedup
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
# 可选 Postgres：
# docker compose up -d
# export PAD_DATABASE_URL=postgresql+psycopg2://pad:pad@localhost:54329/pinterest_animal_dedup
```

默认数据库：SQLite `data/pad.sqlite3`。

## CLI

```bash
pad discover          # 发现 Pin
pad analyze           # 动物内容分析
pad dedup             # 五平台查重
pad score             # 评分并导出 artifacts
pad ui                # http://127.0.0.1:8765
pad run-demo          # 端到端（目标 ~20 条，写入 artifacts/）
pad package-top       # 为最高分可用选题生成 Mode B 短片包
```

## 产物

- `artifacts/ranked_report.md` / `.json` — 排名表
- `artifacts/first_short_package/mode_b_pin_<id>/` — `script.md`, `storyboard.json`, `source.json`, `domestic_check.json`, `publish.json`

## 测试

```bash
pytest
```

## 限制说明

Pinterest 与国内平台可能对数据中心 IP 限流或返回空结果。此时候选数量会下降，查重状态会诚实标记为 `UNKNOWN`。请在可访问 Pinterest 的网络环境重跑 `pad run-demo` 以充实候选池。
