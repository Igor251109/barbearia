from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import Servico, Cliente, HorarioFuncionamento, Agendamento, BloqueioAgenda
from django.contrib.auth import authenticate, login, logout
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from datetime import date, datetime, timedelta
from django.http import JsonResponse

# Create your views here.

def inicio(request):
    return HttpResponse("Igor Rocha Barbearia")

def agendar(request):

    # Verifica se o cliente está autenticado.
    if not request.user.is_authenticated:
        return redirect("login_cliente")

    # Recupera o cadastro do cliente autenticado.
    cliente = get_object_or_404(Cliente, usuario=request.user)

    # Recupera o ID do serviço pelo GET ou POST.
    servico_id = request.GET.get("servico") or request.POST.get("servico")

    if not servico_id:
        return redirect("listar_servicos_publicos")

    # Busca o serviço no banco de dados.
    servico = get_object_or_404(Servico, id=servico_id)

    erro = None
    data_selecionada = ""
    horario_selecionado = ""

    # Verifica se o formulário foi enviado.
    if request.method == "POST":

        # Recupera os valores enviados pelo cliente.
        data_selecionada = request.POST.get("data", "")
        horario_selecionado = request.POST.get("horario", "")

        try:
            # Verifica se os campos foram preenchidos.
            if not data_selecionada or not horario_selecionado:
                raise ValueError

            # Converte os valores recebidos.
            data = date.fromisoformat(data_selecionada)
            horario = datetime.strptime(
                horario_selecionado, "%H:%M"
            ).time()

            # Identifica o dia da semana da data escolhida.
            dia_semana = data.weekday()

            # Verifica se a data está no passado.
            if data < date.today():
                erro = "Não é possível agendar em uma data passada."

            else:
                # Busca o horário de funcionamento do dia escolhido.
                funcionamento = HorarioFuncionamento.objects.filter(
                    dia_semana=dia_semana
                ).first()

                # Verifica se a barbearia funciona nesse dia.
                if not funcionamento or not funcionamento.funciona:
                    erro = "A barbearia não funciona neste dia."

                else:
                    # Combina a data e o horário escolhidos.
                    data_hora = datetime.combine(data, horario)

                    # Calcula o limite mínimo de antecedência.
                    limite_agendamento = datetime.now() + timedelta(hours=1)

                    if data_hora < limite_agendamento:
                        erro = (
                            "O agendamento precisa ser feito com "
                            "pelo menos 1 hora de antecedência."
                        )

                    else:
                        # Calcula quando o serviço terminará.
                        horario_fim = (
                            data_hora + timedelta(minutes=servico.duracao)
                        ).time()

                        # Verifica se o serviço cabe no expediente.
                        if (
                            horario < funcionamento.abertura
                            or horario_fim > funcionamento.fechamento
                        ):
                            erro = (
                                "O horário escolhido está fora do "
                                "funcionamento da barbearia."
                            )

                        else:
                            # Busca os bloqueios existentes na data escolhida.
                            bloqueios = BloqueioAgenda.objects.filter(data=data)

                            # Verifica se o horário escolhido coincide com algum bloqueio.
                            for bloqueio in bloqueios:

                                # Calcula o início do bloqueio.
                                bloqueio_inicio = datetime.combine(
                                    data,
                                    bloqueio.horario_inicio
                                )

                                # Calcula o fim do bloqueio.
                                bloqueio_fim = datetime.combine(
                                    data,
                                    bloqueio.horario_fim
                                )

                                # Verifica se os períodos se sobrepõem.
                                if (
                                    data_hora < bloqueio_fim
                                    and data_hora + timedelta(minutes=servico.duracao) > bloqueio_inicio
                                ):
                                    erro = (
                                        "Este horário está bloqueado. "
                                        "Escolha outro."
                                    )
                                    break

                            # Continua somente se não houver bloqueio.
                            if erro is None:

                                # Busca os agendamentos existentes na mesma data.
                                agendamentos = Agendamento.objects.filter(
                                    data=data
                                ).select_related("servico")

                                # Calcula o início e o término do novo agendamento.
                                novo_inicio = data_hora
                                novo_fim = novo_inicio + timedelta(
                                    minutes=servico.duracao
                                )

                                # Verifica se existe conflito de horário.
                                for agendamento in agendamentos:

                                    # Calcula o início do agendamento existente.
                                    existente_inicio = datetime.combine(
                                        data,
                                        agendamento.horario
                                    )

                                    # Calcula o término do agendamento existente.
                                    existente_fim = existente_inicio + timedelta(
                                        minutes=agendamento.servico.duracao
                                    )

                                    # Verifica se os horários se sobrepõem.
                                    if (
                                        novo_inicio < existente_fim
                                        and novo_fim > existente_inicio
                                    ):
                                        erro = (
                                            "Este horário já está ocupado. "
                                            "Escolha outro."
                                        )
                                        break

                                # Salva somente se todas as validações passaram.
                                if erro is None:
                                    with transaction.atomic():

                                        Agendamento.objects.create(
                                            cliente=cliente,
                                            servico=servico,
                                            data=data,
                                            horario=horario
                                        )

                                    return redirect("listar_servicos_publicos")

        except ValueError:
            erro = "Informe uma data e um horário válidos."

    # Envia os dados para o template.
    return render(
        request,
        "agendamentos/agendar.html",
        {
            "servico": servico,
            "erro": erro,
            "data_selecionada": data_selecionada,
            "horario_selecionado": horario_selecionado
        }
    )

