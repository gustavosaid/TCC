import cv2
import os 
import re
import hashlib
from django.shortcuts import render, redirect
from django.http import StreamingHttpResponse, JsonResponse
from .forms import FuncionarioForm
from .models import Funcionario, ColetaFaces, Treinamento, RegistroEntrada
from .camera import VideoCamera
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
import tempfile
from django.core.files import File
import tkinter as tk
from tkinter import simpledialog
from django.utils import timezone
from .forms import ColetaEntradaForms
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

# from .treinamento import treinar_face

# Instância da câmera global

camera_detection = VideoCamera()

# Função para capturar o frame com a face detectada
def gen_detect_face(camera):
    while True:
        frame = camera.detect_face()
        if frame is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            print("Frame não detectado. Ignorando...")

# Streaming para detecção facial
def detectar_camera(request):
    
    return StreamingHttpResponse(
        
        gen_detect_face(camera_detection),
        content_type='multipart/x-mixed-replace; boundary=frame'
    )


# Criação de funcionário
def criar_funcionario(request):
    if request.method == 'POST':
        form = FuncionarioForm(request.POST)
        if form.is_valid():
            funcionario = form.save()
            return redirect('criar_coleta_faces', funcionario_id=funcionario.id)
    else:
        form = FuncionarioForm()

    return render(request, 'criar_funcionario.html', {'form': form})


# Função de extração de imagens e retornar o file_path
def extract(camera_detection, funcionario_slug):
    amostra = 0
    numero_amostras = 10
    largura, altura = 280, 280
    file_paths = []
    max_falhas = 10
    falhas_consecutivas = 0

    while amostra < numero_amostras:
        frame = camera_detection.get_frame()

        if frame is None:
            falhas_consecutivas += 1
            print(f"Falha ao capturar o frame. Tentativa {falhas_consecutivas} de {max_falhas}.")
    
            if falhas_consecutivas >= max_falhas:
                print("Erro: Número máximo de falhas consecutivas atingido. Interrompendo o processo.")
                return []  # Retorna uma lista vazia se falhar várias vezes
    
        
        crop = camera_detection.sample_faces(frame)

        # Verifica se a face foi detectada corretamente
        if crop is not None:
            falhas_consecutivas = 0
            amostra += 1
            
            face = cv2.resize(crop, (largura, altura))
            imagemCinza = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
            
            # Caminho para salvar a imagem
            file_name_path = f'./tmp/{funcionario_slug}_{amostra}.jpg'
            cv2.imwrite(file_name_path, imagemCinza)
            file_paths.append(file_name_path)
        else:
            print("Face não encontrada")
            camera_detection.restart()

    camera_detection.restart()  # Reinicia a câmera após captura
    return file_paths



# Função principal de extração
def face_extract(context, funcionario):
    # camera_detection = VideoCamera()
    num_coletas = ColetaFaces.objects.filter(
        funcionario__slug=funcionario.slug).count()
    
    print(num_coletas) # quantidade de imagens que o funcionario tem cadastrado

    
    if num_coletas >= 80: #verifica se limite de coletas foi atingido
        context['erro'] = 'Limite máximo de coletas atingido.'
    else:
        # Extrair as faces usando o método da câmera
        file_paths = extract(camera_detection, funcionario.slug)
        print(file_paths)#path rostos
        
        for path in file_paths:
            # Cria uma instância de ColetaFaces e salva a imagem
            coleta_face = ColetaFaces.objects.create(funcionario=funcionario)

            coleta_face.image.save(os.path.basename(path), open(path, 'rb'))
            coleta_face.observacao = funcionario.observacao  # Adiciona a observação
            coleta_face.save()  # Salva a coleta com a observação
            os.remove(path)  # Remove o arquivo temporário após salvamento
        
        #atualiza o contexto com coletas salvas
        context['file_paths'] = ColetaFaces.objects.filter(
            funcionario__slug=funcionario.slug)
        context['extracao_ok'] = True #Define sinalizador de sucesso

    return context
        

