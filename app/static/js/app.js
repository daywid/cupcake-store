// Comportamentos simples de interface: máscaras, ViaCEP, copiar PIX e confirmações.
(function () {
  const digitos = (v) => v.replace(/\D/g, "");
  const mascaras = {
    cpf: (v) => digitos(v).slice(0, 11).replace(/(\d{3})(\d)/, "$1.$2").replace(/(\d{3})(\d)/, "$1.$2").replace(/(\d{3})(\d{1,2})$/, "$1-$2"),
    cep: (v) => digitos(v).slice(0, 8).replace(/(\d{5})(\d)/, "$1-$2"),
    telefone: (v) => digitos(v).slice(0, 11).replace(/(\d{2})(\d)/, "($1) $2").replace(/(\d{4,5})(\d{4})$/, "$1-$2"),
    cartao: (v) => digitos(v).slice(0, 19).replace(/(\d{4})(?=\d)/g, "$1 "),
    validade: (v) => digitos(v).slice(0, 4).replace(/(\d{2})(\d)/, "$1/$2"),
  };
  document.querySelectorAll("[data-mask]").forEach((el) => {
    const fn = mascaras[el.dataset.mask];
    if (!fn) return;
    el.addEventListener("input", () => { el.value = fn(el.value); });
    el.value = fn(el.value);
  });

  // Preenche o endereço pelo CEP (ViaCEP). Se falhar, o usuário digita manualmente.
  document.querySelectorAll("[data-viacep]").forEach((el) => {
    el.addEventListener("blur", async () => {
      const cep = digitos(el.value);
      if (cep.length !== 8) return;
      try {
        const r = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
        const d = await r.json();
        if (d.erro) return;
        const set = (id, v) => { const f = document.getElementById(id); if (f && !f.value) f.value = v || ""; };
        set("logradouro", d.logradouro); set("bairro", d.bairro); set("cidade", d.localidade); set("uf", d.uf);
        document.getElementById("numero")?.focus();
      } catch (_) { /* sem internet: segue manual */ }
    });
  });

  document.querySelectorAll("[data-copiar]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const alvo = document.querySelector(btn.dataset.copiar);
      try { await navigator.clipboard.writeText(alvo.value); } catch (_) { alvo.select(); document.execCommand("copy"); }
      const original = btn.innerHTML;
      btn.innerHTML = '<i class="bi bi-check2"></i> Copiado';
      setTimeout(() => { btn.innerHTML = original; }, 2000);
    });
  });

  document.querySelectorAll("form[data-confirmar]").forEach((f) => {
    f.addEventListener("submit", (e) => { if (!confirm(f.dataset.confirmar)) e.preventDefault(); });
  });

  // Checkout: ao trocar o endereço, recalcula a taxa de entrega.
  document.querySelectorAll("[data-recalcular]").forEach((el) => {
    el.addEventListener("change", () => el.form.requestSubmit());
  });

  // Login: preenche e-mail e senha com o usuário de teste escolhido.
  document.querySelectorAll("[data-login-teste]").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.getElementById("email").value = btn.dataset.loginTeste;
      document.getElementById("senha").value = btn.dataset.senhaTeste;
      document.querySelector("form button.btn-brand")?.focus();
    });
  });
})();
