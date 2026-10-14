/*
 * auth.js - the log-in page: log in, create account, WhatsApp code, forgot password.
 * Like app.js, it only talks to MarketAPI (api.js), never to the data directly.
 *
 * The page has several <form data-panel="..."> and shows one at a time:
 *   login  -> register -> code -> (done, go back to the page you came from)
 *   login  -> forgot   -> code -> newpw -> login
 */
(function () {
  "use strict";
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
  const body = document.body;
  const NEXT = body.dataset.next || "/";

  // ---------- Which form is showing ----------
  const URLS = { login: "/login/", register: "/register/", forgot: "/forgot/" };
  let codeFor = "register";   // the code panel is used for "register" and for "reset"

  function show(panel, push = true) {
    $$("[data-panel]").forEach((f) => (f.hidden = f.dataset.panel !== panel));
    const form = $(`[data-panel="${panel}"]`);
    clearErrors(form);
    document.title = { login: "Log in", register: "Create an account", forgot: "Reset your password",
      code: "Check your WhatsApp", newpw: "New password" }[panel] + ": Murimi Market";
    if (push && URLS[panel] && location.pathname !== URLS[panel]) history.pushState({ panel }, "", URLS[panel] + location.search);
    const first = form.querySelector("input:not([type=radio])");
    if (first && push) first.focus();
  }
  window.addEventListener("popstate", (e) => show((e.state && e.state.panel) || body.dataset.mode, false));

  // Links like <a data-go="register"> switch forms without a page load.
  $$("[data-go]").forEach((a) => a.addEventListener("click", (e) => {
    e.preventDefault();
    show(a.dataset.go === "back" ? codeFor === "reset" ? "forgot" : "register" : a.dataset.go);
  }));

  // ---------- Errors: under each field, plus one line for the whole form ----------
  function clearErrors(form) {
    $$(".field-error", form).forEach((el) => (el.textContent = ""));
    $$("[aria-invalid]", form).forEach((el) => el.removeAttribute("aria-invalid"));
    $(".form-error", form).textContent = "";
  }
  function showErrors(form, body) {
    const errs = body.errors || {};
    let firstBad = null;
    Object.entries(errs).forEach(([field, msg]) => {
      const slot = $(`.field-error[data-for="${field}"]`, form);
      const input = form.elements[field];
      if (slot) slot.textContent = msg;
      if (input && input.setAttribute) { input.setAttribute("aria-invalid", "true"); firstBad = firstBad || input; }
    });
    // Only show the general line when no field explains the problem.
    if (!Object.keys(errs).length || !firstBad) $(".form-error", form).textContent = body.error || "Something went wrong. Please try again.";
    if (firstBad) firstBad.focus();
  }

  // Disable the button while waiting, so nobody sends twice.
  async function busy(form, label, work) {
    const btn = form.querySelector('button[type="submit"]');
    const old = btn.textContent;
    btn.disabled = true; btn.textContent = label;
    try { return await work(); } finally { btn.disabled = false; btn.textContent = old; }
  }

  function toast(msg) {
    const t = $("#toast");
    t.textContent = msg; t.hidden = false;
    clearTimeout(toast._t); toast._t = setTimeout(() => (t.hidden = true), 4500);
  }

  // ---------- Show / hide password ----------
  $$(".pw-eye").forEach((b) => b.addEventListener("click", () => {
    const input = b.parentElement.querySelector("input");
    const showing = input.type === "text";
    input.type = showing ? "password" : "text";
    b.setAttribute("aria-pressed", String(!showing));
    b.setAttribute("aria-label", showing ? "Show password" : "Hide password");
  }));

  // ---------- Log in ----------
  $("#loginForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target; clearErrors(f);
    const res = await busy(f, "Logging in…", () => MarketAPI.login({ identifier: f.identifier.value, password: f.password.value }));
    if (!res.ok) return showErrors(f, res.body);
    goHome(`Welcome back, ${res.body.user.name.split(" ")[0]}.`);
  });

  // ---------- Create account ----------
  $("#registerForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target; clearErrors(f);
    const data = Object.fromEntries(new FormData(f));
    const res = await busy(f, "Sending code…", () => MarketAPI.register(data));
    if (!res.ok) return showErrors(f, res.body);
    startCode("register", res.body.phone);
  });

  // ---------- Forgot password ----------
  $("#forgotForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target; clearErrors(f);
    const res = await busy(f, "Sending code…", () => MarketAPI.forgotPassword(f.phone.value));
    if (!res.ok) return showErrors(f, res.body);
    startCode("reset", res.body.phone);
  });

  // ---------- WhatsApp code ----------
  let timer = null;
  function startCode(why, phone) {
    codeFor = why;
    $("#codePhone").textContent = MarketAPI.prettyPhone(phone);
    $("#codeHint").textContent = `Demo: no WhatsApp message is sent yet. Use ${MarketAPI.demoCode}. (The real server prints the code in its window, like the Hub.)`;
    $("#codeForm").code.value = "";
    show("code");
    countdown(60);
  }
  function countdown(sec) {
    const btn = $("#resendBtn");
    clearInterval(timer);
    btn.disabled = true;
    btn.innerHTML = `Send again in <span id="resendIn">${sec}</span>s`;
    timer = setInterval(() => {
      sec -= 1;
      if (sec <= 0) { clearInterval(timer); btn.disabled = false; btn.textContent = "Send the code again"; return; }
      $("#resendIn").textContent = sec;
    }, 1000);
  }
  $("#resendBtn").addEventListener("click", async () => {
    const res = await MarketAPI.resendCode();
    if (res.ok) { toast("A new code is on its way."); countdown(60); } else { toast(res.body.error); }
  });
  // Only digits in the code box; submit by itself once all 6 are typed.
  $("#codeForm").code.addEventListener("input", (e) => {
    e.target.value = e.target.value.replace(/\D/g, "").slice(0, 6);
    if (e.target.value.length === 6) $("#codeForm").requestSubmit();
  });
  $("#codeForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target; clearErrors(f);
    const res = await busy(f, "Checking…", () => MarketAPI.verifyCode(f.code.value));
    if (!res.ok) return showErrors(f, res.body);
    clearInterval(timer);
    if (res.body.next === "new_password") return show("newpw");
    goHome(`Your account is ready, ${res.body.user.name.split(" ")[0]}. Welcome to Murimi.`);
  });

  // ---------- New password ----------
  $("#newPwForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target; clearErrors(f);
    const res = await busy(f, "Saving…", () => MarketAPI.setNewPassword(f.password.value));
    if (!res.ok) return showErrors(f, res.body);
    show("login");
    toast("Password changed. You can log in now.");
  });

  // ---------- Done: back to where the person came from ----------
  function goHome(message) {
    try { sessionStorage.setItem("murimi-flash", message); } catch (e) { /* fine */ }
    location.href = NEXT;
  }

  // ---------- Start ----------
  // If already logged in, there is nothing to do here.
  MarketAPI.me().then(({ user }) => {
    if (user && body.dataset.mode === "login") {
      $(".form-error", $("#loginForm")).textContent = `You're already logged in as ${user.name}.`;
    }
  });
  show(body.dataset.mode, false);
  history.replaceState({ panel: body.dataset.mode }, "", location.href);
})();
