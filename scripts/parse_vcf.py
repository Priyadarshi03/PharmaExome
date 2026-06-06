import pandas as pd
import sys

vcf = sys.argv[1]
bed = sys.argv[2]
out = sys.argv[3]

genes = pd.read_csv(
    bed,
    sep="\t",
    header=None,
    names=["chrom","start","end","gene"]
)

rows = []

with open(vcf) as fh:

    for line in fh:

        if line.startswith("#"):
            continue

        cols = line.strip().split("\t")

        chrom = cols[0]
        pos = int(cols[1])

        gene = "UNKNOWN"

        hits = genes[
            (genes.chrom == chrom) &
            (genes.start <= pos) &
            (genes.end >= pos)
        ]

        if not hits.empty:
            gene = hits.iloc[0]["gene"]

        rows.append([
            chrom,
            pos,
            cols[3],
            cols[4],
            gene
        ])

pd.DataFrame(
    rows,
    columns=["CHROM","POS","REF","ALT","GENE"]
).to_csv(out, sep="\t", index=False)