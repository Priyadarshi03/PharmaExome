"""
PharmaExome WES Pharmacogenomics Report Generator
Enhanced version with professional design using ReportLab
"""

import sys
import pandas as pd
from collections import defaultdict

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.platypus.flowables import Flowable
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import io


# ─────────────────────────────────────────────
#  BRAND COLORS
# ─────────────────────────────────────────────
NAVY        = colors.HexColor("#0D2B4E")
TEAL        = colors.HexColor("#1A7A8C")
TEAL_LIGHT  = colors.HexColor("#E8F4F6")
GOLD        = colors.HexColor("#D4A847")
LIGHT_GREY  = colors.HexColor("#F4F6F8")
MID_GREY    = colors.HexColor("#9AA5B4")
DARK_GREY   = colors.HexColor("#3D4A5C")
WHITE       = colors.white

# Risk badge colours
RISK_COLORS = {
    "Consider alternative": colors.HexColor("#C0392B"),
    "Reduce":               colors.HexColor("#E67E22"),
    "Consider lower":       colors.HexColor("#E67E22"),
    "default":              colors.HexColor("#2980B9"),
}

PHENOTYPE_COLORS = {
    "Intermediate Metabolizer": colors.HexColor("#F39C12"),
    "Poor Metabolizer":         colors.HexColor("#C0392B"),
    "Rapid Metabolizer":        colors.HexColor("#27AE60"),
    "Decreased Function":       colors.HexColor("#E67E22"),
    "Normal Function":          colors.HexColor("#27AE60"),
    "default":                  colors.HexColor("#2980B9"),
}


# ─────────────────────────────────────────────
#  HELPER FLOWABLES
# ─────────────────────────────────────────────
class ColorBar(Flowable):
    """A solid colour rectangle – used for section separators."""
    def __init__(self, width, height, fill_color):
        Flowable.__init__(self)
        self.width  = width
        self.height = height
        self.fill   = fill_color

    def draw(self):
        self.canv.setFillColor(self.fill)
        self.canv.rect(0, 0, self.width, self.height, fill=1, stroke=0)


class RoundedBadge(Flowable):
    """Pill-shaped coloured badge for phenotype / recommendation labels."""
    def __init__(self, text, bg_color, text_color=WHITE, font_size=7, padding_x=6, padding_y=3):
        Flowable.__init__(self)
        self.text       = text
        self.bg         = bg_color
        self.fg         = text_color
        self.font_size  = font_size
        self.padding_x  = padding_x
        self.padding_y  = padding_y
        # Approximate width from character count
        self.width  = len(text) * font_size * 0.62 + padding_x * 2
        self.height = font_size + padding_y * 2 + 2

    def draw(self):
        c = self.canv
        r = self.height / 2
        c.setFillColor(self.bg)
        c.roundRect(0, 0, self.width, self.height, r, fill=1, stroke=0)
        c.setFillColor(self.fg)
        c.setFont("Helvetica-Bold", self.font_size)
        c.drawCentredString(self.width / 2, self.padding_y + 1, self.text)


class SectionHeader(Flowable):
    """Full-width navy bar with white title text."""
    def __init__(self, title, page_width, font_size=13):
        Flowable.__init__(self)
        self.title      = title
        self.width      = page_width
        self.height     = 28
        self.font_size  = font_size

    def draw(self):
        c = self.canv
        c.setFillColor(NAVY)
        c.rect(0, 0, self.width, self.height, fill=1, stroke=0)
        c.setFillColor(GOLD)
        c.setFont("Helvetica-Bold", self.font_size)
        c.drawString(10, 8, self.title)


