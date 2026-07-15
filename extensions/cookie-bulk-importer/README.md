# Local Cookie Bulk Importer
一次性、离线的 Chromium 扩展，用于从 Cookie-Editor JSON 数组批量导入多个域名的 Cookie。
A one-time offline Chromium extension for importing multi-domain cookies from a Cookie-Editor JSON array.
# 使用 / Usage
1. 在 Chrome 打开 `chrome://extensions`。
2. 开启开发者模式，选择“加载已解压的扩展程序”，选中本文件夹。
3. 点击扩展图标并选择 JSON 文件。
4. 核对读取数量后开始导入，等待完成报告。
5. 验证网站登录状态后立即卸载扩展。
1. Open `chrome://extensions` in Chrome.
2. Enable Developer mode, choose Load unpacked, and select this folder.
3. Open the extension and select the JSON file.
4. Verify the parsed counts, run the import, and wait for the final report.
5. Verify the required site sessions, then uninstall the extension immediately.
# 权限 / Permissions
- `cookies`：读取导入前后的 Cookie 总数并写入 Cookie。
- `<all_urls>`：为 JSON 中每个域名构造合法目标 URL。
- `cookies`: reads before/after counts and writes cookies.
- `<all_urls>`: permits a valid target URL to be constructed for every imported domain.
# 隐私 / Privacy
扩展没有联网代码，不上传所选文件或 Cookie。请勿把真实 Cookie JSON 提交到 Git、Release、Issue 或日志中。
The extension contains no network code and does not upload the selected file or cookies. Never commit real cookie JSON files to Git, Releases, Issues, or logs.
