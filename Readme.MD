# PharmaExome

## WES-Based Pharmacogenomics Analysis Pipeline

PharmaExome is an end-to-end Whole Exome Sequencing (WES) pharmacogenomics (PGx) pipeline that processes raw FASTQ files and generates clinically interpretable pharmacogenomic reports. The workflow performs quality control, alignment, variant calling, PGx variant extraction, phenotype assignment, drug recommendation generation, and PDF report creation.

The project is implemented using Snakemake for reproducible workflow management and Python for downstream pharmacogenomic interpretation.

---

## Features

* End-to-end WES processing from FASTQ to PDF report
* Automated workflow using Snakemake
* Quality control using FastQC and FastP
* Alignment using BWA-MEM
* BAM processing using SAMtools
* Variant calling using BCFtools
* PGx gene filtering using BED coordinates
* Pharmacogenomic phenotype assignment
* CPIC-inspired drug recommendations
* Automated PDF report generation
* Modular and extensible architecture

---

## Workflow Overview

```text
FASTQ
  │
  ▼
FastQC
  │
  ▼
FastP
  │
  ▼
BWA-MEM Alignment
  │
  ▼
SAMtools Sort & Index
  │
  ▼
Variant Calling (BCFtools)
  │
  ▼
PGx Gene Filtering
  │
  ▼
Variant Annotation
  │
  ▼
Phenotype Assignment
  │
  ▼
Drug Recommendation Engine
  │
  ▼
PDF Report Generation
```

---

## Directory Structure

```text
PharmaExome/
├── config/
│   ├── config.yaml
│   └── pgx_genes.txt
│
├── resources/
│   ├── reference/
│   │   ├──  Homo_sapiens_assembly38.fasta
│   │   ├── *.fai
│   │   ├── *.dict
│   │   ├── *.amb
│   │   ├── *.ann
│   │   ├── *.bwt
│   │   ├── *.pac
│   │   └── *.sa
│   │
│   ├── pgx_genes.bed
│   ├── gene_info.tsv
│   ├── drug_guidelines.tsv
│
├── samples/
│   ├── sample.tsv
│   ├── sample_R1.fastq.gz
│   └── sample_R2.fastq.gz
│
├── scripts/
│   ├── parse_vcf.py
│   ├── assign_phenotype.py
│   |__ generate_report.py
│
├── workflow/
│   └── Snakefile
│
└── results/
```

---

## Requirements

### Software

* Snakemake >= 9
* Python >= 3.10
* BWA
* SAMtools
* BCFtools
* FastQC
* FastP
* BEDTools
* Tabix

### Python Packages

```bash
pip install pandas reportlab numpy
```

---

## Reference Genome

Download GRCh38 / hg38 reference genome and place it in:

```text
resources/reference/
```

Required files:

```text
Homo_sapiens_assembly38.fasta
Homo_sapiens_assembly38.fasta.fai
Homo_sapiens_assembly38.dict
Homo_sapiens_assembly38.fasta.amb
Homo_sapiens_assembly38.fasta.ann
Homo_sapiens_assembly38.fasta.bwt
Homo_sapiens_assembly38.fasta.pac
Homo_sapiens_assembly38.fasta.sa
```

Generate indexes if necessary:

```bash
bwa index Homo_sapiens_assembly38.fasta

samtools faidx Homo_sapiens_assembly38.fasta

gatk CreateSequenceDictionary \
-R Homo_sapiens_assembly38.fasta
```

---

## Input Files

### Sequencing Data

```text
samples/
├── SAMPLE_R1.fastq.gz
└── SAMPLE_R2.fastq.gz
```

### Patient Metadata

```text
sample_id patient_name age sex collection_date analysis_date
SAMPLE001 TEST CLIENT  45  Male  2026-06-01  2026-06-06
```

---

## Running the Pipeline

Dry run:

```bash
snakemake -n -p
```

Execute:

```bash
snakemake --snakefile workflow/Snakefile --cores 8
```

---

## Generated Outputs

### Quality Control

```text
results/fastqc/
```

### Alignment Files

```text
results/bam/
```

### Variant Calls

```text
results/vcf/
```

### Pharmacogenomics Results

```text
results/pgx/
├── SAMPLE_gene_info.tsv
├── SAMPLE_phenotypes.tsv
├── SAMPLE_drug_recommendations.tsv
└── SAMPLE_pgx_variants.tsv
```

### Final Report

```text
results/report/
└── SAMPLE_report.pdf
```

---

## Example Report Contents

### Patient Information

* Sample ID
* Patient Name
* Age
* Sex
* Collection Date
* Analysis Date

### Sequencing Summary

* Total Reads
* Mapped Reads
* Alignment Rate
* Variant Counts

### Pharmacogenomic Findings

| Gene    | Phenotype                |
| ------- | ------------------------ |
| CYP2C19 | Intermediate Metabolizer |
| CYP2C9  | Normal Metabolizer       |
| SLCO1B1 | Decreased Function       |

### Drug Recommendations

| Drug        | Recommendation               |
| ----------- | ---------------------------- |
| Clopidogrel | Consider alternative therapy |
| Simvastatin | Lower dose recommended       |

### Report Summary

Clinical interpretation of detected pharmacogenomic variants and potential implications for medication response.

---

## Future Improvements

* VEP annotation support
* PharmCAT integration
* CPIC diplotype-based phenotype calling
* Star allele determination
* MultiQC reporting
* Structural variant support
* CNV calling for CYP2D6
* Interactive HTML reports
* Docker and Singularity support
* Cloud deployment on AWS

---

## Disclaimer

This software is intended for research and educational purposes only and is not intended for clinical diagnosis or medical decision making.

---

## Author

Priyadarshi Anand

Bioinformatics Developer | Genomics | NGS Pipeline Development | Pharmacogenomics

GitHub: https://github.com/Priyadarshi03
