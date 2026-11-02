from django.urls import path
from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("agendar/", views.agendar, name="agendar"),
    path("servicos/", views.servicos, name="servicos"),
    path("servicos/editar/<int:id>/", views.editar_servico, name="editar_servico"),
    path("servicos/excluir/<int:id>/", views.excluir_servico,name="excluir_servico"),
    path("profissional/login/", views.login_profissional, name="login_profissional"),
    path("profissional/logout/", views.logout_profissional, name="logout_profissional"),
    path("servicos-disponiveis/", views.listar_servicos_publicos, name="listar_servicos_publicos"),
    path("cliente/cadastrar/", views.cadastrar_cliente, name="cadastrar_cliente"),
    path("cliente/login/", views.login_cliente, name="login_cliente"),
    path("horarios/", views.gerenciar_horarios, name="horarios")
]