"""
assign_phenotypes.py
────────────────────
Takes a parsed pgx_variants.tsv (output of parse_vcf.py / parse_vep_vcf.py),
matches detected variants against PharmVar star-allele definitions,
assigns CPIC diplotypes and phenotypes, then looks up drug recommendations
from gene_info.tsv and drug_guidelines.tsv.

Inputs  (all positional):
  1. pgx_variants.tsv      — CHROM, POS, ID, REF, ALT, GENE
  2. gene_info.tsv         — GENE, PHENOTYPE, GENE_FUNCTION, ... (one row per gene×phenotype)
  3. drug_guidelines.tsv   — GENE, DRUG, PHENOTYPE, RECOMMENDATION, ... (one row per gene×drug×phenotype)
  4. phenotypes_out.tsv    — output path
  5. drug_recs_out.tsv     — output path

Usage:
  python assign_phenotypes.py \\
      test_S153_L007_pgx_variants.tsv \\
      gene_info.tsv \\
      drug_guidelines.tsv \\
      test_S153_L007_phenotypes.tsv \\
      test_S153_L007_drug_recommendations.tsv
"""

import sys
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
#  PharmVar star-allele definitions
#  Source: https://www.pharmvar.org  (GRCh38 coordinates)
#
#  Each entry: star_allele → {
#      variants : list of (chrom, pos, ref, alt) tuples that define the allele
#      activity : CPIC activity value  0=no function  0.5=decreased  1=normal  2=increased
#      hgvs     : human-readable HGVS notation for the portfolio / report
#  }
#
#  Matching logic: an allele is "detected" when ALL of its defining variants
#  are present in the sample's variant table.  *1 (wild-type) has no defining
#  variants and is used as the default when nothing else matches.
# ─────────────────────────────────────────────────────────────────────────────

