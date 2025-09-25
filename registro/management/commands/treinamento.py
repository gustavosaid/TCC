import os
import numpy as np
import cv2
import tempfile
from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from registro.models import ColetaFaces, Treinamento

class Command(BaseCommand):
    help = "Treina o classificador LBPH para reconhecimento facial"

    def handle(self, *args, **kwargs):
        self.treinamento_face()

    def treinamento_face(self):
        self.stdout.write(self.style.WARNING("Iniciando treinamento com a base de informações"))
        print("Versão do OpenCV:", cv2.__version__)

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
            self.stdout.write(self.style.ERROR(f"Imagens com erro de carregamento: {erro_count}"))
            return

        try:
            # Se já existe um modelo salvo, carrega e faz update
            treinamento = Treinamento.objects.first()
            if treinamento and treinamento.modelo:
                model_path = os.path.join(settings.MEDIA_ROOT, treinamento.modelo.name)
                if os.path.exists(model_path):
                    print("Modelo existente encontrado. Atualizando com novas imagens...")
                    reconhecedor.read(model_path)
                    reconhecedor.update(faces, np.array(labels))
                else:
                    print("Não encontrado no disco. Criando")
                    reconhecedor.train(faces, np.array(labels))
            else:
                print("ℹ Nenhum modelo anterior. Criando ")
                reconhecedor.train(faces, np.array(labels))

            # Salva o modelo treinado em um arquivo temporário
            with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
                model_filename = tmpfile.name
                reconhecedor.write(model_filename)

            # Salva no banco
            with open(model_filename, 'rb') as f:
                treinamento, _ = Treinamento.objects.update_or_create(id=treinamento.id, 
                                defaults={'modelo': File(f, name='classificadorLBPH.yml')})
                treinamento.modelo.save('classificadorLBPH.yml', File(f), save=True)

            # Mensagens finais
            self.stdout.write(self.style.SUCCESS(f"{sucesso_count} imagens treinadas com sucesso."))
            self.stdout.write(self.style.ERROR(f"Imagens com erro de carregamento: {erro_count}"))
            self.stdout.write(self.style.SUCCESS("TREINAMENTO EFETUADO COM SUCESSO"))

        except Exception as e:
            print(f"❌ Erro durante o treinamento: {e}")
