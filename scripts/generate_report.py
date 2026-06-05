import sys
import pandas as pd

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak
)

from reportlab.lib.styles import getSampleStyleSheet

phenotypes = pd.read_csv(sys.argv[1], sep="\t")
drugs = pd.read_csv(sys.argv[2], sep="\t")

pdf = SimpleDocTemplate(sys.argv[3])

styles = getSampleStyleSheet()

elements = []

elements.append(
    Paragraph(
        "WES Pharmacogenomics Report",
        styles["Title"]
    )
)

elements.append(Spacer(1, 20))

elements.append(
    Paragraph(
        "Phenotype Results",
        styles["Heading2"]
    )
)

for _, row in phenotypes.iterrows():

    elements.append(
        Paragraph(
            f"{row['GENE']} : {row['PHENOTYPE']}",
            styles["BodyText"]
        )
    )

elements.append(PageBreak())

elements.append(
    Paragraph(
        "Drug Recommendations",
        styles["Heading2"]
    )
)

for _, row in drugs.iterrows():

    elements.append(
        Paragraph(
            f"{row['DRUG']} : {row['RECOMMENDATION']}",
            styles["BodyText"]
        )
    )

pdf.build(elements)