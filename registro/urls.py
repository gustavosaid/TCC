from django.urls import path
from .views import (criar_funcionario, criar_coleta_faces,
                    buscar_funcionario, encontra_funcionario,tela_reconhecimento, seleciona_gabinete, verifica_status_reconhecimento, 
                    listar_entradas,carrega_entrada, processar_frame_reconhecimento, api_coletar_frame, api_disparar_treinamento )

urlpatterns = [
    path('', criar_funcionario, name='criar_funcionario'),
    path('criar_coleta_faces/<int:funcionario_id>', criar_coleta_faces, name='criar_coleta_faces'),
    #path('detectar_camera/', detectar_camera, name='detectar_camera'),
    path('buscar_funcionario/',buscar_funcionario, name='buscar_funcionario'),
    path('encontra_funcionario/',encontra_funcionario, name='encontra_funcionario'),
    #path('camera_reconhecimento/',camera_reconhecimento, name='camera_reconhecimento'),
    path('tela_reconhecimento/',tela_reconhecimento, name='tela_reconhecimento'),
    path('seleciona_gabinete/<int:funcionario_id>/',seleciona_gabinete, name='seleciona_gabinete'),
    path('verifica_status/', verifica_status_reconhecimento, name='verifica_status_reconhecimento'),
    path('entradas/', listar_entradas, name='listar_entradas'),
    path('tela_entrada/', carrega_entrada, name='carrega_entrada'),
    path('api/processar_frame_reconhecimento/', processar_frame_reconhecimento, name='processar_frame_reconhecimento'),
    path('api/coletar_frame/', 
         api_coletar_frame, 
         name='api_coletar_frame'),

    path('api/disparar_treinamento/', api_disparar_treinamento, name='api_disparar_treinamento'),
]

