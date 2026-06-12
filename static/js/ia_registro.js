/* Registro rápido por áudio e imagem (IA) */
(function () {
  var painel = document.getElementById("ia-painel");
  if (!painel) return;

  var btnVoz = document.getElementById("ia-btn-voz");
  var inputFoto = document.getElementById("ia-input-foto");
  var statusEl = document.getElementById("ia-status");
  var preview = document.getElementById("ia-preview");
  var resumoEl = document.getElementById("ia-resumo");
  var transcricaoEl = document.getElementById("ia-transcricao");
  var detalhesEl = document.getElementById("ia-detalhes");
  var tipoBadge = document.getElementById("ia-tipo-badge");
  var btnSalvar = document.getElementById("ia-btn-salvar");
  var btnEditar = document.getElementById("ia-btn-editar");
  var btnDescartar = document.getElementById("ia-btn-descartar");

  var csrf = document.querySelector('meta[name="csrf-token"]');
  var resultadoAtual = null;
  var gravando = false;
  var mediaRecorder = null;
  var chunks = [];

  var ROTULOS_TIPO = {
    refeicao: "Refeição",
    sono: "Sono",
    exercicio: "Exercício",
  };

  var ROTULOS_CAMPO = {
    tipo: "Tipo",
    alimentos: "Alimentos",
    data_hora: "Data/hora",
    data: "Data",
    fome_antes: "Fome antes",
    fome_depois: "Fome depois",
    saciedade_antes: "Saciedade antes",
    saciedade_depois: "Saciedade depois",
    hora_dormir: "Dormiu",
    hora_acordar: "Acordou",
    qualidade: "Qualidade",
    duracao_minutos: "Duração (min)",
    atividade: "Atividade",
    intensidade: "Intensidade",
    observacoes: "Observações",
  };

  function csrfToken() {
    return csrf ? csrf.getAttribute("content") : "";
  }

  function mostrarStatus(msg, erro) {
    statusEl.hidden = false;
    statusEl.textContent = msg;
    statusEl.className = erro ? "ia-status ia-status-erro" : "ia-status suave";
  }

  function esconderStatus() {
    statusEl.hidden = true;
  }

  function setCarregando(ativo, msg) {
    painel.classList.toggle("ia-carregando", ativo);
    btnVoz.disabled = ativo;
    if (inputFoto) inputFoto.disabled = ativo;
    if (ativo) mostrarStatus(msg || "Processando com IA…");
    else esconderStatus();
  }

  function renderPreview(data) {
    resultadoAtual = data;
    var tipo = data.tipo || "refeicao";
    tipoBadge.textContent = ROTULOS_TIPO[tipo] || tipo;
    resumoEl.textContent = data.resumo || "Registro interpretado.";
    transcricaoEl.textContent = data.transcricao ? ("\"" + data.transcricao + "\"") : "";
    transcricaoEl.style.display = data.transcricao ? "" : "none";

    detalhesEl.innerHTML = "";
    var dados = data.dados || {};
    Object.keys(dados).forEach(function (chave) {
      var val = dados[chave];
      if (val === null || val === undefined || val === "") return;
      var li = document.createElement("li");
      li.innerHTML = "<span>" + (ROTULOS_CAMPO[chave] || chave) + "</span><strong>" + val + "</strong>";
      detalhesEl.appendChild(li);
    });

    preview.hidden = false;
    preview.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function limparPreview() {
    resultadoAtual = null;
    preview.hidden = true;
    detalhesEl.innerHTML = "";
  }

  function enviarForm(url, campo, arquivo) {
    var fd = new FormData();
    fd.append(campo, arquivo);
    return fetch(url, {
      method: "POST",
      headers: { "X-CSRFToken": csrfToken() },
      body: fd,
      credentials: "same-origin",
    }).then(function (r) { return r.json(); });
  }

  function postJson(url, body) {
    return fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken(),
      },
      body: JSON.stringify(body),
      credentials: "same-origin",
    }).then(function (r) { return r.json(); });
  }

  function pararGravacao() {
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
    }
    gravando = false;
    btnVoz.classList.remove("ia-gravando");
    btnVoz.setAttribute("aria-pressed", "false");
    btnVoz.querySelector("strong").textContent = "Falar";
    btnVoz.querySelector("span span").textContent = "Toque para gravar";
  }

  btnVoz.addEventListener("click", function () {
    if (gravando) {
      pararGravacao();
      return;
    }

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      mostrarStatus("Seu navegador não suporta gravação de áudio.", true);
      return;
    }

    navigator.mediaDevices.getUserMedia({ audio: true }).then(function (stream) {
      chunks = [];
      var mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus" : "audio/webm";
      mediaRecorder = new MediaRecorder(stream, { mimeType: mime });
      mediaRecorder.ondataavailable = function (e) {
        if (e.data.size > 0) chunks.push(e.data);
      };
      mediaRecorder.onstop = function () {
        stream.getTracks().forEach(function (t) { t.stop(); });
        var blob = new Blob(chunks, { type: mime });
        var file = new File([blob], "gravacao.webm", { type: mime });
        setCarregando(true, "Transcrevendo e interpretando…");
        enviarForm("/paciente/api/ia/audio", "audio", file).then(function (res) {
          setCarregando(false);
          if (res.ok) renderPreview(res);
          else mostrarStatus(res.erro || "Erro ao processar áudio.", true);
        }).catch(function () {
          setCarregando(false);
          mostrarStatus("Falha na conexão. Tente novamente.", true);
        });
      };
      mediaRecorder.start();
      gravando = true;
      btnVoz.classList.add("ia-gravando");
      btnVoz.setAttribute("aria-pressed", "true");
      btnVoz.querySelector("strong").textContent = "Gravando…";
      btnVoz.querySelector("span span").textContent = "Toque para parar";
      mostrarStatus("Fale agora — descreva sua refeição, sono ou exercício.");
    }).catch(function () {
      mostrarStatus("Permita o uso do microfone para gravar.", true);
    });
  });

  if (inputFoto) {
    inputFoto.addEventListener("change", function () {
      var file = inputFoto.files && inputFoto.files[0];
      inputFoto.value = "";
      if (!file) return;
      setCarregando(true, "Analisando foto…");
      enviarForm("/paciente/api/ia/imagem", "imagem", file).then(function (res) {
        setCarregando(false);
        if (res.ok) renderPreview(res);
        else mostrarStatus(res.erro || "Erro ao processar imagem.", true);
      }).catch(function () {
        setCarregando(false);
        mostrarStatus("Falha na conexão. Tente novamente.", true);
      });
    });
  }

  btnSalvar.addEventListener("click", function () {
    if (!resultadoAtual) return;
    btnSalvar.disabled = true;
    mostrarStatus("Salvando…");
    postJson("/paciente/api/ia/salvar", {
      tipo: resultadoAtual.tipo,
      dados: resultadoAtual.dados,
    }).then(function (res) {
      btnSalvar.disabled = false;
      if (res.ok && res.redirect) window.location.href = res.redirect;
      else mostrarStatus(res.erro || "Não foi possível salvar.", true);
    }).catch(function () {
      btnSalvar.disabled = false;
      mostrarStatus("Falha ao salvar.", true);
    });
  });

  btnEditar.addEventListener("click", function () {
    if (!resultadoAtual) return;
    postJson("/paciente/api/ia/editar", {
      tipo: resultadoAtual.tipo,
      dados: resultadoAtual.dados,
    }).then(function (res) {
      if (res.ok && res.redirect) window.location.href = res.redirect;
      else mostrarStatus(res.erro || "Erro ao abrir formulário.", true);
    });
  });

  btnDescartar.addEventListener("click", limparPreview);
})();
