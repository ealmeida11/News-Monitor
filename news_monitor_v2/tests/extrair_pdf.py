# -*- coding: utf-8 -*-
"""
Extrai texto do PDF de feedback (pode ser PDF truncado com imagem).
Se o PDF for inválido, tenta extrair a imagem embutida e rodar OCR.
"""
import re
from pathlib import Path

pdf_path = Path(r"C:\Users\ealmeida\Downloads\Feedback.pdf")
output_dir = Path(__file__).resolve().parent / "output"
out_txt = output_dir / "feedback_extraido.txt"
out_jpg = output_dir / "feedback_pagina.jpg"


def extrair_imagem_pdf_truncado():
    """Extrai o primeiro stream de imagem (JPEG) do PDF."""
    data = pdf_path.read_bytes()
    # Objeto com /Length 114410 e stream
    match = re.search(rb"/Length\s+(\d+).*?stream\s*\n", data, re.DOTALL)
    if not match:
        return None, None
    length = int(match.group(1))
    start = match.end()
    jpeg_data = data[start : start + length]
    if not jpeg_data.startswith(b"\xff\xd8\xff"):
        return None, None
    return jpeg_data, length


def ocr_imagem(jpeg_path):
    """Roda OCR na imagem com Tesseract (português)."""
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(jpeg_path)
        text = pytesseract.image_to_string(img, lang="por")
        return text.strip()
    except Exception as e:
        print(f"OCR: {e}")
        try:
            text = pytesseract.image_to_string(Image.open(jpeg_path))
            return text.strip()
        except Exception:
            return ""


def main():
    output_dir.mkdir(parents=True, exist_ok=True)
    full = ""

    # 1) Tentar leitura normal com pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    full += t + "\n"
    except Exception as e:
        print(f"pdfplumber: {e}")

    # 2) Se falhou, extrair imagem do PDF truncado e OCR
    if not full.strip():
        print("Tentando extrair imagem do PDF e rodar OCR...")
        jpeg_data, length = extrair_imagem_pdf_truncado()
        if jpeg_data:
            out_jpg.write_bytes(jpeg_data)
            print(f"Imagem extraída: {out_jpg} ({length} bytes)")
            full = ocr_imagem(out_jpg)
            if full:
                print("OCR concluído (português).")
        else:
            print("Nenhuma imagem JPEG encontrada no PDF.")
            return

    if not full.strip():
        print("Nenhum texto obtido.")
        return

    out_txt.write_text(full, encoding="utf-8")
    print(f"Texto salvo em: {out_txt}")
    print("\n--- Conteúdo extraído (primeiros 5000 caracteres) ---\n")
    print(full[:5000])


if __name__ == "__main__":
    main()
