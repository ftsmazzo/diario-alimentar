/* Pleno — interações leves, mobile-first */

// Sliders das escalas: mostrar o valor ao vivo
document.querySelectorAll("input[type=range][data-saida]").forEach(function (slider) {
  var saida = document.getElementById(slider.dataset.saida);
  if (!saida) return;
  var atualizar = function () { saida.textContent = slider.value; };
  slider.addEventListener("input", atualizar);
  atualizar();
});

// Exercício: lista de atividades muda conforme o tipo
var seletorTipo = document.getElementById("tipo-exercicio");
if (seletorTipo) {
  var ATIVIDADES = {
    "Aeróbico": ["Caminhada", "Corrida", "Ciclismo", "Natação", "Dança",
                 "Pular corda", "Escada", "Elíptico", "Remo", "Boxe",
                 "Futebol", "Basquete", "Tênis", "Vôlei", "Outro"],
    "Anaeróbico": ["Musculação", "Crossfit", "Calistenia", "Pilates",
                   "Treino funcional", "HIIT", "Powerlifting", "Outro"]
  };
  var campoAtividade = document.getElementById("atividade");
  var listaDatalist = document.getElementById("lista-atividades");
  seletorTipo.addEventListener("change", function () {
    if (!listaDatalist) return;
    listaDatalist.innerHTML = "";
    (ATIVIDADES[seletorTipo.value] || []).forEach(function (a) {
      var opt = document.createElement("option");
      opt.value = a;
      listaDatalist.appendChild(opt);
    });
    if (campoAtividade) campoAtividade.value = "";
  });
}

// Copiar código de convite (com fallback para mobile)
var btnCopiar = document.getElementById("copiar-codigo");
if (btnCopiar) {
  btnCopiar.addEventListener("click", function () {
    var codigo = btnCopiar.dataset.codigo || "";
    var textoOriginal = btnCopiar.textContent;
    function ok() {
      btnCopiar.textContent = "Copiado!";
      setTimeout(function () { btnCopiar.textContent = textoOriginal; }, 1800);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(codigo).then(ok).catch(function () {
        window.prompt("Copie o código:", codigo);
      });
    } else {
      window.prompt("Copie o código:", codigo);
    }
  });
}

// Cadastro: código obrigatório só para pacientes
(function () {
  var campo = document.getElementById("campo-codigo-convite");
  var input = document.getElementById("codigo_convite");
  var radios = document.querySelectorAll('input[name="tipo"]');
  if (!campo || !input || !radios.length) return;

  function atualizar() {
    var paciente = document.querySelector('input[name="tipo"][value="paciente"]').checked;
    campo.style.display = paciente ? "" : "none";
    input.required = paciente;
    if (!paciente) input.value = "";
  }

  radios.forEach(function (r) { r.addEventListener("change", atualizar); });
  atualizar();
})();

// Auto-ocultar flashes após alguns segundos
document.querySelectorAll(".flash").forEach(function (el) {
  setTimeout(function () {
    el.style.transition = "opacity .4s";
    el.style.opacity = "0";
    setTimeout(function () { el.remove(); }, 400);
  }, 5000);
});