@staff_member_required(login_url="login_profissional")
def servicos(request):
    if request.method == "POST":
        nome = request.POST.get("nome")
        preco = request.POST.get("preco")
        duracao = request.POST.get("duracao")

        if not nome.strip() or not preco or not duracao:
            return render(request, "agendamentos/servicos.html", {
    "servicos": Servico.objects.all(),
    "erro": "Dados não preenchidos. Tente novamente."
})

        try:
            if float(preco) < 0 or int(duracao) <= 0:
                return render(request, "agendamentos/servicos.html", {
            "servicos": Servico.objects.all(),
            "erro": "Preço ou duração inválidos."
        })
        except ValueError:
            return render(request, "agendamentos/servicos.html", {
                        "servicos": Servico.objects.all(),
                        "erro": "Preço ou duração inválidos."
                    })

        
        else:
            Servico.objects.create(nome=nome, preco=preco, duracao=duracao)
            return redirect("servicos")

    servicos = Servico.objects.all()

    return render(request, "agendamentos/servicos.html", {
        "servicos": servicos})

@staff_member_required(login_url="login_profissional")
def editar_servico(request, id):
    servico = Servico.objects.get(id=id)

    if request.method == "POST":
        nome = request.POST.get("nome")
        preco = request.POST.get("preco")
        duracao = request.POST.get("duracao")

        # Verificar campos vazios
        if not nome or not nome.strip() or not preco or not duracao:
            return render(request, "agendamentos/editar_servico.html", {
                "servico": servico,
                "erro": "Preencha todos os campos."
            })

        # Validar valores numéricos
        try:
            preco = float(preco)
            duracao = int(duracao)

            if preco < 0 or duracao <= 0:
                return render(request, "agendamentos/editar_servico.html", {
                    "servico": servico,
                    "erro": "Preço ou duração inválidos."
                })

        except ValueError:
            return render(request, "agendamentos/editar_servico.html", {
                "servico": servico,
                "erro": "Digite valores numéricos válidos."
            })

        # Atualizar serviço
        servico.nome = nome.strip()
        servico.preco = preco
        servico.duracao = duracao

        servico.save()

        return redirect("servicos")

    return render(request, "agendamentos/editar_servico.html", {
        "servico": servico
    })

@staff_member_required(login_url="login_profissional")
def excluir_servico(request, id):
    servico = Servico.objects.get(id=id)

    if request.method == "POST":
        servico.delete()
        return redirect("servicos")