# ─────────────────────────────────────────────
#  PAGE TEMPLATE (header + footer on every page)
# ─────────────────────────────────────────────
class ReportCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        self._meta = kwargs.pop("meta", {})
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_chrome(self._pageNumber, total)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def _draw_chrome(self, page_num, total_pages):
        w, h = A4
        m = self._meta

        # ── Top header bar ──
        self.setFillColor(NAVY)
        self.rect(0, h - 40, w, 40, fill=1, stroke=0)

        # Logo text
        self.setFillColor(WHITE)
        self.setFont("Helvetica-Bold", 12)
        self.drawString(20, h - 26, "PharmaExome")
        self.setFont("Helvetica", 8)
        self.setFillColor(GOLD)
        self.drawString(20, h - 36, "WES Pharmacogenomics Report")

        # Patient name top-right
        self.setFillColor(WHITE)
        self.setFont("Helvetica-Bold", 8)
        name = m.get("patient_name", "")
        sid  = m.get("sample_id", "")
        self.drawRightString(w - 20, h - 24, name)
        self.setFont("Helvetica", 7)
        self.setFillColor(MID_GREY)
        self.drawRightString(w - 20, h - 34, sid)

        # Teal accent line under header
        self.setFillColor(TEAL)
        self.rect(0, h - 43, w, 3, fill=1, stroke=0)

        # ── Bottom footer ──
        self.setFillColor(LIGHT_GREY)
        self.rect(0, 0, w, 25, fill=1, stroke=0)

        self.setFillColor(DARK_GREY)
        self.setFont("Helvetica", 7)
        self.drawString(20, 9, "RESEARCH USE ONLY — NOT FOR CLINICAL DIAGNOSIS")

        self.drawRightString(w - 20, 9,
            f"Page {page_num} of {total_pages}  |  {m.get('analysis_date', '')}")


# ─────────────────────────────────────────────
#  STYLE FACTORY
# ─────────────────────────────────────────────
def make_styles():
    base = getSampleStyleSheet()

    styles = {
        "cover_title": ParagraphStyle(
            "cover_title", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=28,
            textColor=NAVY, leading=34, spaceAfter=6
        ),
        "cover_subtitle": ParagraphStyle(
            "cover_subtitle", parent=base["Normal"],
            fontName="Helvetica", fontSize=13,
            textColor=TEAL, leading=18, spaceAfter=4
        ),
        "cover_field_label": ParagraphStyle(
            "cover_field_label", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=8,
            textColor=MID_GREY, leading=12
        ),
        "cover_field_value": ParagraphStyle(
            "cover_field_value", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=11,
            textColor=NAVY, leading=15, spaceAfter=4
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"],
            fontName="Helvetica", fontSize=9,
            textColor=DARK_GREY, leading=14, spaceAfter=4
        ),
        "body_bold": ParagraphStyle(
            "body_bold", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=9,
            textColor=NAVY, leading=14
        ),
        "caption": ParagraphStyle(
            "caption", parent=base["Normal"],
            fontName="Helvetica", fontSize=7,
            textColor=MID_GREY, leading=10
        ),
        "gene_card_title": ParagraphStyle(
            "gene_card_title", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=11,
            textColor=NAVY, leading=14
        ),
        "gene_card_sub": ParagraphStyle(
            "gene_card_sub", parent=base["Normal"],
            fontName="Helvetica", fontSize=8,
            textColor=DARK_GREY, leading=12
        ),
        "table_header": ParagraphStyle(
            "table_header", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=8,
            textColor=WHITE, leading=11
        ),
        "table_cell": ParagraphStyle(
            "table_cell", parent=base["Normal"],
            fontName="Helvetica", fontSize=8,
            textColor=DARK_GREY, leading=11
        ),
        "warning": ParagraphStyle(
            "warning", parent=base["Normal"],
            fontName="Helvetica", fontSize=8,
            textColor=colors.HexColor("#7B341E"), leading=12
        ),
    }
    return styles


# ─────────────────────────────────────────────
#  COLOUR LOOKUP HELPERS
# ─────────────────────────────────────────────
def phenotype_color(phenotype_str):
    for key, col in PHENOTYPE_COLORS.items():
        if key.lower() in phenotype_str.lower():
            return col
    return PHENOTYPE_COLORS["default"]


def recommendation_color(rec_str):
    for key, col in RISK_COLORS.items():
        if key.lower() in rec_str.lower():
            return col
    return RISK_COLORS["default"]


