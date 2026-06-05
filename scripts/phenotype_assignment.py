import sys
import pandas as pd

variants = pd.read_csv(sys.argv[1], sep="\t")

phenotypes = []

for gene in variants["GENE"].unique():

    phenotype = "Normal"

    if gene == "CYP2C19":
        phenotype = "Intermediate Metabolizer"

    phenotypes.append(
        [gene, phenotype]
    )

df = pd.DataFrame(
    phenotypes,
    columns=["GENE", "PHENOTYPE"]
)

df.to_csv(
    sys.argv[2],
    sep="\t",
    index=False
)