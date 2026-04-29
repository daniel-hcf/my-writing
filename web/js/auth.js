import { api, saveToken } from "./api.js";
import { showToast } from "./utils.js";

export async function checkAuth() {
  if (!localStorage.getItem("auth_token")) return false;
  try {
    await api.getConfig();
    return true;
  } catch (e) {
    if (e.message === "UNAUTHORIZED") return false;
    return true;
  }
}

export async function showAuthScreen(onSuccess) {
  const { passwordSet } = await api.authStatus();

  const overlay = document.createElement("div");
  overlay.className = "auth-overlay";

  const card = document.createElement("div");
  card.className = "auth-card";

  const title = document.createElement("h1");
  title.className = "auth-title";
  title.textContent = passwordSet ? "登录" : "首次设置密码";

  const hint = document.createElement("p");
  hint.className = "auth-hint";
  hint.textContent = passwordSet
    ? "请输入密码以继续使用"
    : "这是你第一次使用写作练习，请设置一个访问密码（至少 4 位）";

  const input = document.createElement("input");
  input.type = "password";
  input.className = "auth-input";
  input.placeholder = passwordSet ? "密码" : "设置密码";
  input.autocomplete = passwordSet ? "current-password" : "new-password";

  const btn = document.createElement("button");
  btn.className = "btn auth-btn";
  btn.textContent = passwordSet ? "登录" : "设置并进入";

  async function submit() {
    const password = input.value.trim();
    if (!password) return;
    btn.disabled = true;
    btn.textContent = "请稍候...";
    try {
      const result = passwordSet
        ? await api.login(password)
        : await api.setup(password);
      saveToken(result.token);
      overlay.remove();
      onSuccess();
    } catch (e) {
      showToast(e.message || "操作失败", "error");
      btn.disabled = false;
      btn.textContent = passwordSet ? "登录" : "设置并进入";
      input.value = "";
      input.focus();
    }
  }

  btn.addEventListener("click", submit);
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") submit(); });

  card.append(title, hint, input, btn);
  overlay.appendChild(card);
  document.body.appendChild(overlay);
  setTimeout(() => input.focus(), 50);
}