# ─────────────────────────────────────────────
#  PAGE BUILDERS
# ─────────────────────────────────────────────
def build_cover(patient, styles, W, H):
    """Full cover page."""
    elems = []
    usable = W  # full content width

    # ── Big gold accent bar ──
    elems.append(ColorBar(usable, 6, GOLD))
    elems.append(Spacer(1, 30))

    elems.append(Paragraph("Pharmacogenomics", styles["cover_subtitle"]))
    elems.append(Paragraph("Clinical Report", styles["cover_title"]))
    elems.append(Spacer(1, 6))
    elems.append(ColorBar(120, 4, TEAL))
    elems.append(Spacer(1, 30))

    # Patient detail table
    detail_data = [
        [Paragraph("PATIENT NAME", styles["cover_field_label"]),
         Paragraph("SAMPLE ID", styles["cover_field_label"]),
         Paragraph("DATE OF BIRTH / AGE", styles["cover_field_label"]),
         Paragraph("SEX", styles["cover_field_label"])],
        [Paragraph(patient['patient_name'], styles["cover_field_value"]),
         Paragraph(str(patient['sample_id']), styles["cover_field_value"]),
         Paragraph(str(patient['age']) + " years", styles["cover_field_value"]),
         Paragraph(patient['sex'], styles["cover_field_value"])],
        [Paragraph("COLLECTION DATE", styles["cover_field_label"]),
         Paragraph("ANALYSIS DATE", styles["cover_field_label"]),
         Paragraph("REFERENCE GENOME", styles["cover_field_label"]),
         Paragraph("REPORT VERSION", styles["cover_field_label"])],
        [Paragraph(str(patient['collection_date']), styles["cover_field_value"]),
         Paragraph(str(patient['analysis_date']), styles["cover_field_value"]),
         Paragraph("GRCh38", styles["cover_field_value"]),
         Paragraph("2.0", styles["cover_field_value"])],
    ]

    col_w = usable / 4
    detail_table = Table(detail_data, colWidths=[col_w]*4)
    detail_table.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,-1), LIGHT_GREY),
        ("ROWBACKGROUND", (0,0), (-1,0), LIGHT_GREY),
        ("ROWBACKGROUND", (0,2), (-1,2), LIGHT_GREY),
        ("GRID",        (0,0), (-1,-1), 0.5, WHITE),
        ("VALIGN",      (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",  (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0), (-1,-1), 8),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
    ]))
    elems.append(detail_table)
    elems.append(Spacer(1, 30))

    # Pipeline badge row
    pipeline_steps = ["FASTQ", "fastp", "BWA-MEM", "SAMtools Sort & Index", "Variant Calling", "PGx Annotation", "Report"]
    step_w = usable / len(pipeline_steps)
    step_data = [[Paragraph(s, ParagraphStyle("ps", fontName="Helvetica-Bold",
                   fontSize=7, textColor=WHITE, alignment=TA_CENTER))
                  for s in pipeline_steps]]
    step_table = Table(step_data, colWidths=[step_w]*len(pipeline_steps))
    step_table.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), TEAL),
        ("TEXTCOLOR",    (0,0), (-1,-1), WHITE),
        ("TOPPADDING",   (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0), (-1,-1), 6),
        ("GRID",         (0,0), (-1,-1), 1, WHITE),
    ]))
    elems.append(Paragraph("ANALYSIS PIPELINE", styles["cover_field_label"]))
    elems.append(Spacer(1, 4))
    elems.append(step_table)
    elems.append(Spacer(1, 30))

    # Disclaimer box
    disclaimer_data = [[
        Paragraph(
            "⚠  FOR RESEARCH USE ONLY — This report is intended for informational "
            "purposes and must not be used as the sole basis for clinical decision-making. "
            "All findings should be interpreted by a qualified healthcare professional in "
            "conjunction with the patient's clinical context.",
            styles["warning"]
        )
    ]]
    dis_table = Table(disclaimer_data, colWidths=[usable])
    dis_table.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), colors.HexColor("#FFF5F0")),
        ("LEFTPADDING",  (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("TOPPADDING",   (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0), (-1,-1), 8),
        ("BOX",          (0,0), (-1,-1), 1.5, colors.HexColor("#E07B54")),
    ]))
    elems.append(dis_table)

    elems.append(PageBreak())
    return elems


