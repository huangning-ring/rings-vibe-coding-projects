# Ring's vibe coding projects
个人 vibe coding 项目集合，按可复用能力类型分为 Skills、Plugins 和 Extensions。
Personal vibe coding projects organized as reusable skills, plugins, and extensions.
# 目录 / Directories
- `skills/`：面向 AI 编程代理的可复用技能包。Reusable skill packages for AI coding agents.
- `plugins/`：插件项目。Plugin projects.
- `extensions/`：浏览器或桌面扩展。Browser or desktop extensions.
# 当前项目 / Projects
- `extensions/cookie-bulk-importer/`：一次性、离线的 Chromium Cookie JSON 批量导入器。A one-time offline bulk importer for Chromium Cookie JSON exports.
- `skills/remove-blank-lines-md/`：递归清理 Markdown 空白行的技能。A skill for removing blank lines from Markdown files.
# 安全说明 / Security
`cookie-bulk-importer` 需要 Chrome 的 `cookies` 和 `<all_urls>` 权限，才能按每条记录的域名写入 Cookie。扩展不包含网络请求代码，也不应与真实 Cookie 文件一起提交或分发。仅从可信 Release 获取，检查源码后加载，导入完成并验证后立即卸载。
`cookie-bulk-importer` requires Chrome's `cookies` and `<all_urls>` permissions so it can write each cookie to its own domain. It contains no network request code. Never commit or distribute real cookie files with it. Load it only from a trusted release, inspect the source, and remove it immediately after import and verification.
# 安装扩展 / Install the extension
1. 下载并解压 `cookie-bulk-importer-v1.0.0.zip`。
2. 在 Chrome 打开 `chrome://extensions`，启用“开发者模式”。
3. 点击“加载已解压的扩展程序”，选择解压后的 `cookie-bulk-importer` 文件夹。
4. 点击扩展图标，选择 Cookie-Editor JSON 文件，核对条目与域名数量后开始导入。
5. 查看完成报告，验证目标网站，然后卸载扩展。
1. Download and extract `cookie-bulk-importer-v1.0.0.zip`.
2. Open `chrome://extensions` and enable Developer mode.
3. Choose Load unpacked and select the extracted `cookie-bulk-importer` folder.
4. Open the extension, select a Cookie-Editor JSON file, verify the counts, and start the import.
5. Review the result, verify the target sites, and uninstall the extension.
# License
MIT