STAR_ALLELES = {

    # ── CYP2C19 ──────────────────────────────────────────────────────────────
    "CYP2C19": {
        "*1":  {"variants": [],                                          "activity": 1.0, "hgvs": "wild-type / reference"},
        "*2":  {"variants": [("chr10", 94781859, "G",  "A")],           "activity": 0.0, "hgvs": "c.681G>A (p.Trp227Ter) — rs4244285"},
        "*3":  {"variants": [("chr10", 94773528, "G",  "A")],           "activity": 0.0, "hgvs": "c.636G>A (p.Trp212Ter) — rs4986893"},
        "*17": {"variants": [("chr10", 94842866, "A",  "G")],           "activity": 2.0, "hgvs": "c.-806C>T (promoter, increased transcription) — rs12248560"},
    },

    # ── CYP2C9 ───────────────────────────────────────────────────────────────
    "CYP2C9": {
        "*1":  {"variants": [],                                          "activity": 1.0, "hgvs": "wild-type / reference"},
        "*2":  {"variants": [("chr10", 96527337, "C",  "T")],           "activity": 0.5, "hgvs": "c.430C>T (p.Arg144Cys) — rs1799853"},
        "*3":  {"variants": [("chr10", 96610601, "A",  "C")],           "activity": 0.0, "hgvs": "c.1075A>C (p.Ile359Leu) — rs1057910"},
    },

    # ── SLCO1B1 ──────────────────────────────────────────────────────────────
    "SLCO1B1": {
        "*1a": {"variants": [],                                          "activity": 1.0, "hgvs": "wild-type / reference"},
        "*1b": {"variants": [("chr12", 21183015, "A",  "G")],           "activity": 1.0, "hgvs": "c.388A>G (p.Asn130Asp) — rs2306283"},
        "*5":  {"variants": [("chr12", 21178164, "T",  "C")],           "activity": 0.0, "hgvs": "c.521T>C (p.Val174Ala) — rs4149056 [primary myopathy SNP]"},
        "*15": {"variants": [("chr12", 21178164, "T",  "C"),
                             ("chr12", 21183015, "A",  "G")],           "activity": 0.0, "hgvs": "c.521T>C + c.388A>G (*1b background + *5)"},
    },

    # ── TPMT ─────────────────────────────────────────────────────────────────
    "TPMT": {
        "*1":  {"variants": [],                                          "activity": 1.0, "hgvs": "wild-type / reference"},
        "*2":  {"variants": [("chr6",  18143723, "G",  "C")],           "activity": 0.0, "hgvs": "c.238G>C (p.Ala80Pro) — rs1800462"},
        "*3A": {"variants": [("chr6",  18129420, "A",  "G"),
                             ("chr6",  18165748, "A",  "G")],           "activity": 0.0, "hgvs": "c.460G>A + c.719A>G (*3B + *3C combined)"},
        "*3B": {"variants": [("chr6",  18129420, "A",  "G")],           "activity": 0.0, "hgvs": "c.460G>A (p.Ala154Thr) — rs1800460"},
        "*3C": {"variants": [("chr6",  18165748, "A",  "G")],           "activity": 0.0, "hgvs": "c.719A>G (p.Tyr240Cys) — rs1142345"},
    },

    # ── NUDT15 ───────────────────────────────────────────────────────────────
    "NUDT15": {
        "*1":  {"variants": [],                                          "activity": 1.0, "hgvs": "wild-type / reference"},
        "*2":  {"variants": [("chr16", 31119836, "C",  "T"),
                             ("chr16", 31104935, "G",  "A")],           "activity": 0.0, "hgvs": "c.415C>T + c.52G>A"},
        "*3":  {"variants": [("chr16", 31104935, "G",  "A")],           "activity": 0.0, "hgvs": "c.415C>T (p.Arg139Cys) — rs116855232 [major Asian risk allele]"},
    },

    # ── CYP2B6 ───────────────────────────────────────────────────────────────
    "CYP2B6": {
        "*1":  {"variants": [],                                          "activity": 1.0, "hgvs": "wild-type / reference"},
        "*6":  {"variants": [("chr19", 15988455, "G",  "T"),
                             ("chr19", 16012093, "C",  "T")],           "activity": 0.5, "hgvs": "c.516G>T (p.Gln172His) + c.785A>G — rs3745274 + rs2279343"},
        "*18": {"variants": [("chr19", 15998716, "G",  "A")],           "activity": 0.0, "hgvs": "c.983T>C (p.Ile328Thr) — rs28399499"},
    },

    # ── CYP2D6 ───────────────────────────────────────────────────────────────
    "CYP2D6": {
        "*1":  {"variants": [],                                          "activity": 1.0, "hgvs": "wild-type / reference"},
        "*4":  {"variants": [("chr22", 42524947, "C",  "T")],           "activity": 0.0, "hgvs": "c.1846G>A (splice-site) — rs3892097"},
        "*10": {"variants": [("chr22", 42523805, "C",  "T")],           "activity": 0.5, "hgvs": "c.100C>T (p.Pro34Ser) — rs1065852"},
        "*41": {"variants": [("chr22", 42526694, "G",  "A")],           "activity": 0.5, "hgvs": "c.2988G>A (splicing) — rs28371725"},
    },
}


# ─────────────────────────────────────────────────────────────────────────────
#  CPIC activity-score → phenotype  (gene-specific thresholds)
#  Source: CPIC gene-specific guidelines (cpicpgx.org)
# ─────────────────────────────────────────────────────────────────────────────

def activity_score_to_phenotype(gene: str, score: float) -> str:
    if gene in ("CYP2C19", "CYP2D6", "CYP2B6", "CYP2C9"):
        if score == 0:      return "Poor Metabolizer"
        if score <= 1.0:    return "Intermediate Metabolizer"
        if score <= 2.0:    return "Normal Metabolizer"
        return "Ultrarapid Metabolizer"

    if gene == "SLCO1B1":
        if score == 0:      return "Poor Function"
        if score <= 1.0:    return "Decreased Function"
        return "Normal Function"

    if gene in ("TPMT", "NUDT15"):
        if score == 0:      return "Poor Metabolizer"
        if score < 2.0:     return "Intermediate Metabolizer"
        return "Normal Metabolizer"

    # Generic fallback
    if score == 0:          return "Poor Metabolizer"
    if score < 2.0:         return "Intermediate Metabolizer"
    return "Normal Metabolizer"