def build_exec_summary(phenotypes, drugs, styles, W):
    elems = []
    elems.append(SectionHeader("EXECUTIVE SUMMARY", W))
    elems.append(Spacer(1, 12))

    n_genes = len(phenotypes)
    n_drugs = len(drugs)

    # KPI row
    kpi_data = [[
        Paragraph(f"{n_genes}", ParagraphStyle("kpin", fontName="Helvetica-Bold",
            fontSize=28, textColor=NAVY, alignment=TA_CENTER)),
        Paragraph(f"{n_drugs}", ParagraphStyle("kpin", fontName="Helvetica-Bold",
            fontSize=28, textColor=NAVY, alignment=TA_CENTER)),
        Paragraph(f"{len(phenotypes[phenotypes['PHENOTYPE'].str.contains('Intermediate|Poor|Decreased', na=False)])}", 
            ParagraphStyle("kpin", fontName="Helvetica-Bold",
            fontSize=28, textColor=colors.HexColor("#C0392B"), alignment=TA_CENTER)),
    ],[
        Paragraph("Pharmacogenes<br/>Analyzed", ParagraphStyle("kpil", fontName="Helvetica",
            fontSize=8, textColor=MID_GREY, alignment=TA_CENTER)),
        Paragraph("Drug<br/>Recommendations", ParagraphStyle("kpil", fontName="Helvetica",
            fontSize=8, textColor=MID_GREY, alignment=TA_CENTER)),
        Paragraph("Actionable<br/>Findings", ParagraphStyle("kpil", fontName="Helvetica",
            fontSize=8, textColor=MID_GREY, alignment=TA_CENTER)),
    ]]
    col_w = W / 3
    kpi_table = Table(kpi_data, colWidths=[col_w]*3)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), LIGHT_GREY),
        ("GRID",         (0,0), (-1,-1), 1, WHITE),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",   (0,0), (-1,-1), 12),
        ("BOTTOMPADDING",(0,0), (-1,-1), 8),
    ]))
    elems.append(kpi_table)
    elems.append(Spacer(1, 16))

    # Summary paragraph
    elems.append(Paragraph(
        f"This pharmacogenomics report for <b>{phenotypes.shape[0]}</b> pharmacogenes identified "
        f"<b>{n_drugs}</b> clinically relevant drug-gene interactions. Findings include "
        "intermediate or decreased metabolizer phenotypes in genes involved in thiopurine, "
        "antiplatelet, and statin metabolism. Dose adjustments or alternative therapies may "
        "be warranted. Please consult a clinical pharmacist or geneticist for interpretation.",
        styles["body"]
    ))
    elems.append(Spacer(1, 6))
    elems.append(PageBreak())
    return elems


def build_gene_cards(phenotypes, drugs, styles, W):
    """One card per gene with phenotype badge + drug recommendation."""
    elems = []
    elems.append(SectionHeader("PHARMACOGENOMIC FINDINGS", W))
    elems.append(Spacer(1, 12))

    drug_map = defaultdict(list)
    for _, row in drugs.iterrows():
        drug_map[row["GENE"]].append((row["DRUG"], row["RECOMMENDATION"]))

    cards = []
    for _, row in phenotypes.iterrows():
        gene    = row["GENE"]
        pheno   = row["PHENOTYPE"]
        func    = row["GENE_FUNCTION"]
        p_color = phenotype_color(pheno)
        gene_drugs = drug_map.get(gene, [])

        # Build drug rows inside card
        drug_rows = []
        for drug, rec in gene_drugs:
            r_color = recommendation_color(rec)
            drug_rows.append([
                Paragraph(f"<b>{drug}</b>", styles["table_cell"]),
                Paragraph(rec, ParagraphStyle("rec", fontName="Helvetica",
                    fontSize=8, textColor=r_color, leading=11)),
            ])

        drug_table = Table(drug_rows or [[Paragraph("—", styles["table_cell"]),
                                          Paragraph("No action required", styles["table_cell"])]],
                           colWidths=[W*0.28, W*0.44])
        drug_table.setStyle(TableStyle([
            ("VALIGN",       (0,0), (-1,-1), "TOP"),
            ("BOTTOMPADDING",(0,0), (-1,-1), 2),
            ("TOPPADDING",   (0,0), (-1,-1), 2),
        ]))

        # Left col: gene name + phenotype badge
        left_content = [
            Paragraph(gene, styles["gene_card_title"]),
            Spacer(1, 3),
            Paragraph(pheno, ParagraphStyle("pheno", fontName="Helvetica-Bold",
                fontSize=8, textColor=p_color)),
            Spacer(1, 4),
            Paragraph(func, styles["gene_card_sub"]),
        ]

        card_data = [[left_content, drug_table]]
        card = Table(card_data, colWidths=[W*0.28, W*0.72])
        card.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (0,0), TEAL_LIGHT),
            ("BACKGROUND",    (1,0), (1,0), WHITE),
            ("BOX",           (0,0), (-1,-1), 1, colors.HexColor("#CBD5E0")),
            ("LINEAFTER",     (0,0), (0,-1), 1.5, TEAL),
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
            ("TOPPADDING",    (0,0), (-1,-1), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 10),
            ("LEFTPADDING",   (0,0), (-1,-1), 10),
            ("RIGHTPADDING",  (0,0), (-1,-1), 10),
        ]))
        cards.append(KeepTogether([card, Spacer(1, 8)]))

    elems += cards
    elems.append(PageBreak())
    return elems


