"""Create synthetic physical-page QA material; run with the bundled ReportLab runtime."""
import argparse
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


parser = argparse.ArgumentParser()
parser.add_argument('output', type=Path)
args = parser.parse_args()
args.output.parent.mkdir(parents=True, exist_ok=True)
if args.output.exists():
    raise SystemExit('Refusing to overwrite an existing fixture')
pdf = canvas.Canvas(str(args.output), pagesize=A4)
for title, sentences in [
    ('Chapter 1 Cells', [
        'Cells are the basic units of life in living organisms.',
        'Mitochondria release usable energy for cellular work.',
        'Ribosomes support protein synthesis inside cells.',
        'Cell membranes regulate what enters and leaves the cell.',
        'The nucleus contains genetic information for the cell.',
    ]),
    ('Chapter 2 Plants', [
        'Photosynthesis converts light energy into chemical energy.',
        'Roots absorb water and minerals from the soil.',
        'Stems support leaves and transport materials through plants.',
        'Flowers contain reproductive structures in flowering plants.',
        'Seeds contain an embryo and stored food for early growth.',
    ]),
]:
    pdf.setFont('Helvetica-Bold', 18)
    pdf.drawString(54, 780, title)
    pdf.setFont('Helvetica', 11)
    for index, sentence in enumerate(sentences):
        pdf.drawString(54, 740 - index * 24, sentence)
    pdf.showPage()
pdf.showPage()  # Deliberately empty third physical page; no OCR/text content.
pdf.save()
print('Created synthetic three-page PDF fixture')
