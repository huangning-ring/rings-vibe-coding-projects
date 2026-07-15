const fileInput = document.getElementById("cookie-file");
const importButton = document.getElementById("import-button");
const summary = document.getElementById("summary");
const progress = document.getElementById("progress");
const log = document.getElementById("log");

let cookies = [];

function appendLog(message) {
  log.textContent += `${message}\n`;
  log.scrollTop = log.scrollHeight;
}

function normalizeInput(parsed) {
  if (Array.isArray(parsed)) return parsed;
  if (parsed && Array.isArray(parsed.cookies)) return parsed.cookies;
  throw new Error("JSON 顶层必须是数组，或包含 cookies 数组。");
}

function cookieUrl(cookie) {
  const rawDomain = String(cookie.domain || "").trim();
  const host = rawDomain.replace(/^\.+/, "");
  if (!host) throw new Error("缺少 domain");

  const secureName = String(cookie.name || "").startsWith("__Secure-") ||
    String(cookie.name || "").startsWith("__Host-");
  const scheme = cookie.secure || secureName ? "https" : "http";
  const rawPath = String(cookie.path || "/");
  const path = rawPath.startsWith("/") ? rawPath : `/${rawPath}`;
  return `${scheme}://${host}${path}`;
}

function toChromeCookie(cookie) {
  const name = String(cookie.name ?? "");
  const isHostPrefix = name.startsWith("__Host-");
  const secure = Boolean(cookie.secure || isHostPrefix || name.startsWith("__Secure-"));
  const details = {
    url: cookieUrl({ ...cookie, secure }),
    name,
    value: String(cookie.value ?? ""),
    path: isHostPrefix ? "/" : String(cookie.path || "/"),
    secure,
    httpOnly: Boolean(cookie.httpOnly)
  };

  if (!cookie.hostOnly && !isHostPrefix) {
    details.domain = String(cookie.domain);
  }

  const expiration = Number(cookie.expirationDate);
  if (!cookie.session && Number.isFinite(expiration) && expiration > 0) {
    details.expirationDate = expiration;
  }

  const sameSite = cookie.sameSite;
  if (["no_restriction", "lax", "strict"].includes(sameSite)) {
    details.sameSite = sameSite;
  }

  return details;
}

fileInput.addEventListener("change", async () => {
  cookies = [];
  importButton.disabled = true;
  log.textContent = "";
  const file = fileInput.files && fileInput.files[0];
  if (!file) return;

  try {
    const parsed = JSON.parse(await file.text());
    cookies = normalizeInput(parsed);
    const domains = new Set(cookies.map((cookie) => cookie.domain).filter(Boolean));
    summary.textContent = `已读取 ${cookies.length} 条 Cookie，涉及 ${domains.size} 个域名。`;
    progress.max = Math.max(cookies.length, 1);
    progress.value = 0;
    importButton.disabled = cookies.length === 0;
  } catch (error) {
    summary.textContent = `读取失败：${error.message}`;
  }
});

importButton.addEventListener("click", async () => {
  importButton.disabled = true;
  fileInput.disabled = true;
  log.textContent = "";
  let succeeded = 0;
  const failures = [];
  const before = await chrome.cookies.getAll({});
  appendLog(`开始导入 ${cookies.length} 条；Chrome 当前共有 ${before.length} 条 Cookie。`);

  for (let index = 0; index < cookies.length; index += 1) {
    const cookie = cookies[index];
    try {
      const result = await chrome.cookies.set(toChromeCookie(cookie));
      if (!result) throw new Error("Chrome 未返回写入结果");
      succeeded += 1;
    } catch (error) {
      failures.push({
        index,
        domain: cookie.domain || "",
        name: cookie.name || "",
        error: error.message || String(error)
      });
    }

    progress.value = index + 1;
    if ((index + 1) % 100 === 0) {
      appendLog(`进度 ${index + 1}/${cookies.length}，成功 ${succeeded}，失败 ${failures.length}`);
    }
  }

  const after = await chrome.cookies.getAll({});
  appendLog(`完成：成功 ${succeeded}，失败 ${failures.length}。`);
  appendLog(`Chrome Cookie 总数：导入前 ${before.length}，导入后 ${after.length}。`);
  if (failures.length) {
    appendLog("前 30 条失败记录：");
    for (const failure of failures.slice(0, 30)) {
      appendLog(`#${failure.index} ${failure.domain} ${failure.name}: ${failure.error}`);
    }
  }
  appendLog("验证后请在 chrome://extensions 中移除此临时扩展。");
  fileInput.disabled = false;
  importButton.disabled = false;
});
