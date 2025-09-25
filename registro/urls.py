from django.urls import path
from .views import (criar_funcionario, criar_coleta_faces, detectar_camera,
                    buscar_funcionario, encontra_funcionario,camera_reconhecimento,tela_reconhecimento, seleciona_gabinete, verifica_status_reconhecimento )

urlpatterns = [
    path('', criar_funcionario, name='criar_funcionario'),
    path('criar_coleta_faces/<int:funcionario_id>', criar_coleta_faces, name='criar_coleta_faces'),
    path('detectar_camera/', detectar_camera, name='detectar_camera'),
    path('buscar_funcionario/',buscar_funcionario, name='buscar_funcionario'),
    path('encontra_funcionario/',encontra_funcionario, name='encontra_funcionario'),
    path('camera_reconhecimento/',camera_reconhecimento, name='camera_reconhecimento'),
    path('tela_reconhecimento/',tela_reconhecimento, name='tela_reconhecimento'),
    path('seleciona_gabinete/<int:funcionario_id>/',seleciona_gabinete, name='seleciona_gabinete'),
    path('verifica_status/', verifica_status_reconhecimento, name='verifica_status_reconhecimento'),
]

