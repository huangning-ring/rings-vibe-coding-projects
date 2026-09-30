---
name: literature-search-setup
description: >
  文献检索工作流的首次环境配置与 API Key 布置。在新机器/云端安装并配置 scansci-pdf 与
  paper-fetch 两个 MCP 引擎、申请并写入可用 API key、验证数据源就绪，并引导用户选配
  可选的 Elsevier/机构访问通道。触发词：配置文献检索、装 scansci-pdf、装 paper-fetch、
  配 API key、新机搭文献环境、文献检索环境配置。
---
# 文献检索环境配置
在目标机器上把文献检索链的**执行引擎 + 可配置的 API key** 一次布置到可用状态。原则：**能免费申请/便捷 CLI 配齐的尽量配，付费/机构通道作为可选项交给用户拍板，不默认强配。**
## 前置事实（本机已验证）
- **检索层**：PubMed / Europe PMC / OpenAlex / Crossref / arXiv 公共 API **直连免 key**（Semantic Scholar 需 key，否则 429 限流）。
- **执行引擎**：`scansci-pdf`（18 工具，PyPI 可用 `uvx`）+ `paper-fetch` v6.2.4（离线包，GitHub Releases Dictation354/paper-fetch-skill）。
- **outbox**：`/home/admin/hermes-outbox`（可写，交付通道）。
- **Obsidian vault**：云端只读（owner=syncthing），**不写入**；Obsidian 侧由用户从 outbox 同步。
- **依赖 skill**：`grilling`、`personal-format` 需已在。
## 第 1 步 · 验证/安装执行引擎
```bash
# scansci-pdf：PyPI，用 uvx 隔离，不污染 venv
uvx scansci-pdf --help          # 验证可跑；MCP 入口是 `run`
uvx scansci-pdf check           # 依赖诊断

# paper-fetch：离线自解压（GitHub Releases v6.2.4，Linux x86_64 cp311）
# 下载 .sh → 对照 Releases SHA256SUMS 校验 →
./install-offline.sh --install-dir $HOME/.local/share/paper-fetch-skill \
  --preset=headless --non-interactive --no-user-config
# 确认：paper-fetch --version / paper_fetch import / bin/paper-fetch-mcp 存在
```
## 第 2 步 · 挂进 Hermes（重启 gateway 后生效）
```bash
hermes config set mcp_servers.scansci-pdf.command uvx
hermes config set mcp_servers.scansci-pdf.args '["scansci-pdf","run"]'
hermes config set mcp_servers.scansci-pdf.enabled true
hermes config set mcp_servers.scansci-pdf.timeout 180

hermes config set mcp_servers.paper-fetch.command /home/admin/.local/share/paper-fetch-skill/bin/paper-fetch-mcp
hermes config set mcp_servers.paper-fetch.args '[]'
hermes config set 'mcp_servers.paper-fetch.env.PAPER_FETCH_ENV_FILE' /home/admin/.local/share/paper-fetch-skill/offline.env
hermes config set mcp_servers.paper-fetch.enabled true
hermes config set mcp_servers.paper-fetch.timeout 300
```
之后用 `hermes mcp test scansci-pdf` / `hermes mcp test paper-fetch` 验证连接与工具数。
### 第 3 步 · API Key
前言：Elsevier 权限、机构登录等为**后续可选项**，用户需要时才研究，不默认强配。
### A. 强烈推荐（免费，扩源显著，无风险）

| Key | 载体 | 申请方法 | 作用 |
|---|---|---|---|
| `OPENALEX_API_KEY` | scansci-pdf | OpenAlex 官网免费注册 | OpenAlex 源稳定访问 |
| `ELSEVIER_API_KEY` | both | dev.elsevier.com 免费→My API Key→ScienceDirect Article Retrieval | Elsevier/ScienceDirect 直达下载 |
| `SPRINGER_API_KEY` | scansci-pdf | Springer Nature 开发者站免费 | Springer/OA 源 |
| `UNPAYWALL_EMAIL` | paper-fetch | 任意邮箱 | Unpaywall OA 覆盖 |
| `CROSSREF_MAILTO` | paper-fetch | 你的邮箱（polite pool 礼仪） | Crossref 合规拉取 |
```bash
# paper-fetch：写入 offline.env
#   /home/admin/.local/share/paper-fetch-skill/offline.env
#   UNPAYWALL_EMAIL=you@example.com
#   CROSSREF_MAILTO=you@example.com
#   ELSEVIER_API_KEY=***

# scansci-pdf：config-cmd
uvx scansci-pdf config-cmd openalex_api_key <key>
uvx scansci-pdf config-cmd elsevier_api_key <key>
uvx scansci-pdf config-cmd springer_api_key <key>
```
**Elsevier 便捷引导（优先走 CLI，请用户选配）**
```bash
uvx scansci-pdf elsevier_setup   # 打开指导页，引导注册 ScienceDirect Article Retrieval API
# 注册后：uvx scansci-pdf config-cmd elsevier_api_key <key>
# 验证：uvx scansci-pdf config-cmd elsevier_api_key  应显示 key，去掉值后 `paper-fetch doctor` 的 elsevier 变 ready
```
### B. 可选增强（试用/少用才配）

| Key | 载体 | 申请 | 作用 |
|---|---|---|---|
| `WILEY_TDM_CLIENT_TOKEN` | paper-fetch | Wiley TDM 授权 | Wiley 官方 PDF |
| `PAPER_FETCH_TAVILY_API_KEY` | paper-fetch | Tavily 免费（1000 积分/月） | 网页发现/预印本兜底 |
| `PAPER_FETCH_HTTP_PROXY` | paper-fetch | 自己/学校代理 | 出口受限时（`http://127.0.0.1:7890`） |
### C. 默认已就绪（无需配）
- `scihub_enabled=True` + Hub 域名清单已内建 → **SciHub 默认启用生效**。
- `download_strategy=fastest`（全源竞速）。
- 公共 API 直连免 key。
### D. 后续可选项（用户需要时才研究，说明为可选）
- **机构登录 / WebVPN / CARSI / EZProxy**（`uvx scansci-pdf setup` 引导；`carsi_enabled`、`ezproxy_enabled`、`schools`/`vpnsci_*` 工具）。依赖机构账号登录态，通常归 Windows/机构端。
- **`ELSEVIER_INSTTOKEN`**（机构令牌，需学校图书馆申请）。
- **`core_api_key`**（CORE 源需申请）。
- **Zotero 桌面**（`scansci-pdf zotero_push` 需本机 Zotero 服务；云端无）。
> 这些默认**不配置**。用户明确要机构受限全文或 Zotero 导入时，再单独研究并按 `scansci-pdf setup`/`login`/`auth` 引导。

## 第 4 步 · 验证
```bash
# 每把 key 写后看 provider 从 not_configured → ready
paper-fetch doctor 2>&1 | grep -E "elsevier|openalex|springer|unpaywall|crossref"
uvx scansci-pdf config-cmd          # 确认 key 已写入
hermes mcp test scansci-pdf && hermes mcp test paper-fetch
```
## 边界
- key 均为只读 API token，**只写入本地配置文件**；绝不写入记忆/聊天/日志。
- 机构凭据一律归 Windows/机构端，云端不握有登录态。
- 重装 `install-offline.sh` 会重写 skill/MCP 注册，按需 `--no-user-config`。