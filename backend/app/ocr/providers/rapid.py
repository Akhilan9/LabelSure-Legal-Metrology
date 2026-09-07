import io
import logging
from pathlib import Path
from threading import Lock
from importlib.metadata import version
import cv2
import numpy as np
from PIL import Image, ImageOps
from app.ocr.base import BaseOCRProvider
from app.ocr.schemas import RawOCRBlockData, RawOCRRunResult
from app.ocr.normalization import calculate_polygon_bounding_box, normalize_ocr_text
from app.models.ocr import OCRStatus

logger = logging.getLogger(__name__)

class RapidOCRProvider(BaseOCRProvider):
    def __init__(self, fallback_threshold=0.50):
        self.threshold = fallback_threshold
        self._engine = None
        self._lock = Lock()

    @property
    def engine_name(self): return 'RapidOCR'

    @property
    def engine_version(self): return version('rapidocr')

    def _rapid(self, image):
        from rapidocr import RapidOCR, OCRVersion, ModelType
        with self._lock:
            if self._engine is None:
                try:
                    self._engine = RapidOCR(params={
                        'Det.ocr_version': OCRVersion.PPOCRV4,
                        'Det.model_type': ModelType.MOBILE,
                        'Rec.model_type': ModelType.MOBILE,
                        'Rec.ocr_version': OCRVersion.PPOCRV4,
                        'EngineConfig.onnxruntime.intra_op_num_threads': 2,
                        'EngineConfig.onnxruntime.inter_op_num_threads': 2,
                    })
                except Exception:
                    logger.warning('Failed to initialize RapidOCR with custom params, falling back to default', exc_info=True)
                    self._engine = RapidOCR()
            result = self._engine(image)
        if result is None or getattr(result, 'boxes', None) is None or getattr(result, 'txts', None) is None:
            return []
        return [(box.tolist(), text, float(score)) for box, text, score in zip(result.boxes, result.txts, result.scores)]

    def _tesseract(self, image, language):
        import pytesseract
        import shutil
        if not shutil.which('tesseract'):
            installed = Path('C:/Program Files/Tesseract-OCR/tesseract.exe')
            if installed.exists(): pytesseract.pytesseract.tesseract_cmd = str(installed)
        data = pytesseract.image_to_data(cv2.cvtColor(image, cv2.COLOR_BGR2RGB), lang={'en': 'eng', 'hi': 'hin'}.get(language, language),
                                        config='--psm 11', output_type=pytesseract.Output.DICT, timeout=90)
        groups = {}
        for i, text in enumerate(data['text']):
            if not text.strip() or float(data['conf'][i]) < 0: continue
            key = tuple(data[k][i] for k in ['page_num', 'block_num', 'par_num', 'line_num'])
            groups.setdefault(key, []).append((text, float(data['conf'][i]) / 100, data['left'][i], data['top'][i], data['width'][i], data['height'][i]))
        rows = []
        for words in groups.values():
            x = min(w[2] for w in words); y = min(w[3] for w in words)
            right = max(w[2]+w[4] for w in words); bottom = max(w[3]+w[5] for w in words)
            rows.append(([[x,y],[right,y],[right,bottom],[x,bottom]], ' '.join(w[0] for w in words), sum(w[1] for w in words)/len(words)))
        return rows

    def recognize_image_file(self, image_path, language='en'):
        return self.recognize_image_bytes(Path(image_path).read_bytes(), language)

    def recognize_image_bytes(self, image_bytes, language='en'):
        rows = []; engine = self.engine_name; engine_version = self.engine_version; warning = None
        image = None
        if image_bytes:
            try:
                pil_img = Image.open(io.BytesIO(image_bytes))
                pil_img = ImageOps.exif_transpose(pil_img)
                if pil_img.mode != "RGB":
                    pil_img = pil_img.convert("RGB")
                rgb_arr = np.array(pil_img)
                image = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)
            except Exception:
                image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is not None:
            try: rows = self._rapid(image)
            except Exception: logger.exception('RapidOCR failed')
            if not rows or sum(r[2] for r in rows)/len(rows) < self.threshold:
                try:
                    fallback = self._tesseract(image, language)
                    if fallback and (not rows or sum(r[2] for r in fallback)/len(fallback) > sum(r[2] for r in rows)/len(rows)):
                        rows = fallback; engine = 'Tesseract'; engine_version = version('pytesseract')
                except Exception:
                    logger.warning('Tesseract fallback unavailable', exc_info=True)
                    warning = 'Tesseract fallback unavailable. Install the Tesseract executable and language data.'
        blocks = []
        for polygon, text, confidence in rows:
            if not text.strip(): continue
            height, width = image.shape[:2]
            polygon = [[min(max(float(x),0),width),min(max(float(y),0),height)] for x,y in polygon]
            blocks.append(RawOCRBlockData(raw_text=text, normalized_text=normalize_ocr_text(text),
                confidence=min(1,max(0,confidence)), polygon=polygon, bounding_box=calculate_polygon_bounding_box(polygon)))
        blocks.sort(key=lambda b: (round(b.bounding_box.y_min / max(1,b.bounding_box.height)), b.bounding_box.x_min))
        for i, block in enumerate(blocks): block.reading_order = i; block.line_number = i+1
        average = sum(b.confidence for b in blocks)/len(blocks) if blocks else None
        return RawOCRRunResult(engine_name=engine, engine_version=engine_version, language_config=language,
            status=OCRStatus.SUCCESS if blocks and average >= self.threshold else OCRStatus.PARTIAL if blocks else OCRStatus.FAILED,
            average_confidence=average, blocks=blocks,
            error_code='OCR_UNAVAILABLE' if not blocks else 'FALLBACK_UNAVAILABLE' if warning else None,
            error_message_safe=warning or ('No readable text found in this image.' if not blocks else None))