# ─────────────────────────────────────────────────────────────────────────────
#  Diplotype caller
#  Checks which star alleles have ALL their defining variants present in the
#  sample, then picks the two best-matching non-reference alleles (or *1).
# ─────────────────────────────────────────────────────────────────────────────

def call_diplotype(gene: str, sample_variants: set) -> tuple[str, str]:
    """
    sample_variants: set of (chrom, pos, ref, alt) tuples for this gene.
    Returns: (allele1, allele2) — the two most likely star alleles.
    """
    allele_defs = STAR_ALLELES.get(gene, {})
    matched = []

    for star, info in allele_defs.items():
        if star in ("*1", "*1a", "*1b"):
            continue                          # wild-type: only used as default
        defining = set(tuple(v) for v in info["variants"])
        if defining and defining.issubset(sample_variants):
            matched.append(star)

    # Deduplicate: *3A subsumes *3B and *3C — if *3A matched, drop its parts
    if "*3A" in matched:
        matched = [m for m in matched if m not in ("*3B", "*3C")]

    # *15 subsumes *5 and *1b for SLCO1B1
    if "*15" in matched:
        matched = [m for m in matched if m not in ("*5", "*1b")]

    # Reference allele for this gene
    ref_allele = "*1a" if gene == "SLCO1B1" else "*1"

    if len(matched) == 0:
        return ref_allele, ref_allele
    if len(matched) == 1:
        return ref_allele, matched[0]
    return matched[0], matched[1]


