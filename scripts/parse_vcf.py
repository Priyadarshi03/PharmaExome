import sys
import gzip
import pandas as pd

vcf = sys.argv[1]
out = sys.argv[2]

pgx_genes = {
    "CYP2C19",
    "CYP2D6",
    "CYP2C9",
    "CYP3A5",
    "VKORC1",
    "TPMT",
    "NUDT15",
    "SLCO1B1"
}

rows = []

with gzip.open(vcf, "rt") as fh:
    for line in fh:

        if line.startswith("#"):
            continue

        cols = line.strip().split("\t")

        chrom = cols[0]
        pos = cols[1]
        ref = cols[3]
        alt = cols[4]

        gene = "UNKNOWN"

        rows.append(
            [chrom, pos, ref, alt, gene]
        )

df = pd.DataFrame(
    rows,
    columns=["CHROM", "POS", "REF", "ALT", "GENE"]
)

df.to_csv(out, sep="\t", index=False)