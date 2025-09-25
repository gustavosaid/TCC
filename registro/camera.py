import cv2
import os
import time


class VideoCamera:
    def __init__(self, camera_index=None, cascade_path=None, tmp_dir="./tmp"):
        """
        Inicializa a câmera, carrega o classificador Haar e cria diretório temporário.
        Se camera_index não for fornecido, tenta detectar a primeira câmera disponível.
        """
        self.video = None
        self.camera_index = camera_index if camera_index is not None else self._find_camera()
        self._init_camera(self.camera_index)

        # Classificador Haar
        if cascade_path is None:
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        if self.face_cascade.empty():
            raise Exception(f"Erro: Classificador Haar Cascade não carregado. Caminho: {cascade_path}")

        # Diretório temporário
        self.img_dir = tmp_dir
        os.makedirs(self.img_dir, exist_ok=True)
        print(f"Câmera {self.camera_index} inicializada com sucesso.")

    def _find_camera(self, max_index=5):
        """Tenta detectar automaticamente uma câmera disponível."""
        for i in range(max_index):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                cap.release()
                print(f"Câmera encontrada no índice {i}")
                return i
            cap.release()
        raise Exception("Nenhuma câmera encontrada.")

    def _init_camera(self, index):
        """Inicializa o VideoCapture."""
        self.video = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if not self.video.isOpened():
            raise Exception(f"Erro: Não foi possível abrir a câmera {index}.")

    def __del__(self):
        """Libera recursos da câmera e fecha janelas OpenCV."""
        try:
            if hasattr(self, 'video') and self.video.isOpened():
                self.video.release()
            cv2.destroyAllWindows()
            print("Câmera liberada com sucesso.")
        except Exception:
            pass  # Evita erros de shutdown do Python

    def restart(self):
        """Reinicia a câmera em caso de falha."""
        print("Reiniciando a câmera...")
        self.video.release()
        time.sleep(1)
        self._init_camera(self.camera_index)

    def get_frame(self, max_attempts=1):
        """Captura um frame com múltiplas tentativas."""
        for attempt in range(max_attempts):
            ret, frame = self.video.read()
            if ret and frame is not None:
                return ret, frame
            time.sleep(0.5)
        print("Falha ao capturar frame. Reiniciando a câmera...")
        self.restart()
        return None, None

    def detect_face(self, use_roi=True):
        """
        Detecta faces no frame e retorna JPEG codificado.
        Se use_roi=True, considera uma região central.
        """
        ret, frame = self.get_frame()
        if not ret or frame is None:
            return None

        frame = cv2.flip(frame, 1) #espelha a camera
        altura, largura, _ = frame.shape
        if use_roi:
            centro_x, centro_y = largura // 2, altura // 2
            a, b = 140, 180
            x1, y1 = centro_x - a, centro_y - b
            x2, y2 = centro_x + a, centro_y + b
        else:
            x1, y1, x2, y2 = 0, 0, largura, altura

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=8, minSize=(70, 70))

        for (x, y, w, h) in faces:
            if x1 < x < x2 and y1 < y < y2 and (x + w) < x2 and (y + h) < y2:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        ret, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes() if ret else None

    def sample_faces(self,frame):
        """Captura e retorna a primeira face encontrada no frame."""
        ret, frame = self.get_frame()
        if not ret or frame is None:
            return None

        frame = cv2.flip(frame, 180)
        frame = cv2.resize(frame, (640, 480))

        faces = self.face_cascade.detectMultiScale(
            frame, scaleFactor=1.1, minNeighbors=10, minSize=(50, 50), maxSize=(300, 300)
        )

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 4)
            return frame[y:y + h, x:x + w]

        return None
