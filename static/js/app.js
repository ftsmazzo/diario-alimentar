/* Pleno — interações leves, sem framework. */

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

// Copiar código de convite
var btnCopiar = document.getElementById("copiar-codigo");
if (btnCopiar) {
  btnCopiar.addEventListener("click", function () {
    var codigo = btnCopiar.dataset.codigo || "";
    navigator.clipboard.writeText(codigo).then(function () {
      btnCopiar.textContent = "Copiado!";
      setTimeout(function () { btnCopiar.textContent = "Copiar código"; }, 1800);
    });
  });
}