def login_profissional(request):
    erro = None

    if request.method == "POST":
        usuario = request.POST.get("usuario")
        senha = request.POST.get("senha")

        usuario_autenticado = authenticate(request, username=usuario, password=senha)

        if usuario_autenticado is not None and usuario_autenticado.is_staff:
            login(request, usuario_autenticado)
            return redirect("servicos")
        else:
            erro = "Usuário ou senha inválidos."

    return render(request, "agendamentos/login_profissional.html", {
        "erro": erro
    })

def logout_profissional(request):
    logout(request)
    return redirect("login_profissional")

def listar_servicos_publicos(request):
   servicos = Servico.objects.all()

   return render(request, "agendamentos/listar_servicos.html", {"servicos": servicos})

def cadastrar_cliente(request):
    erro = None

    if request.method == "POST":
        nome = request.POST.get("nome")
        telefone = request.POST.get("telefone")
        senha = request.POST.get("senha")

        if not nome or not telefone or not senha:
            erro = "Preencha todos os campos."

        elif Cliente.objects.filter(telefone=telefone).exists():
            erro = "Este telefone já está cadastrado."

        if erro is None:
            usuario = User.objects.create_user(username=telefone, password=senha)

            Cliente.objects.create(usuario=usuario, nome=nome, telefone=telefone)
            return redirect("listar_servicos_publicos")

    return render(request, "agendamentos/cadastrar_cliente.html", {
    "erro": erro
})

def login_cliente(request):
    erro = None

    if request.method == "POST":
        telefone = request.POST.get("telefone")
        senha = request.POST.get("senha")

        usuario_autenticado = authenticate(request, username=telefone, password=senha)

        if usuario_autenticado is not None:
            cliente_existe = Cliente.objects.filter(usuario=usuario_autenticado).exists()

            if cliente_existe:
                login(request, usuario_autenticado)
                return redirect("listar_servicos_publicos")

        erro = "Telefone ou senha inválidos."

    return render(request, "agendamentos/login_cliente.html", {
        "erro": erro})



@staff_member_required(login_url="login_profissional")
def gerenciar_horarios(request):

    erro = None

    dados_enviados = {}

    # Verifica se o formulário foi enviado.
    if request.method == "POST":

        try:
            # Garante que os sete dias sejam salvos como uma única operação.
            with transaction.atomic():

                # Percorre os sete dias da semana.
                for numero, nome in HorarioFuncionamento.DIAS_SEMANA:

                    # Verifica se o checkbox foi marcado.
                    funciona = request.POST.get(f"funciona_{numero}") == "on"

                    # Recupera os horários enviados pelo formulário.
                    abertura = request.POST.get(f"abertura_{numero}") or None
                    fechamento = request.POST.get(f"fechamento_{numero}") or None

                    # Procura o registro do dia ou cria um novo.
                    horario, criado = HorarioFuncionamento.objects.get_or_create(
                        dia_semana=numero,
                        defaults={
                            "funciona": funciona,
                            "abertura": abertura,
                            "fechamento": fechamento
                        }
                    )

                    # Atualiza os dados do registro.
                    horario.funciona = funciona
                    horario.abertura = abertura
                    horario.fechamento = fechamento

                    # Valida os dados antes de salvar.
                    horario.full_clean()

                    # Salva no banco de dados.
                    horario.save()

            # Se tudo deu certo, retorna à página.
            return redirect("horarios")

        except ValidationError as e:
            # Guarda as mensagens de validação para exibir no HTML.
            erro = " ".join(e.messages)
            dados_enviados = request.POST

    # Busca os horários cadastrados.
    horarios = HorarioFuncionamento.objects.all()

    # Organiza os registros pelo número do dia.
    horarios_por_dia = {
        horario.dia_semana: horario
        for horario in horarios
    }

    # Monta a lista com os sete dias.
   # Monta a lista com os sete dias.
    dias = []

    for numero, nome in HorarioFuncionamento.DIAS_SEMANA:

        horario = horarios_por_dia.get(numero)

        # Recupera os valores enviados pelo formulário, se houver erro.
        if dados_enviados:
            abertura = dados_enviados.get(f"abertura_{numero}", "")
            fechamento = dados_enviados.get(f"fechamento_{numero}", "")
            funciona = dados_enviados.get(f"funciona_{numero}") == "on"

        # Caso contrário, utiliza os valores salvos no banco.
        else:
            abertura = horario.abertura.strftime("%H:%M") if horario and horario.abertura else ""
            fechamento = horario.fechamento.strftime("%H:%M") if horario and horario.fechamento else ""
            funciona = horario.funciona if horario else False

        dias.append({
            "numero": numero,
            "nome": nome,
            "abertura": abertura,
            "fechamento": fechamento,
            "funciona": funciona
        })

    return render(request, "agendamentos/gerenciar_horarios.html", {
    "dias": dias,
    "erro": erro,
    "dados_enviados": dados_enviados
})


