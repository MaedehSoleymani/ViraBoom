/* Viraboom — main.js (بدون وابستگی) */
(() => {
  "use strict";

  const FA = "۰۱۲۳۴۵۶۷۸۹";
  const AR = "٠١٢٣٤٥٦٧٨٩";
  const toLatin = (s) =>
    s.replace(/[۰-۹]/g, (d) => FA.indexOf(d)).replace(/[٠-٩]/g, (d) => AR.indexOf(d));

  // ۱) تبدیل ارقام فارسی/عربی به لاتین هنگام تایپ شماره موبایل
  document.querySelectorAll("[data-phone]").forEach((input) => {
    input.addEventListener("input", () => {
      const cleaned = toLatin(input.value).replace(/[^\d+]/g, "");
      if (cleaned !== input.value) input.value = cleaned;
    });
  });

  // ۲) نمایش/پنهان‌کردن رمز عبور
  document.querySelectorAll("[data-toggle-password]").forEach((btn) => {
    const input = btn.parentElement.querySelector("input");
    if (!input) return;
    input.setAttribute("data-pw", "");
    btn.addEventListener("click", () => {
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      btn.textContent = show ? "پنهان" : "نمایش";
      btn.setAttribute("aria-label", show ? "پنهان‌کردن رمز عبور" : "نمایش رمز عبور");
    });
  });

  // ۳) جلوگیری از ارسال دوبارهٔ فرم (دابل‌کلیک)
  document.querySelectorAll("form[data-submit-once]").forEach((form) => {
    form.addEventListener("submit", () => {
      form.querySelectorAll('button[type="submit"]').forEach((b) => {
        b.setAttribute("aria-busy", "true");
        setTimeout(() => (b.disabled = true), 0);
      });
    });
  });
  window.addEventListener("pageshow", (e) => {
    if (e.persisted) {
      document.querySelectorAll('form[data-submit-once] button[type="submit"]').forEach((b) => {
        b.disabled = false;
        b.removeAttribute("aria-busy");
      });
    }
  });

  // ۴) بستن پیام‌ها (و محو خودکار پیام‌های موفقیت)
  const dismiss = (alert) => alert && alert.remove();
  document.querySelectorAll("[data-dismiss]").forEach((btn) =>
    btn.addEventListener("click", () => dismiss(btn.closest(".alert")))
  );
  document.querySelectorAll(".messages .alert-success").forEach((a) => setTimeout(() => dismiss(a), 7000));

  // ۵) منوی موبایل
  const toggle = document.querySelector("[data-nav-toggle]");
  const nav = document.getElementById("site-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", () => {
      const open = nav.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", String(open));
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && nav.classList.contains("is-open")) {
        nav.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
        toggle.focus();
      }
    });
  }
})();
