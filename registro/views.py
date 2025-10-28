import cv2
import os 
import re
import hashlib
import json
import base64
import numpy as np
from django.shortcuts import render, redirect, get_object_or_404
from django.http import StreamingHttpResponse, JsonResponse
from .forms import FuncionarioForm
from .models import Funcionario, ColetaFaces, Treinamento, RegistroEntrada
# from .camera import VideoCamera # Removido - Não é mais necessário
from django.contrib import messages
from django.conf import settings
import tempfile
from django.core.files import File
from django.core.files.base import ContentFile

from django.utils import timezone
from .forms import ColetaEntradaForms
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

# from .treinamento import treinar_face # Se você usa, descomente


# --- CARREGAMENTO GLOBAL DOS MODELOS ---
# Isso é muito mais eficiente. Carrega os modelos uma vez quando o servidor inicia.

# --- CARREGAMENTO GLOBAL SEGURO ---
# Carregar o classificador de um ficheiro é SEGURO, pois não acede à DB.
try:
    # Ajuste o caminho se necessário para encontrar o XML
    cascade_path = os.path.join(settings.BASE_DIR, 'haarcascade_frontalface_default.xml')
    if not os.path.exists(cascade_path):
        # Fallback para o caminho antigo se existir
        cascade_path = 'haarcascade_frontalface_default.xml' 
        
    face_cascade = cv2.CascadeClassifier(cascade_path)
    
    if face_cascade.empty():
        print(f"Erro: Não foi possível carregar o classificador Haar de '{cascade_path}'")
        face_cascade = None
    else:
        print(f"Classificador Haar '{os.path.basename(cascade_path)}' carregado com sucesso.")

except Exception as e:
    print(f"Erro CATASTRÓFICO ao carregar face_cascade: {e}")
    face_cascade = None

# --- CARREGAMENTO GLOBAL CORRIGIDO ---
# NÃO fazemos queries aqui. Apenas inicializamos a variável.
reconhecedor = None
print("Variável 'reconhecedor' inicializada como None.")

# --- FIM DO CARREGAMENTO GLOBAL ---


# Instância da câmera global (REMOVIDA)
# camera_detection = VideoCamera() # Removido

# Funções de Streaming (REMOVIDAS)
# def gen_detect_face(camera): # Removido
# def detectar_camera(request): # Removido


# --- NOVA FUNÇÃO DE CARREGAMENTO (Lazy Loading) ---
def load_reconhecedor(force_reload=False):
    """
    Carrega ou recarrega o reconhecedor da DB.
    Evita queries no arranque do servidor.
    """
    global reconhecedor
    
    # Só carrega se for a primeira vez (None) ou se forçarmos (force_reload=True)
    if reconhecedor is None or force_reload:
        if reconhecedor is None:
             reconhecedor = cv2.face.LBPHFaceRecognizer_create()
             print("Instância do LBPHFaceRecognizer criada.")
        
        try:
            # A query à DB só acontece AQUI, de forma segura.
            treinamento = Treinamento.objects.first() 
            if treinamento:
                model_path = os.path.join(settings.MEDIA_ROOT, treinamento.modelo.name)
                if os.path.exists(model_path):
                    reconhecedor.read(model_path)
                    print("Modelo de reconhecimento (LBPH) carregado/recarregado na memória.")
                else:
                    print(f"Arquivo do modelo não existe: {model_path}")
            else:
                print("Nenhum 'Treinamento' encontrado na DB. Reconhecedor está vazio.")
        except Exception as e:
            # Se isto falhar (ex: durante o primeiro 'migrate'), não quebra o servidor.
            print(f"Erro ao carregar modelo da DB (isto é normal no primeiro migrate): {e}")


# Criação de funcionário (Sem alterações)
def criar_funcionario(request):
    if request.method == 'POST':
        form = FuncionarioForm(request.POST)
        if form.is_valid():
            funcionario = form.save()
            return redirect('criar_coleta_faces', funcionario_id=funcionario.id)
    else:
        form = FuncionarioForm()

    return render(request, 'criar_funcionario.html', {'form': form})


# Funções de extração (REMOVIDAS - Lógica movida para 'api_coletar_frame')
# def extract(camera_detection, funcionario_slug): # Removido
# def face_extract(context, funcionario): # Removido
    