def build_drug_table(drugs, styles, W):
    elems = []
    elems.append(SectionHeader("DRUG RECOMMENDATIONS", W))
    elems.append(Spacer(1, 12))

    header = [
        Paragraph("GENE",           styles["table_header"]),
        Paragraph("DRUG",           styles["table_header"]),
        Paragraph("RECOMMENDATION", styles["table_header"]),
    ]
    rows = [header]
    for i, (_, row) in enumerate(drugs.iterrows()):
        r_color = recommendation_color(row["RECOMMENDATION"])
        rows.append([
            Paragraph(f"<b>{row['GENE']}</b>", styles["table_cell"]),
            Paragraph(row["DRUG"],             styles["table_cell"]),
            Paragraph(row["RECOMMENDATION"],
                ParagraphStyle("rec", fontName="Helvetica-Bold",
                    fontSize=8, textColor=r_color, leading=11)),
        ])

    col_ws = [W*0.18, W*0.22, W*0.60]
    t = Table(rows, colWidths=col_ws, repeatRows=1)
    row_bg = [(i, LIGHT_GREY if i % 2 == 0 else WHITE) for i in range(1, len(rows))]
    style_cmds = [
        ("BACKGROUND",    (0,0), (-1,0), NAVY),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("GRID",          (0,0), (-1,-1), 0.4, colors.HexColor("#CBD5E0")),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("ROWBACKGROUND", (0,0), (-1,0), NAVY),
    ]
    for idx, bg in row_bg:
        style_cmds.append(("BACKGROUND", (0,idx), (-1,idx), bg))
    t.setStyle(TableStyle(style_cmds))
    elems.append(t)
    elems.append(PageBreak())
    return elems