def horarios_disponiveis(request):

    # Recupera a data e o serviço enviados pelo JavaScript.
    data_selecionada = request.GET.get("data")
    servico_id = request.GET.get("servico")

    # Verifica se os dois valores foram enviados.
    if not data_selecionada or not servico_id:
        return JsonResponse({"horarios": []})

    try:
        # Converte a data recebida para um objeto date.
        data = date.fromisoformat(data_selecionada)

        # Busca o serviço no banco de dados.
        servico = get_object_or_404(Servico, id=servico_id)

    except ValueError:
        return JsonResponse({"horarios": []})

    # Impede consultas para datas passadas.
    if data < date.today():
        return JsonResponse({"horarios": []})

    # Descobre o dia da semana da data escolhida.
    dia_semana = data.weekday()

    # Busca o funcionamento da barbearia nesse dia.
    funcionamento = HorarioFuncionamento.objects.filter(
        dia_semana=dia_semana
    ).first()

    # Verifica se a barbearia funciona nesse dia.
    if not funcionamento or not funcionamento.funciona:
        return JsonResponse({"horarios": []})

    agendamentos = Agendamento.objects.filter(data=data).select_related("servico")
    bloqueios = BloqueioAgenda.objects.filter(data=data)

    # Define o início e o fim do expediente.
    inicio = datetime.combine(data, funcionamento.abertura)
    fechamento = datetime.combine(data, funcionamento.fechamento)

    # Define a duração do serviço.
    duracao = timedelta(minutes=servico.duracao)

    # Define a antecedência mínima de uma hora.
    limite = datetime.now() + timedelta(hours=1)

    # Começa a gerar horários a partir da abertura.
    horario_atual = inicio

    # Lista que armazenará os horários disponíveis.
    horarios = []

    # Continua enquanto o serviço inteiro couber no expediente.
    while horario_atual + duracao <= fechamento:

    # Verifica se existe pelo menos uma hora de antecedência.
        if horario_atual >= limite:

            # Considera inicialmente que o horário está disponível.
            disponivel = True

            # Calcula o término do novo agendamento.
            novo_fim = horario_atual + duracao

            # Percorre os agendamentos existentes nessa data.
            for agendamento in agendamentos:

                # Calcula o início do agendamento existente.
                existente_inicio = datetime.combine(data,agendamento.horario)

                # Calcula o término do agendamento existente.
                existente_fim = existente_inicio + timedelta(minutes=agendamento.servico.duracao)

                # Percorre os bloqueios existentes nessa data.
                for bloqueio in bloqueios:

                    # Combina a data com o início e o fim do bloqueio.
                    bloqueio_inicio = datetime.combine(
                        data,
                        bloqueio.horario_inicio
                    )

                    bloqueio_fim = datetime.combine(
                        data,
                        bloqueio.horario_fim
                    )

                    # Verifica se o horário pretendido coincide com um bloqueio.
                    if horario_atual < bloqueio_fim and novo_fim > bloqueio_inicio:
                        disponivel = False
                        break

                # Verifica se os períodos se sobrepõem.
                if horario_atual < existente_fim and novo_fim > existente_inicio:
                    disponivel = False
                    break

            # Adiciona somente horários disponíveis.
            if disponivel:
                horarios.append(horario_atual.strftime("%H:%M"))

        # Avança 15 minutos, independentemente de estar disponível.
        horario_atual += timedelta(minutes=15)


