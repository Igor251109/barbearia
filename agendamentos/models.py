from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

# Create your models here.

class Cliente(models.Model):
    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
    )

    nome = models.CharField(max_length=100)
    telefone = models.CharField(max_length=20)

    def __str__(self):
        return self.nome
    

class Servico(models.Model):
    nome = models.CharField(max_length=100)
    preco = models.DecimalField(max_digits=7, decimal_places=2)
    duracao = models.PositiveIntegerField()

    def __str__(self):
        return self.nome

class Agendamento(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    servico = models.ForeignKey(Servico, on_delete=models.PROTECT)
    data = models.DateField()
    horario = models.TimeField()

class HorarioFuncionamento(models.Model):
    DIAS_SEMANA = [(0, "Segunda-feira"),
                   (1, "Terça-feira"),
                   (2, "Quarta-feira"),
                   (3, "Quinta-feira"),
                   (4, "Sexta-feira"),
                   (5, "Sábado"),
                   (6, "Domingo")]

    dia_semana = models.IntegerField(choices=DIAS_SEMANA)  # choices é um argumento do campo IntegerField.
                                                            #Ele informa ao Django quais valores são permitidos como opções.

    abertura = models.TimeField(null=True, blank=True)  # null=True: permite armazenar NULL no banco.
    fechamento = models.TimeField(null=True, blank=True)  # blank=True: permite deixar o campo vazio nos formulários Django.
    funciona = models.BooleanField()

    def clean(self):  # clean() é um método especial do Django usado para validar os dados do modelo.
        super().clean()   # self.abertura acessa o horário de abertura daquele registro.
                          # self.fechamento acessa o horário de fechamento.

        if self.funciona:
            if not self.abertura or not self.fechamento:
                raise ValidationError("Informe os horários de abertura e fechamento."
                                      )
            if self.fechamento <= self.abertura:  # super().clean() executa a validação herdada da classe original.
                raise ValidationError("O horário de fechamento deve ser posterior ao de abertura.")
        
            # O que é raise?
            #É uma instrução do Python que lança uma exceção.
            # Nesse caso, se alguém tentar cadastrar um horário inválido, o Django recebe um ValidationError.
            # Um detalhe importante: o método clean() não é executado automaticamente quando usamos save().

    class Meta:
        constraints = [models.UniqueConstraint(fields=["dia_semana"], name="dia_semana_unico")]

        # O que isso faz?
        # Meta: configura regras internas do modelo.
        # constraints: define restrições no banco de dados.
        # UniqueConstraint: impede valores duplicados.
        # fields=["dia_semana"]: determina que o dia da semana não pode se repetir.