# Criação de coletas de faces (AJUSTADA)
# Esta view agora apenas renderiza a página e atualiza a observação.
# A coleta de fotos será feita por JavaScript chamando 'api_coletar_frame'.
def criar_coleta_faces(request, funcionario_id):
    funcionario = get_object_or_404(Funcionario, id=funcionario_id)
    observacao = funcionario.observacao # Pega a observação atual

    if request.method == 'POST':
        # Esta view agora SÓ lida com a atualização da observação
        observacao_post = request.POST.get('observacao', funcionario.observacao)
        
        if observacao_post != funcionario.observacao:
            funcionario.observacao = observacao_post
            funcionario.save()
            messages.success(request, 'Observação atualizada.')
        
        # Redireciona para evitar re-POST do formulário
        return redirect('criar_coleta_faces', funcionario_id=funcionario.id)
    
    # Contagem de coletas para exibir no template
    num_coletas = ColetaFaces.objects.filter(funcionario=funcionario).count()

    context = {
        'funcionario': funcionario,
        'observacao': observacao,
        'num_coletas': num_coletas, # Informa ao template quantas fotos já existem
        'max_coletas': 80 # Informa o limite (você usou 80 no seu código)
        # 'detectar_camera' foi removido
    }
    
    # A lógica 'botao_extrai_foto' foi removida. O JS no template
    # chamará a nova API 'api_coletar_frame'

    return render(request, 'criar_coleta_faces.html', context)


# --- NOVA VIEW DE API PARA COLETA DE FACES ---
@csrf_exempt # Idealmente, use o token CSRF no JS
@require_POST
def api_coletar_frame(request):
    """
    Recebe um frame (imagem) via POST do JavaScript, detecta a face,
    processa (corta, redimensiona, cinza) e salva no banco de dados.
    """
    if not face_cascade:
        return JsonResponse({'status': 'erro', 'message': 'Classificador de face não carregado no servidor.'})
    

    try:
        data = json.loads(request.body)
        frame = decode_base64_image(data['image'])
        # frame = cv2.flip(frame, 1)
        funcionario_id = data.get('funcionario_id')
        
        if frame is None:
            return JsonResponse({'status': 'erro', 'message': 'Frame inválido.'})
        if not funcionario_id:
            return JsonResponse({'status': 'erro', 'message': 'ID do funcionário não fornecido.'})

        funcionario = get_object_or_404(Funcionario, id=funcionario_id)
    
    except Exception as e:
        return JsonResponse({'status': 'erro', 'message': f'Erro nos dados da requisição: {e}'})

    # --- LÓGICA MOVIDA DE 'extract' e 'face_extract' ---
    
    # 1. Verificar limite
    num_coletas = ColetaFaces.objects.filter(funcionario=funcionario).count()
    if num_coletas >= 80: # Limite definido no seu código original
        return JsonResponse({'status': 'limite', 'message': 'Limite máximo de 80 coletas atingido.'})

    # 2. Detectar e processar a face (lógica de 'extract' e 'sample_faces')
    imagemCinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    largura, altura = 280, 280 # Tamanho definido no seu 'extract'

    # Usando o classificador global
    faces_detectadas = face_cascade.detectMultiScale(
        imagemCinza,
        scaleFactor=1.1,
        minNeighbors=8, 
        minSize=(70, 70) 
    )

    if len(faces_detectadas) == 0:
        return JsonResponse({'status': 'erro', 'message': 'Nenhuma face detectada.'})
    
    if len(faces_detectadas) > 1:
        return JsonResponse({'status': 'erro', 'message': 'Múltiplas faces detectadas. Capture apenas uma.'})

    # 3. Processar a face encontrada
    (x, y, l, a) = faces_detectadas[0] # Pega a primeira face
    
    face_recortada = cv2.resize(imagemCinza[y:y+a, x:x+l], (largura, altura))
    
    # 4. Salvar a imagem (lógica de 'face_extract')
    try:
        coleta_face = ColetaFaces.objects.create(funcionario=funcionario)
        
        # Converte o frame (array numpy) para um arquivo em memória
        ret, buf = cv2.imencode('.jpg', face_recortada)
        if not ret:
            return JsonResponse({'status': 'erro', 'message': 'Erro ao codificar imagem JPG.'})
        
        content = ContentFile(buf.tobytes(), name=f'{funcionario.slug}_{num_coletas + 1}.jpg')
        
        # Salva o arquivo no campo ImageField
        coleta_face.image.save(content.name, content, save=False) # save=False para não salvar no DB ainda
        
        coleta_face.observacao = funcionario.observacao # Adiciona observação
        coleta_face.save() # Salva tudo no DB
        
        print(f"Amostra {num_coletas + 1} salva para {funcionario.nome}")

        # Opcional: Disparar o treinamento aqui se desejar
        # try:
        #     treinador = Treinamento.get_instance()
        #     treinador.treinar_face()
        # except Exception as e:
        #     print(f"Erro ao disparar treinamento: {e}")
        
        return JsonResponse({
            'status': 'salvo', 
            'nova_contagem': num_coletas + 1,
            'message': f'Amostra {num_coletas + 1} salva.'
        })
    
    except Exception as e:
        print(f"Erro ao salvar no banco: {e}")
        return JsonResponse({'status': 'erro', 'message': f'Erro ao salvar no banco: {e}'})


