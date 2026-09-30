---
name: literature-search-workflow
description: >
  云端医学科文献检索与下载实操：grilling 澄清主题 → 真实 MeSH 构建检索式 → 多库查准/查全 →
  开放全文→SciHub→题录三步下载 → 双报告(检索报告+下载报告) → 发 outbox。触发词：查文献、
  文献检索、查准版、查全版、医学文献检索汇报、下载全文、做这个主题的文献调研、综述检索。
---
# 文献检索下载工作流（云端实操）
融合用户自制的“查准/查全两阶段 + MeSH/自由词/布尔检索式 + 双报告”工作流、云端-本机-Windows 分工以及现有依赖（scansci-pdf + paper-fetch MCP）。
## 第 1 步 · grilling 追问主题（必做）
用 `grilling` 的交互方式澄清——**一次一个问题、附我的推荐答案、能查的技术事实我自己查**。覆盖：
- 完整综述 / 深挖某机制 / 课题立项前调研？
- 查全（无遗漏）还是查准（高相关）？有无已知锚点文献/综述？
- 主题拆解：核心概念对象词是什么（忽略形容词/副词/限定语）？
- 时间范围、语言（中英）、文献类型（原始研究/综述/预印本）、是否含中文库（知网/万方）？
- 只要检索报告，还是要下载全文并清洗？报告给谁、篇幅？
- 是否涉及受限全文/机构？确认接受 SciHub 默认启用（本工作流不再中途请求授权）。
**事实类（自己查，不问用户）**：MeSH 词表、数据库可达性、工具/MCP 状态。
先明确这些再进检索；实时工具调用自行执行，不因此打断用户。
## 第 2 步 · 主题词提取 + 真实 MeSH
- 从主题提取 **核心概念对象词**，拆成主题词组。
- **英文库走真实 MeSH 规范表达**：`esearch db=mesh` 取主题词 → `efetch db=mesh` 取 Entry terms 自由词。
- **中文库（知网/万方）**跳过 MeSH，直接用模型生成主题词 + 自由词。
- 自由词清洗：去带逗号、词干合并（`*` 通配）、每组 ≤6 词。
- 检索式 = 同词组 OR、组间 AND、可选 NOT；给**单行/换行/去字段三版**。
## 第 3 步 · 多库检索（查准 → 查全）
- PubMed（E-utilities）主查 + Europe PMC + OpenAlex + Crossref + arXiv（Semantic Scholar 无 key 跳过）。
- **每轮跑前把检索式 + 数据库/纳排/时间/语言/类型给用户确认**。
- 查准版先跑；强候选太少才升查全版（扩同义词/放宽限制/加 related-cited-by/更多 OA 库），同样先确认。
- 每轮汇报：各库原始命中数、去重后总数、题名/摘要筛选后数量、强候选、研究类型分布、新颖性、建议下载清单。
## 第 4 步 · 全文获取（开放 → SciHub → 题录）
1. **开放全文优先**：`mcp_scansci_pdf_download` / `batch_download`（OA/PMC/arXiv/Crossref 等竞速）。
2. **SciHub 默认启用**：完全按工具默认（`scihub_enabled=True`、`download_strategy=fastest`），不额外提示/标注，不请求授权。
3. **仍拿不到 → 只存题录**（篇名/作者/期刊/DOI/摘要/关键词/来源/获取尝试），并用中文总结该篇。
4. 拿到全文的 → `mcp_paper_fetch_fetch_paper` 清洗成 AI 可读 Markdown + 结构化元数据。
## 第 5 步 · 双报告 + 交付 outbox
**检索报告.md**：库列表+理由、MeSH/自由词策略、布尔逻辑/时间/语言/类型区间、每库代表检索式、各库命中数/去重数/筛选数/全文数、5-10 篇核心摘要（研究设计/样本量/暴露/对照/结局/关键发现/证据等级）、Mermaid 检索流程图。
**下载报告.md**：每篇 DOI/题名、下载途径（OA / SciHub / 仅题录）、成功/失败、Markdown 路径、中文总结、待补动作（题录篇的上游获取）。
全部过 `personal-format` 标准化；写入 **`/home/admin/hermes-outbox/YYYY-MM-DD 文献检索-主题短名/`**（检索报告.md + 下载报告.md + per-paper Markdown 视需要）。
## 边界（写死）
- **云端（本机）**：grilling/主题拆解、MeSH+检索式、多库公共 API 检索、开放全文+SciHub 下载、paper-fetch 清洗、双报告、发 outbox。
- **Windows 端**：机构登录/WebVPN/CARSI/EZProxy 受限全文、Zotero 桌面导入。
- 云端不碰机构登录态、Zotero desktop、受限全文权限；Obsidian vault 只读不写，Obsidian 侧由用户从 outbox 同步。
## 依赖（已就绪）
公共 API、`scansci-pdf` MCP（18 工具）、`paper-fetch` MCP（9 工具）、outbox 目录、`personal-format` 与 `grilling` 两个 skill。
环境短板（不阻塞）：node/npx 缺、Semantic Scholar 需 key、Camoufox 浏览器源需另配。