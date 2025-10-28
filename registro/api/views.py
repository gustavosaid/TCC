from rest_framework import viewsets
from registro.api.serializers import FuncionarioSerializer, TreinamentoSerializer, ColetaFacesSerializer, RegistroEntradaSerializer
from registro.models import Funcionario, Treinamento, ColetaFaces, RegistroEntrada

class FuncionarioViewSet(viewsets.ModelViewSet):
    queryset = Funcionario.objects.all()
    serializer_class = FuncionarioSerializer

class TreinamentoViewSet(viewsets.ModelViewSet):
    queryset = Treinamento.objects.all()
    serializer_class = TreinamentoSerializer
    
class ColetaFacesViewSet(viewsets.ModelViewSet):
    queryset = ColetaFaces.objects.all()
    serializer_class = ColetaFacesSerializer

class RegistroEntradaViewSet(viewsets.ModelViewSet):
    queryset = RegistroEntrada.objects.all()
    serializer_class = RegistroEntradaSerializer