# (Sem alterações)
def buscar_funcionario(request):
    cpf = request.GET.get('cpf', '').strip()
    funcionario = Funcionario.objects.filter(cpf=cpf).first()

    if funcionario:
        return redirect('criar_coleta_faces', funcionario_id=funcionario.id)
    return redirect('criar_funcionario')


# (Sem alterações)
def encontra_funcionario(request):
    return render(request,'encontra_funcionario.html')


# Função de decodificação (Helper)
def decode_base64_image(data_url):
    try:
        format, imgstr = data_url.split(';base64,') 
        img_data = base64.b64decode(imgstr)
        nparr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return frame
    except Exception as e:
        print(f"Erro ao decodificar imagem: {e}")
        return None
    
# --- VIEW DE PROCESSAMENTO DE RECONHECIMENTO ---
@csrf_exempt
@require_POST
def processar_frame_reconhecimento(request):
    
    # GARANTE QUE O MODELO ESTÁ CARREGADO ANTES DE USAR
    if reconhecedor is None:
        load_reconhecedor() 

    # 1. Verifica se os modelos carregaram
    if not reconhecedor or not face_cascade:
        return JsonResponse({'status': 'erro', 'message': 'Modelo ou classificador não carregado no servidor.'})

    # 2. Recebe e decodifica a imagem
    try:
        data = json.loads(request.body)
        frame = decode_base64_image(data['image'])
        if frame is None:
            return JsonResponse({'status': 'erro', 'message': 'Frame inválido.'})
    except Exception as e:
        return JsonResponse({'status': 'erro', 'message': f'Erro no JSON: {e}'})

    # Inverte o frame (como fizemos na coleta)
    frame = cv2.flip(frame, 1)

    # --- 3. LÓGICA DE RECONHECIMENTO (Sem alterações, mas agora segura) ---
    
    largura, altura = 280, 280 # O tamanho do seu treino
    frame_reconhecido = False
    imagemCinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    faces_detectadas = face_cascade.detectMultiScale(
        imagemCinza,
        scaleFactor=1.1,
        minNeighbors=5, # Mais permissivo
        minSize=(70, 70),
        maxSize=(400, 400)
    )
    
    # ... (O resto da sua lógica 'for' e 'if confianca < ...' continua igual) ...
    # ( ... )
    for (x, y, l, a) in faces_detectadas:
        imagemFace = cv2.resize(imagemCinza[y:y+a, x:x+l], (largura, altura))
        label, confianca = reconhecedor.predict(imagemFace)
        
        if confianca < 100: # Usando 100 como limiar
            funcionario = Funcionario.objects.filter(id=label).first()
            if funcionario:
                request.session['funcionario_id'] = funcionario.id
                request.session['funcionario_nome'] = funcionario.nome
                request.session.save()
                print(f"RECONHECIDO: {funcionario.nome} (Confiança: {confianca:.2f}). Sessão salva.")
                frame_reconhecido = True
                break
            else:
                print(f"Rosto detectado, mas ID {label} não encontrado.")
        else:
            print(f"Rosto detectado, mas 'Desconhecido'. Confiança: {confianca:.2f} (Label: {label})")

    if frame_reconhecido:
        return JsonResponse({'status': 'reconhecido'})
    else:
        return JsonResponse({'status': 'pendente'})


