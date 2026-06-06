import sys
import pandas as pd

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Table,
    TableStyle
)

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

metadata = pd.read_csv(sys.argv[1], sep="\t")
phenotypes = pd.read_csv(sys.argv[2], sep="\t")
drugs = pd.read_csv(sys.argv[3], sep="\t")
variants = pd.read_csv(sys.argv[4], sep="\t")

pdf = SimpleDocTemplate(sys.argv[5])

styles = getSampleStyleSheet()

elements = []

patient = metadata.iloc[0]

elements.append(
    Paragraph(
        "PharmaExome WES Pharmacogenomics Report",
        styles["Title"]
    )
)

elements.append(Spacer(1,20))

elements.append(
    Paragraph(
        f"Patient: {patient['patient_name']}",
        styles["BodyText"]
    )
)

elements.append(
    Paragraph(
        f"Sample ID: {patient['sample_id']}",
        styles["BodyText"]
    )
)

elements.append(
    Paragraph(
        f"Age: {patient['age']} | Sex: {patient['sex']}",
        styles["BodyText"]
    )
)

elements.append(
    Paragraph(
        f"Analysis Date: {patient['analysis_date']}",
        styles["BodyText"]
    )
)

elements.append(PageBreak())

elements.append(
    Paragraph(
        "Executive Summary",
        styles["Heading1"]
    )
)

elements.append(
    Paragraph(
        f"{len(phenotypes)} pharmacogenes with actionable findings were identified.",
        styles["BodyText"]
    )
)

elements.append(Spacer(1,10))

elements.append(
    Paragraph(
        "Pharmacogenomic Findings",
        styles["Heading1"]
    )
)

data = [list(phenotypes.columns)] + phenotypes.values.tolist()

table = Table(data)

table.setStyle(
    TableStyle([
        ('GRID',(0,0),(-1,-1),1,colors.black)
    ])
)

elements.append(table)

elements.append(PageBreak())

elements.append(
    Paragraph(
        "Drug Recommendations",
        styles["Heading1"]
    )
)

data = [list(drugs.columns)] + drugs.values.tolist()

table = Table(data)

table.setStyle(
    TableStyle([
        ('GRID',(0,0),(-1,-1),1,colors.black)
    ])
)

elements.append(table)

elements.append(PageBreak())

elements.append(
    Paragraph(
        "Detected Variants",
        styles["Heading1"]
    )
)

data = [list(variants.columns)] + variants.values.tolist()

table = Table(data)

table.setStyle(
    TableStyle([
        ('GRID',(0,0),(-1,-1),1,colors.black)
    ])
)

elements.append(table)

elements.append(PageBreak())

elements.append(
    Paragraph(
        "Methodology",
        styles["Heading1"]
    )
)

elements.append(
    Paragraph(
        "FASTQ → fastp → BWA-MEM → Variant Calling → PGx Annotation → Report Generation",
        styles["BodyText"]
    )
)

elements.append(
    Paragraph(
        "Reference Genome: GRCh38",
        styles["BodyText"]
    )
)

elements.append(Spacer(1,20))

elements.append(
    Paragraph(
        "Limitations",
        styles["Heading1"]
    )
)

elements.append(
    Paragraph(
        "This report is intended for research use. Clinical decisions should not be based solely on these findings.",
        styles["BodyText"]
    )
)

pdf.build(elements)