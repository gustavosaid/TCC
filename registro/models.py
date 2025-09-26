from django.db import models
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from random import randint
from django.utils.timezone import now  # Para timestamps com timezone-aware
import cv2, os, tempfile, numpy as np
from django.conf import settings
from django.core.files import File
from django.utils import timezone


class Funcionario(models.Model):
    slug = models.SlugField(max_length=200, unique=True)
    #foto = models.ImageField(upload_to='foto/', null=True, blank=True)  #, blank=True para aceitar nullo, fazer isso e rodar migration de novo 
    nome = models.CharField(max_length=50,  blank=True)
    cpf = models.CharField(max_length=11, unique=True) #evita cpf duplicado
    observacao = models.CharField(max_length=50, blank=True)
    dataHora = models.DateTimeField(auto_now_add=True) 

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        seq = self.nome + '_FUNC' + str(randint(10000000, 99999999))
        self.slug = slugify(seq)
        super().save(*args, **kwargs)


class ColetaFaces(models.Model):
    funcionario = models.ForeignKey(
        Funcionario,  # Referência ao modelo Funcionario
        on_delete=models.CASCADE,
        related_name='funcionario_coletas'
    )
    image = models.ImageField(upload_to='roi/')
    created_at = models.DateTimeField(default=now, editable=False)  # Campo para data e hora da criação
    observacao = models.CharField(max_length=50, null=True, blank=True)
    
    def save(self, *args, **kwargs):
            if self.observacao:
                self.observacao = self.observacao.lower()  # Converte para minúsculas antes de salvar
            super().save(*args, **kwargs)
            
    def __str__(self):
        # Evitar recursão: Exibe a hora formatada diretamente
        return f"Coleta de {self.funcionario.nome} em {self.created_at.strftime('%d/%m/%Y %H:%M:%S')} " # caso queria pode colocar aqui - Observação: {self.observacao}
    
    

class Treinamento(models.Model):
    modelo = models.FileField(upload_to='treinamento/')  # Arquivo .yml

    class Meta:
        verbose_name = 'Treinamento'
        verbose_name_plural = 'Treinamentos'

    @classmethod
    def get_instance(cls):
        """Retorna sempre o unico Treinamento """
        obj, created = cls.objects.get_or_create(id=1)
        return obj

    def __str__(self):
        return f"Treinamento {self.id}"
    
    def treinar_face(self):
    # Inicializa o classificador LBPH
        reconhecedor = cv2.face.LBPHFaceRecognizer_create()

        faces, labels = [], []
        erro_count = 0
        sucesso_count = 0

        # Processa cada imagem coletada
        for coleta in ColetaFaces.objects.all():
            image_path = os.path.join(settings.MEDIA_ROOT, coleta.image.name)

            if not os.path.exists(image_path):
                print(f"❌ Caminho não encontrado: {image_path}")
                erro_count += 1
                continue

            # Carrega a imagem
            image = cv2.imread(image_path)
            if image is None:
                print(f"❌ Erro ao carregar a imagem: {image_path}")
                erro_count += 1
                continue

            # Converte para cinza e redimensiona
            imagemFace = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            imagemFace = cv2.resize(imagemFace, (220, 220))

            faces.append(imagemFace)
            labels.append(coleta.funcionario.id)  # ID único do funcionário
            sucesso_count += 1

            print(f"✅ Imagem processada: {coleta.image.name} | Treinada em: {coleta.created_at.strftime('%H:%M')}")

        # Se não houver faces válidas, interrompe o treinamento
        if not faces:
            print("⚠ Nenhuma face válida encontrada para treinamento.")
            print(f"Imagem com erro de carregamento, {erro_count}")
            return

        try:
            # Carrega modelo existente se houver
            treinamento = Treinamento.get_instance()
            if treinamento.modelo and os.path.exists(treinamento.modelo.path):
                print("🔄 Atualizando modelo existente...")
                reconhecedor.read(treinamento.modelo.path)
                reconhecedor.update(faces, np.array(labels))
            else:
                print("🆕 Criando novo modelo...")
                reconhecedor.train(faces, np.array(labels))

            # Caminho definitivo dentro do MEDIA_ROOT/treinamento/
            model_path = os.path.join(settings.MEDIA_ROOT, 'treinamento', 'classificadorLBPH.yml')

            # Garante que a pasta existe
            os.makedirs(os.path.dirname(model_path), exist_ok=True)

            # Salva modelo treinado no disco
            reconhecedor.write(model_path)

            # Atualiza no banco vinculando o arquivo salvo
            with open(model_path, 'rb') as f:
                treinamento.modelo.save('classificadorLBPH.yml', File(f), save=True)

            print(f"✅ {sucesso_count} imagens treinadas com sucesso.")
            print(f"❌ Imagens com erro: {erro_count}")

        except Exception as e:
            print(f"❌ Erro durante o treinamento: {e}")



class RegistroEntrada(models.Model):
    funcionario = models.ForeignKey("Funcionario", on_delete=models.CASCADE)
    gabinete = models.CharField(max_length=50)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.funcionario.nome} - {self.gabinete} em {self.timestamp.strftime('%d/%m/%Y %H:%M')}"

    
