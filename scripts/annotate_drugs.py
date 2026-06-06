import sys
import pandas as pd

phenotypes = pd.read_csv(
    sys.argv[1],
    sep="\t"
)

guidelines = pd.read_csv(
    "resources/drug_guidelines.tsv",
    sep="\t"
)

recommendations = guidelines[
    guidelines["GENE"].isin(
        phenotypes["GENE"]
    )
]

recommendations.to_csv(
    sys.argv[2],
    sep="\t",
    index=False
)