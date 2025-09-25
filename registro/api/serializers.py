from rest_framework import serializers
from registro.models import Funcionario, Treinamento, ColetaFaces

class FuncionarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Funcionario
        fields = ['id', 'slug', 'nome', 'cpf','observacao', 'dataHora']

class TreinamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Treinamento
        fields = ['id', 'modelo',]
        
class ColetaFacesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ColetaFaces
        fields = ['image','created_at', 'observacao','funcionario_id']
