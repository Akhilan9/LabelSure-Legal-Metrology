import io
import cv2
import numpy as np
from PIL import Image, ImageOps

# Harden against decompression bomb attacks
Image.MAX_IMAGE_PIXELS = 50_000_000


class ImagePreprocessor:
    """
    OpenCV preprocessing pipeline specifically tailored for packaging labels.

    Preserves text sharpness, balances local contrast with CLAHE in LAB color space,
    removes high-frequency sensor noise with edge-preserving bilateral filtering,
    and produces an OCR-ready PNG artifact.
    """

    def __init__(self, max_dimension: int = 2560, clahe_clip_limit: float = 2.0):
        self.max_dimension = max_dimension
        self.clahe_clip_limit = clahe_clip_limit

    @staticmethod
    def decode_and_orient(image_bytes: bytes) -> np.ndarray:
        """
        Safely decodes image bytes and corrects orientation based on EXIF metadata.
        """
        if not image_bytes or len(image_bytes) == 0:
            raise ValueError("Image bytes are empty")

        try:
            pil_image = Image.open(io.BytesIO(image_bytes))
            pil_image = ImageOps.exif_transpose(pil_image)
            if pil_image.mode != "RGB":
                pil_image = pil_image.convert("RGB")
            # Convert RGB to BGR for OpenCV
            rgb_arr = np.array(pil_image)
            bgr_arr = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)
            return bgr_arr
        except Exception:
            # Fallback to standard OpenCV decode
            np_arr = np.frombuffer(image_bytes, np.uint8)
            cv_img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if cv_img is None or cv_img.size == 0:
                raise ValueError("Failed to decode image data using OpenCV")
            return cv_img

    def preprocess(self, image: np.ndarray) -> tuple[np.ndarray, bytes]:
        """
        Runs preprocessing stages and returns (processed_cv_image, png_encoded_bytes).
        """
        if image is None or image.size == 0:
            raise ValueError("Input image array is invalid or empty")

        working_img = image.copy()
        height, width = working_img.shape[:2]

        # 1. Dimension normalization (prevent decompression bomb / excessive matrix sizes)
        max_dim = max(height, width)
        if max_dim > self.max_dimension:
            scale = self.max_dimension / float(max_dim)
            new_width = max(1, int(width * scale))
            new_height = max(1, int(height * scale))
            working_img = cv2.resize(working_img, (new_width, new_height), interpolation=cv2.INTER_AREA)

        # 2. Local contrast enhancement via CLAHE on L channel in LAB color space
        lab = cv2.cvtColor(working_img, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)

        clahe = cv2.createCLAHE(clipLimit=self.clahe_clip_limit, tileGridSize=(8, 8))
        enhanced_l = clahe.apply(l_channel)

        merged_lab = cv2.merge([enhanced_l, a_channel, b_channel])
        contrast_enhanced = cv2.cvtColor(merged_lab, cv2.COLOR_LAB2BGR)

        # 3. Edge-preserving bilateral smoothing to reduce sensor/compression noise
        denoised = cv2.bilateralFilter(contrast_enhanced, d=5, sigmaColor=35, sigmaSpace=35)

        # 4. Encode to lossless PNG
        success, png_bytes = cv2.imencode(".png", denoised, [cv2.IMWRITE_PNG_COMPRESSION, 4])
        if not success:
            raise RuntimeError("Failed to encode preprocessed image to PNG")

        return denoised, png_bytes.tobytes()
