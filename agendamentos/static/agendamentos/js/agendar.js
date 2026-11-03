// Localiza o campo onde o cliente escolhe a data.
const campoData = document.getElementById("data");

// Recupera o ID do serviço escolhido.
const campoServico = document.getElementById("servico");

// Localiza a área onde os horários serão exibidos.
const areaHorarios = document.getElementById("horarios-disponiveis");

// Localiza o campo oculto que armazenará o horário escolhido.
const campoHorario = document.getElementById("horario");


// Detecta quando o cliente seleciona ou altera uma data.
campoData.addEventListener("change", function() {

    // Recupera a data escolhida pelo cliente.
    const data = campoData.value;

    // Limpa o horário anteriormente selecionado.
    campoHorario.value = "";

    // Limpa os horários que estavam sendo exibidos.
    areaHorarios.innerHTML = "";

    // Envia uma requisição ao Django com a data selecionada.
    fetch(`/horarios-disponiveis/?data=${data}&servico=${campoServico.value}`)

        // Converte a resposta do Django para JSON.
        .then(resposta => resposta.json())

        // Recebe e utiliza os dados enviados pelo Django.
        .then(dados => {

            // Percorre todos os horários recebidos.
            dados.horarios.forEach(function(horario) {

                // Cria um novo botão para o horário.
                const botao = document.createElement("button");

                // Define o texto que aparecerá no botão.
                botao.textContent = horario;

                // Impede que o botão envie o formulário.
                botao.type = "button";

                // Detecta quando o cliente seleciona esse horário.
                botao.addEventListener("click", function() {

                    // Guarda o horário escolhido no campo oculto.
                    campoHorario.value = horario;

                });

                // Adiciona o botão à página.
                areaHorarios.appendChild(botao);

            });

        });

});