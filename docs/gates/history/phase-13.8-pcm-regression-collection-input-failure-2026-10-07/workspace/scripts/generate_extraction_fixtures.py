"""Rebuild the synthetic Phase 10 multilingual PDF corpus (dev tool)."""

from pathlib import Path

import pymupdf


def create_language_pdf(path):
    doc = pymupdf.open()
    samples = [
        ("eng", "Package voltage 5 V", "helv"),
        ("deu", "Gehäuse Spannung 5 V", "helv"),
        ("chi_sim", "产品规格 额定电压 5 V 电流 20 mA 封装类型", "china-s"),
        ("eng+deu+chi_sim", "Package Gehäuse", "helv"),
    ]
    for _language, text, font in samples:
        native = doc.new_page(width=1000, height=300)
        native.insert_text((45, 90), text, fontsize=26, fontname=font)
        if "+" in _language:
            native.insert_text(
                (45, 210),
                "产品规格 额定电压 5 V 电流 20 mA 封装类型",
                fontsize=26,
                fontname="china-s",
            )
        native.insert_text((45, 145), "TEST-32R  5.00 mm", fontsize=26)
        png = native.get_pixmap(dpi=300).tobytes("png")
        scanned = doc.new_page(width=1000, height=300)
        scanned.insert_image(scanned.rect, stream=png)
    doc.save(path, deflate=True, garbage=4, no_new_id=True)
    doc.close()
    return path


if __name__ == "__main__":
    create_language_pdf(
        Path(__file__).resolve().parents[1]
        / "fixtures/extraction/language-matrix.pdf"
    )
