import fitz  # PyMuPDF
import os

def pdf_to_pngs(
    pdf_path,
    part_number,
    output_dir="output_images",
    dpi=300,
):
    """
    Converts a PDF into high-quality PNG images.

    Args:
        pdf_path (str): Path to the PDF file
        output_dir (str): Folder to store PNGs
        dpi (int): Rendering DPI (300 = print quality, 600 = ultra high quality)
    """

    os.makedirs(output_dir, exist_ok=True)

    pdf = fitz.open(pdf_path)

    # Scale factor: PDF default is 72 DPI
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)

    for page_number in range(len(pdf)):
        page = pdf[page_number]

        pix = page.get_pixmap(
            matrix=matrix,
            alpha=False
        )

        output_path = os.path.join(
            output_dir,
            f"FN-PG-P{part_number}-{page_number + 1:02}.png"
        )

        pix.save(output_path)

        print(f"Saved: {output_path}")

    pdf.close()
    print("Conversion complete.")


if __name__ == "__main__":
    pdfs = [
        "IMSLP935307-PMLP1467582-farbigenoten1.pdf",
        "IMSLP935308-PMLP1467582-farbigenoten2.pdf",
        "IMSLP935310-PMLP1467582-farbigenoten_erklarung.pdf"
    ]

    for part_number, pdf_file in enumerate(pdfs, start=1):
        pdf_to_pngs(
            pdf_path=f"masters/{pdf_file}",
            part_number = part_number,
            output_dir=f"working/png-scans-1/part-{part_number}",
            dpi=600
        )