# Criação de coletas de faces
def criar_coleta_faces(request, funcionario_id):
    print(funcionario_id) #id do funcionario cadastrado
    funcionario = Funcionario.objects.get(id=funcionario_id)
    
    # Recebe a observação, se estiver no request
    observacao = request.GET.get('observacao', funcionario.observacao)
    

    if request.method == 'POST':
        # Pega o valor de observação do POST, caso não tenha, mantém o valor atual
        observacao = request.GET.get('observacao', funcionario.observacao)  # Se não houver observação no POST, usa a atual
        
        # Atualiza o campo observação do funcionário
        funcionario.observacao = observacao
        funcionario.save()  # Salva no banco de dados
        
    else:
        # Se for GET, usamos a observação que já está no banco
        observacao = funcionario.observacao
    context = {
        'funcionario': funcionario,
        'detectar_camera': detectar_camera,
        'observacao': observacao,  # Passa a observação para o template
    }
    

    botao_extrai_foto = request.POST.get("cliked", "False") == "True"
    
    if botao_extrai_foto:
        print("Cliquei em Extrair Imagens!")
        context = face_extract(context, funcionario)  # Chama função para extrair funcionário
        treinador = Treinamento.get_instance()
        treinador.treinar_face()

    return render(request, 'criar_coleta_faces.html', context)


def buscar_funcionario(request):
    # Obtém o CPF da URL e remove espaços extras
    cpf = request.GET.get('cpf', '').strip()

    # Busca funcionário no banco de dados
    funcionario = Funcionario.objects.filter(cpf=cpf).first()

    if funcionario:
        # Se o CPF já estiver cadastrado, redireciona para a página de coleta de faces
        return redirect('criar_coleta_faces', funcionario_id=funcionario.id)

    # Se não encontrou o funcionário, direciona para o cadastro
    return redirect('criar_funcionario')


def encontra_funcionario(request):
    return render(request,'encontra_funcionario.html')


def captura_reconhece_faces(request):

    # Carrega o classificador HaarCascade, modelo pre treinado do opencv para detectar rosto na imagem
    cascade_path = "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)

    # Carrega modelo treinado
    reconhecedor = cv2.face.LBPHFaceRecognizer_create()
    
    treinamento = Treinamento.objects.first()
    if not treinamento:
        print("Modelo de treinamento não encontrado.")
        return

    model_path = os.path.join(settings.MEDIA_ROOT, treinamento.modelo.name)
    if not os.path.exists(model_path):
        print("Arquivo do modelo não existe:", model_path)
        return

    reconhecedor.read(model_path)
    print("Modelo carregado:", model_path)

    # Configura câmera
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    largura, altura = 220, 220
    

    while True:
        ret, frame = camera.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1) #espelha a camera
        frame = cv2.resize(frame, (550, 500)) # redimensiona
        imagemCinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) #converte para cinza

        faces_detectadas = face_cascade.detectMultiScale(
            imagemCinza,
            scaleFactor=1.1,
            minNeighbors=8,
            minSize=(70, 70),
            maxSize=(400, 400)
        )
        
        for (x, y, l, a) in faces_detectadas:
            imagemFace = cv2.resize(imagemCinza[y:y+a, x:x+l], (largura, altura))
            cv2.rectangle(frame, (x, y), (x+l, y+a), (0, 255, 0), 2)

            label, confianca = reconhecedor.predict(imagemFace)
            print(f"Rosto detectado - Label: {label}, Confiança: {confianca:.2f}")
            posicao_texto_y = y - 10 if y - 10 > 10 else y + a + 20 # Garante que o texto não saia da tela
            fonte = cv2.FONT_HERSHEY_DUPLEX

            if confianca < 60:
                funcionario = Funcionario.objects.filter(id=label).first()
                if funcionario:
                    print(f"Funcionário {funcionario.nome} RECONHECIDO. Salvando sessão...")
                    request.session['funcionario_id'] = funcionario.id
                    request.session['funcionario_nome'] = funcionario.nome # Adicionar o nome é uma boa prática

                    # A LINHA MÁGICA QUE DEVE RESOLVER TUDO
                    request.session.save()

                    print(f"Sessão FOI FORÇADA a salvar no banco de dados.")
                    
                    texto = f"{funcionario.nome} ({confianca:.0f})"
                    #({confianca:.0f})
                    cv2.putText(frame, texto, (x, posicao_texto_y), fonte, 0.9, (0, 255, 0), 2)
                else:
                    cv2.putText(frame, "Nao Encontrado", (x, posicao_texto_y), fonte, 0.9, (0, 0, 255), 2)
            else:
                cv2.putText(frame, "Desconhecido", (x, posicao_texto_y), fonte, 0.9, (0, 0, 255), 2)

        # # Converte o frame para JPEG e envia para o navegador
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    camera.release()
    cv2.destroyAllWindows()