# (Sem alterações)
def verifica_status_reconhecimento(request):
    """
    Verifica a sessão para ver se um funcionário foi reconhecido.
    Esta view será chamada pelo JavaScript a cada segundo.
    """
    funcionario_id = request.session.get('funcionario_id')


    if funcionario_id:
        funcionario_nome = request.session.get('funcionario_nome', '')
        
        # Limpa a sessão para não ficar redirecionando em loop
        if 'funcionario_id' in request.session:
            del request.session['funcionario_id']
        if 'funcionario_nome' in request.session:
            del request.session['funcionario_nome']

        return JsonResponse({
            'status': 'sucesso',
            'funcionario_id': funcionario_id,
            'funcionario_nome':funcionario_nome,
            # Garante que a URL seja gerada corretamente
            'redirect_url': reverse('seleciona_gabinete', args=[funcionario_id]) 
        })
    else:
        return JsonResponse({'status': 'pendente'})


# View de Streaming (REMOVIDA)
# def camera_reconhecimento(request): # Removido


# (Sem alterações)
def seleciona_gabinete(request, funcionario_id):
    funcionario = get_object_or_404(Funcionario, pk=funcionario_id)
    
    if request.method == 'POST':
        form = ColetaEntradaForms(request.POST)
        if form.is_valid():
            novo_registro = form.save(commit=False)
            novo_registro.funcionario = funcionario
            novo_registro.save()
            #messages.success(request, f'Entrada de {funcionario.nome} registrada com sucesso!')
            return redirect('criar_funcionario') # Redireciona para a página inicial
    else:
        form = ColetaEntradaForms()

    context = {
        'form': form,
        'funcionario': funcionario,
        'mensagem': f'Por favor, registre o setor de destino para {funcionario.nome}.'
    }
    
    return render(request, 'form_gabinete.html', context)
        

# (Sem alterações)
def tela_reconhecimento(request):
    """
    Renderiza a página de reconhecimento E GARANTE 
    que uma sessão seja criada.
    """
    if not request.session.session_key:
        request.session.create()
    
    print(f"PÁGINA DE RECONHECIMENTO CARREGADA. Chave de sessão: {request.session.session_key}")
    return render(request, 'reconhecimento.html')


# (Sem alterações)
def carrega_entrada(request):
    return render(request, 'listar_entradas.html')


# (Sem alterações)
def listar_entradas(request):
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    funcionario_id = request.GET.get('funcionario')

    entradas = RegistroEntrada.objects.all().order_by('-timestamp') # Alterado para '-' para mais recentes primeiro

    if data_inicio:
        entradas = entradas.filter(timestamp__date__gte=data_inicio) # Use __date para comparar só a data
    if data_fim:
        entradas = entradas.filter(timestamp__date__lte=data_fim) # Use __date
    if funcionario_id:
        entradas = entradas.filter(funcionario__id=funcionario_id)

    todos_funcionarios = Funcionario.objects.all().order_by('nome')

    contexto = {
        'entradas': entradas,
        'data_inicio_val': data_inicio,
        'data_fim_val': data_fim,
        'todos_funcionarios': todos_funcionarios,
        'funcionario_selecionado_id': funcionario_id,
    }

    return render(request, 'listar_entradas.html', contexto)



@csrf_exempt
def api_disparar_treinamento(request):
    
    try:
        print("Iniciando processo de treinamento do modelo...")
        
        # 1. Executa o treinamento (cria o novo .yml)
        treinador = Treinamento.get_instance()
        treinador.treinar_face()
        
        print("Treinamento concluído. Recarregando o modelo na memória...")

        # 2. PASSO CRUCIAL: Força o recarregamento
        # A nossa nova função 'load_reconhecedor' é chamada com 'force_reload=True'
        load_reconhecedor(force_reload=True) 

        # 3. Envia a resposta de sucesso
        redirect_url = reverse('criar_funcionario')
        return JsonResponse({
            'status': 'sucesso', 
            'message': 'Modelo treinado! Redirecionando...',
            'redirect_url': redirect_url
        })
        
    except Exception as e:
        print(f"Erro GERAL durante o treinamento ou recarregamento: {e}")
        return JsonResponse({'status': 'erro', 'message': f'Erro ao treinar: {e}'}, status=500)