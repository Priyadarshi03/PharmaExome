import sys
import pandas as pd

variants = pd.read_csv(sys.argv[1], sep="\t")
gene_db = pd.read_csv("resources/gene_info.tsv", sep="\t")

phenotypes = gene_db[
    gene_db["GENE"].isin(
        variants["GENE"].unique()
    )
]

phenotypes.to_csv(
    sys.argv[2],
    sep="\t",
    index=False
)