def verifica_status_reconhecimento(request):
    """
    Verifica a sessão para ver se um funcionário foi reconhecido.
    Esta view será chamada pelo JavaScript a cada segundo.
    """
    print(f"VERIFICANDO SESSÃO. Conteúdo recebido: {request.session.items()}")

    funcionario_id = request.session.get('funcionario_id')


    if funcionario_id:
        # Se encontrou, retorna o ID e uma URL para redirecionar
        funcionario_nome = request.session.get('funcionario_nome', '')
        
        # Limpa a sessão para não ficar redirecionando em loop
        del request.session['funcionario_id']
        del request.session['funcionario_nome']

        return JsonResponse({
            'status': 'sucesso',
            'funcionario_id': funcionario_id,
            'funcionario_nome':funcionario_nome,
            'redirect_url': f"/seleciona_gabinete/{funcionario_id}"
        })
    else:
        # Se não encontrou, avisa que ainda está pendente
        return JsonResponse({'status': 'pendente'})


def camera_reconhecimento(request):
    return StreamingHttpResponse(captura_reconhece_faces(request), content_type="multipart/x-mixed-replace; boundary=frame")

def seleciona_gabinete(request, funcionario_id):
    # 1. Busca o funcionário pelo ID ou retorna um erro 404 se não existir
    funcionario = get_object_or_404(Funcionario, pk=funcionario_id)
    
    # 2. Lógica para quando o formulário é enviado (POST)
    if request.method == 'POST':
        form = ColetaEntradaForms(request.POST)
        if form.is_valid():
            # Cria o objeto RegistroEntrada, mas não salva no banco ainda (commit=False)
            novo_registro = form.save(commit=False)
            
            # Associa o funcionário correto ao registro
            novo_registro.funcionario = funcionario
            
            # Agora sim, salva o objeto completo no banco de dados
            novo_registro.save()
            
            messages.success(request, f'Entrada de {funcionario.nome} registrada com sucesso!')
            return redirect('criar_funcionario') # Redireciona para a página inicial ou outra de sua escolha
    
    # 3. Lógica para o primeiro acesso à página (GET)
    else:
        form = ColetaEntradaForms()

    # Prepara o contexto para enviar ao template
    context = {
        'form': form,
        'funcionario': funcionario,
        'mensagem': f'Por favor, registre o setor de destino para {funcionario.nome}.'
    }
    
    # Renderiza a página com o formulário e os dados do funcionário
    return render(request, 'form_gabinete.html', context)
        

def tela_reconhecimento(request):
    
    """
    Esta view renderiza a página de reconhecimento E GARANTE 
    que uma sessão seja criada antes do início do stream.
    """
    # Se o usuário ainda não tem uma chave de sessão, crie uma.
    if not request.session.session_key:
        request.session.create()
    
    # A linha acima força a criação da sessão no banco de dados.
    print(f"PÁGINA CARREGADA. Chave de sessão garantida: {request.session.session_key}")

    #context = {} # Adicione qualquer contexto que você precise
    return render(request, 'reconhecimento.html')

















# def set_test_session(request):
#     request.session['teste'] = 'ola mundo'
#     print("Sessão de teste SALVA:", request.session.items())
#     return JsonResponse({'status': 'sessao de teste definida'})

# def get_test_session(request):
#     valor_teste = request.session.get('teste', 'NAO ENCONTRADO')
#     print("Sessão de teste LIDA:", request.session.items())
#     return JsonResponse({'valor': valor_teste})