# ─────────────────────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) != 6:
        print(__doc__)
        sys.exit(1)

    variants_path    = sys.argv[1]
    gene_info_path   = sys.argv[2]
    guidelines_path  = sys.argv[3]
    phenotypes_out   = sys.argv[4]
    drug_recs_out    = sys.argv[5]

    # ── Load inputs ──────────────────────────────────────────────────────────
    variants   = pd.read_csv(variants_path,  sep="\t")
    gene_info  = pd.read_csv(gene_info_path, sep="\t")
    guidelines = pd.read_csv(guidelines_path, sep="\t")

    genes_in_variants = [g for g in variants["GENE"].unique() if g != "UNKNOWN"]

    print(f"\n{'='*60}")
    print(f"  PGx Phenotype Assignment")
    print(f"  Variants file : {variants_path}  ({len(variants)} rows, {len(genes_in_variants)} genes)")
    print(f"  Gene info     : {gene_info_path}")
    print(f"  Guidelines    : {guidelines_path}")
    print(f"{'='*60}\n")

    phenotype_rows = []
    drug_rows      = []

    for gene in genes_in_variants:

        gene_variants = variants[variants["GENE"] == gene]

        # Build set of (chrom, pos, ref, alt) for this sample + gene
        sample_variant_set = set(
            zip(
                gene_variants["CHROM"],
                gene_variants["POS"].astype(int),
                gene_variants["REF"].astype(str),
                gene_variants["ALT"].astype(str),
            )
        )

        # ── Diplotype calling ─────────────────────────────────────────────
        allele1, allele2 = call_diplotype(gene, sample_variant_set)
        diplotype = f"{allele1}/{allele2}"

        allele_defs = STAR_ALLELES.get(gene, {})
        act1 = allele_defs.get(allele1, {}).get("activity", 1.0)
        act2 = allele_defs.get(allele2, {}).get("activity", 1.0)
        activity_score = act1 + act2

        hgvs1 = allele_defs.get(allele1, {}).get("hgvs", ".")
        hgvs2 = allele_defs.get(allele2, {}).get("hgvs", ".")

        # ── Phenotype ─────────────────────────────────────────────────────
        phenotype = activity_score_to_phenotype(gene, activity_score)

        # ── Pull gene metadata from gene_info.tsv ─────────────────────────
        gene_meta = gene_info[
            (gene_info["GENE"] == gene) &
            (gene_info["PHENOTYPE"] == phenotype)
        ]

        if gene_meta.empty:
            # Phenotype class not in gene_info — use any row for gene metadata
            gene_meta = gene_info[gene_info["GENE"] == gene]

        if not gene_meta.empty:
            row0           = gene_meta.iloc[0]
            gene_function  = row0.get("GENE_FUNCTION", f"{gene} drug metabolism")
            enzyme_class   = row0.get("ENZYME_CLASS",  ".")
            cpic_tier      = row0.get("CPIC_TIER",     ".")
            pharmvar_url   = row0.get("PHARMVAR_URL",  ".")
            guideline_url  = row0.get("CPIC_GUIDELINE_URL", ".")
            pmid           = row0.get("PMID",          ".")
        else:
            gene_function = f"{gene} drug metabolism"
            enzyme_class  = "."
            cpic_tier     = "."
            pharmvar_url  = "."
            guideline_url = "."
            pmid          = "."

        print(f"  [{gene}]")
        print(f"    Variants detected : {len(gene_variants)}")
        print(f"    Diplotype         : {diplotype}")
        print(f"    Activity score    : {activity_score}")
        print(f"    Phenotype         : {phenotype}")

        phenotype_rows.append({
            "GENE":              gene,
            "DIPLOTYPE":         diplotype,
            "ALLELE1":           allele1,
            "ALLELE2":           allele2,
            "ALLELE1_HGVS":      hgvs1,
            "ALLELE2_HGVS":      hgvs2,
            "ACTIVITY_SCORE":    activity_score,
            "PHENOTYPE":         phenotype,
            "GENE_FUNCTION":     gene_function,
            "ENZYME_CLASS":      enzyme_class,
            "CPIC_TIER":         cpic_tier,
            "PHARMVAR_URL":      pharmvar_url,
            "CPIC_GUIDELINE_URL": guideline_url,
            "PMID":              pmid,
            "N_VARIANTS_DETECTED": len(gene_variants),
        })

        # ── Drug recommendations from drug_guidelines.tsv ─────────────────
        gene_drugs = guidelines[
            (guidelines["GENE"] == gene) &
            (guidelines["PHENOTYPE"] == phenotype)
        ]

        if gene_drugs.empty:
            print(f"    [warn] No guideline rows found for {gene} / {phenotype}")
        else:
            print(f"    Drug recs         : {len(gene_drugs)} drugs")

        for _, drug_row in gene_drugs.iterrows():
            drug_rows.append({
                "GENE":               gene,
                "DRUG":               drug_row["DRUG"],
                "DIPLOTYPE":          diplotype,
                "PHENOTYPE":          phenotype,
                "RECOMMENDATION":     drug_row["RECOMMENDATION"],
                "ACTION_CATEGORY":    drug_row.get("ACTION_CATEGORY",  "."),
                "EVIDENCE_LEVEL":     drug_row.get("EVIDENCE_LEVEL",   "."),
                "CPIC_STRENGTH":      drug_row.get("CPIC_STRENGTH",    "."),
                "CPIC_GUIDELINE_URL": drug_row.get("CPIC_GUIDELINE_URL", "."),
                "PMID":               drug_row.get("PMID",             "."),
            })

        print()

    # ── Write outputs ─────────────────────────────────────────────────────────
    phenotypes_df = pd.DataFrame(phenotype_rows)
    drug_recs_df  = pd.DataFrame(drug_rows)

    phenotypes_df.to_csv(phenotypes_out, sep="\t", index=False)
    drug_recs_df.to_csv(drug_recs_out,  sep="\t", index=False)

    print(f"{'='*60}")
    print(f"  ✓  {phenotypes_out}  ({len(phenotypes_df)} genes)")
    print(f"  ✓  {drug_recs_out}   ({len(drug_recs_df)} drug-gene pairs)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