def build_variants_table(variants, styles, W):
    elems = []
    elems.append(SectionHeader("DETECTED VARIANTS", W))
    elems.append(Spacer(1, 8))
    elems.append(Paragraph(
        f"A total of <b>{len(variants)}</b> variants were detected across the pharmacogenes analyzed.",
        styles["body"]
    ))
    elems.append(Spacer(1, 8))

    # Group by gene, show mini-table per gene
    for gene, grp in variants.groupby("GENE"):
        elems.append(Paragraph(f"Gene: {gene}  ({len(grp)} variants)", styles["body_bold"]))
        elems.append(Spacer(1, 4))

        header = [Paragraph(c, styles["table_header"]) for c in ["CHROM","POSITION","REF","ALT"]]
        rows   = [header]
        for i, (_, vrow) in enumerate(grp.iterrows()):
            ref = str(vrow["REF"])[:18] + ("…" if len(str(vrow["REF"])) > 18 else "")
            alt = str(vrow["ALT"])[:18] + ("…" if len(str(vrow["ALT"])) > 18 else "")
            rows.append([
                Paragraph(vrow["CHROM"],       styles["table_cell"]),
                Paragraph(str(vrow["POS"]),    styles["table_cell"]),
                Paragraph(ref,                 styles["table_cell"]),
                Paragraph(alt,                 styles["table_cell"])
            ])

        col_ws = [W*0.14, W*0.22, W*0.32, W*0.32]
        t = Table(rows, colWidths=col_ws, repeatRows=1)
        style_cmds = [
            ("BACKGROUND",    (0,0), (-1,0), TEAL),
            ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
            ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#CBD5E0")),
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
            ("TOPPADDING",    (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ]
        for i in range(1, len(rows)):
            bg = LIGHT_GREY if i % 2 == 0 else WHITE
            style_cmds.append(("BACKGROUND", (0,i), (-1,i), bg))
        t.setStyle(TableStyle(style_cmds))
        elems.append(t)
        elems.append(Spacer(1, 12))

    elems.append(PageBreak())
    return elems


def build_methodology(styles, W):
    elems = []
    elems.append(SectionHeader("METHODOLOGY & LIMITATIONS", W))
    elems.append(Spacer(1, 12))

    steps = [
        ("Raw Sequencing (FASTQ)",  "Paired-end whole-exome sequencing reads."),
        ("Quality Control (fastp)", "Adapter trimming, quality filtering, and QC metrics."),
        ("Read Alignment (BWA-MEM)","Reads aligned to human reference genome GRCh38."),
        ("Sorting and Indexing (Samtools)","Sorting and Indexing of reads."),
        ("Variant Calling",         "BCftools used for SNP detection."),
        ("PGx Annotation",          "Variants annotated against curated(dummy) datasets."),
        ("Report Generation",       "Automated PDF report compiled with clinical recommendations."),
    ]

    for i, (step, desc) in enumerate(steps):
        row = [[
            Paragraph(str(i+1), ParagraphStyle("num", fontName="Helvetica-Bold",
                fontSize=12, textColor=WHITE, alignment=TA_CENTER)),
            Paragraph(f"<b>{step}</b><br/>{desc}", styles["body"]),
        ]]
        t = Table(row, colWidths=[30, W-30])
        t.setStyle(TableStyle([
            ("BACKGROUND",   (0,0), (0,0), TEAL),
            ("BACKGROUND",   (1,0), (1,0), TEAL_LIGHT if i%2==0 else WHITE),
            ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING",   (0,0), (-1,-1), 8),
            ("BOTTOMPADDING",(0,0), (-1,-1), 8),
            ("LEFTPADDING",  (1,0), (1,0), 10),
            ("BOX",          (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ]))
        elems.append(t)
        elems.append(Spacer(1, 2))

    elems.append(Spacer(1, 16))
    elems.append(Paragraph("Limitations", styles["body_bold"]))
    elems.append(Spacer(1, 4))
    limitations = [
        "This report covers the pharmacogenes captured by the PharmaExome panel only.",
        "Structural variants, gene duplications, and non-coding variants may not be fully detected.",
        "Clinical phenotype may be influenced by drug interactions, comorbidities, and other factors not captured here.",
        "Results should be interpreted by a qualified clinical pharmacist or medical geneticist.",
        "This report is for research use only and is not a substitute for professional medical advice.",
    ]
    for lim in limitations:
        elems.append(Paragraph(f"• {lim}", styles["body"]))

    return elems


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
def main():
    if len(sys.argv) != 6:
        print("Usage: python generate_report.py <metadata> <phenotypes> <drugs> <variants> <output.pdf>")
        sys.exit(1)

    metadata  = pd.read_csv(sys.argv[1], sep="\t")
    phenotypes= pd.read_csv(sys.argv[2], sep="\t")
    drugs     = pd.read_csv(sys.argv[3], sep="\t")
    variants  = pd.read_csv(sys.argv[4], sep="\t")
    out_path  = sys.argv[5]

    patient = metadata.iloc[0].to_dict()
    styles  = make_styles()

    page_w, page_h = A4
    margin = 20*mm
    usable_w = page_w - 2*margin

    # Canvas factory carrying metadata for header/footer
    def canvas_factory(filename, **kwargs):
        return ReportCanvas(filename, meta=patient, **kwargs)

    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=50, bottomMargin=35,
        title="PharmaExome PGx Report",
        author="PharmaExome Platform",
    )

    story = []
    story += build_cover(patient, styles, usable_w, page_h)
    story += build_exec_summary(phenotypes, drugs, styles, usable_w)
    story += build_gene_cards(phenotypes, drugs, styles, usable_w)
    story += build_drug_table(drugs, styles, usable_w)
    story += build_variants_table(variants, styles, usable_w)
    story += build_methodology(styles, usable_w)

    doc.build(story, canvasmaker=canvas_factory)
    print(f"✓ Report saved: {out_path}")


if __name__ == "__main__":
    main()
