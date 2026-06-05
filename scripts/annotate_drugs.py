import sys
import pandas as pd

phenotypes = pd.read_csv(
    sys.argv[1],
    sep="\t"
)

recommendations = []

for _, row in phenotypes.iterrows():

    gene = row["GENE"]

    if gene == "CYP2C19":

        recommendations.append(
            [
                gene,
                "Clopidogrel",
                "Consider alternative therapy"
            ]
        )

    elif gene == "SLCO1B1":

        recommendations.append(
            [
                gene,
                "Simvastatin",
                "Lower dose recommended"
            ]
        )

df = pd.DataFrame(
    recommendations,
    columns=[
        "GENE",
        "DRUG",
        "RECOMMENDATION"
    ]
)

df.to_csv(
    sys.argv[2],
    sep="\t",
    index=False
)