import io
from urllib.parse import parse_qs

import zxingcpp
from PIL import Image, UnidentifiedImageError

RECEIPT_KEYS = {"t", "s", "fn", "i", "fp", "n"}


def read_qr_codes(image_bytes: bytes) -> list[str]:
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image = image.convert("L")
    except (UnidentifiedImageError, OSError):
        return []
    barcodes = zxingcpp.read_barcodes(image, formats=zxingcpp.BarcodeFormat.QRCode)
    return [barcode.text for barcode in barcodes]

def is_receipt(text: str) -> bool:
    return RECEIPT_KEYS <= parse_qs(text.strip()).keys()