# Exibe os horários encontrados no terminal.
    print("Horários encontrados:", horarios)

# Retorna os horários para o JavaScript.
    return JsonResponse({"horarios": horarios})





@staff_member_required(login_url="login_profissional")
def gerenciar_bloqueios(request):

    erro = None

    if request.method == "POST":

        data = request.POST.get("data")
        horario_inicio = request.POST.get("horario_inicio")
        horario_fim = request.POST.get("horario_fim")
        motivo = request.POST.get("motivo", "")

        try:
            bloqueio = BloqueioAgenda(
                data=data,
                horario_inicio=horario_inicio,
                horario_fim=horario_fim,
                motivo=motivo
            )

            bloqueio.full_clean()
            bloqueio.save()

            return redirect("bloqueios")

        except ValidationError as e:
            erro = " ".join(e.messages)

    bloqueios = BloqueioAgenda.objects.order_by(
        "data", "horario_inicio"
    )

    return render(
        request,
        "agendamentos/gerenciar_bloqueios.html",
        {
            "bloqueios": bloqueios,
            "erro": erro
        }
    )

def meus_agendamentos(request):

    if not request.user.is_authenticated:
        return redirect("login_cliente")

    cliente = get_object_or_404(
        Cliente,
        usuario=request.user
    )

    agendamentos = Agendamento.objects.filter(
        cliente=cliente
    ).select_related("servico").order_by("data", "horario")

    return render(
        request,
        "agendamentos/meus_agendamentos.html",
        {
            "agendamentos": agendamentos
        }
    )

def cancelar_agendamento(request, id):

    # Verifica se o cliente está autenticado.
    if not request.user.is_authenticated:
        return redirect("login_cliente")

    if request.method != "POST":
        return redirect("meus_agendamentos")

    # Recupera o cadastro do cliente autenticado.
    cliente = get_object_or_404(
        Cliente,
        usuario=request.user
    )

    # Busca somente o agendamento pertencente a esse cliente.
    agendamento = get_object_or_404(
        Agendamento,
        id=id,
        cliente=cliente
    )

    # Combina a data e o horário do agendamento.
    data_hora = datetime.combine(
        agendamento.data,
        agendamento.horario
    )

    # Calcula o limite mínimo para cancelamento.
    limite_cancelamento = datetime.now() + timedelta(hours=1)

    # Verifica se ainda existe uma hora de antecedência.
    if data_hora < limite_cancelamento:
        return redirect("meus_agendamentos")

    # Exclui o agendamento do banco de dados.
    agendamento.delete()

    # Retorna à página de reservas.
    return redirect("meus_agendamentos")



@staff_member_required(login_url="login_profissional")
def gerenciar_agendamentos(request):

    # Recupera a data enviada pelo formulário.
    data_selecionada = request.GET.get("data", "")

    # Busca todos os agendamentos.
    agendamentos = Agendamento.objects.select_related(
        "cliente",
        "servico"
    )

    # Filtra os agendamentos caso uma data tenha sido selecionada.
    if data_selecionada:
        agendamentos = agendamentos.filter(
            data=data_selecionada
        )

    # Organiza os agendamentos por data e horário.
    agendamentos = agendamentos.order_by("data", "horario")

    # Envia os dados para o template.
    return render(
        request,
        "agendamentos/gerenciar_agendamentos.html",
        {
            "agendamentos": agendamentos,
            "data_selecionada": data_selecionada
        }
    )

@staff_member_required(login_url="login_profissional")
def cancelar_agendamento_profissional(request, id):

    # Aceita somente requisições POST.
    if request.method != "POST":
        return redirect("gerenciar_agendamentos")

    # Busca o agendamento pelo ID.
    agendamento = get_object_or_404(
        Agendamento,
        id=id
    )

    # Exclui o agendamento.
    agendamento.delete()

    # Retorna à página de gerenciamento.
    return redirect("gerenciar_agendamentos")