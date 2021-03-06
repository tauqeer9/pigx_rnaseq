# PiGx RNAseq Pipeline.
#
# Copyright © 2017, 2018 Bora Uyar <bora.uyar@mdc-berlin.de>
# Copyright © 2017, 2018 Jonathan Ronen <yablee@gmail.com>
# Copyright © 2017, 2018 Ricardo Wurmus <ricardo.wurmus@mdc-berlin.de>
#
# This file is part of the PiGx RNAseq Pipeline.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Snakefile for pigx rnaseq pipeline
"""

import os
import yaml
import csv
import inspect

include: os.path.join(config['locations']['pkglibexecdir'], 'scripts/validate_input.py')
validate_config(config)

GENOME_FASTA = config['locations']['genome-fasta']
CDNA_FASTA = config['locations']['cdna-fasta']
READS_DIR = config['locations']['reads-dir']
OUTPUT_DIR = config['locations']['output-dir']
ORGANISM = config['organism']

if os.getenv("PIGX_UNINSTALLED"):
    LOGO = os.path.join(config['locations']['pkgdatadir'], "images/Logo_PiGx.png")
else:
    LOGO = os.path.join(config['locations']['pkgdatadir'], "Logo_PiGx.png")

SCRIPTS_DIR = os.path.join(config['locations']['pkglibexecdir'], 'scripts/')

TRIMMED_READS_DIR = os.path.join(OUTPUT_DIR, 'trimmed_reads')
LOG_DIR           = os.path.join(OUTPUT_DIR, 'logs')
FASTQC_DIR        = os.path.join(OUTPUT_DIR, 'fastqc')
MULTIQC_DIR       = os.path.join(OUTPUT_DIR, 'multiqc')
MAPPED_READS_DIR  = os.path.join(OUTPUT_DIR, 'mapped_reads')
BIGWIG_DIR      = os.path.join(OUTPUT_DIR, 'bigwig_files')
COUNTS_DIR  = os.path.join(OUTPUT_DIR, 'feature_counts')
SALMON_DIR        = os.path.join(OUTPUT_DIR, 'salmon_output')

def toolArgs(name):
    if 'args' in config['tools'][name]:
        return config['tools'][name]['args']
    else:
        return ""

def tool(name):
    cmd = config['tools'][name]['executable']
    return cmd + " " + toolArgs(name)

FASTQC_EXEC  = tool('fastqc')
MULTIQC_EXEC = tool('multiqc')
STAR_EXEC_MAP    = tool('star_map')
STAR_EXEC_INDEX  = tool('star_index')
SALMON_EXEC  = tool('salmon')
TRIM_GALORE_EXEC = tool('trim-galore')
SAMTOOLS_EXEC    = tool('samtools')
HTSEQ_COUNT_EXEC = tool('htseq-count')
GUNZIP_EXEC      = tool('gunzip')
RSCRIPT_EXEC     = tool('Rscript')
SED_EXEC = tool('sed')

STAR_INDEX_THREADS   = config['execution']['rules']['star_index']['threads']
SALMON_INDEX_THREADS = config['execution']['rules']['salmon_index']['threads']
STAR_MAP_THREADS     = config['execution']['rules']['star_map']['threads']
SALMON_QUANT_THREADS = config['execution']['rules']['salmon_quant']['threads']


GTF_FILE = config['locations']['gtf-file']
SAMPLE_SHEET_FILE = config['locations']['sample-sheet']

DE_ANALYSIS_LIST = config.get('DEanalyses', {})

## Load sample sheet
with open(SAMPLE_SHEET_FILE, 'r') as fp:
  rows =  [row for row in csv.reader(fp, delimiter=',')]
  header = rows[0]; rows = rows[1:]
  SAMPLE_SHEET = [dict(zip(header, row)) for row in rows]

# Convenience function to access fields of sample sheet columns that
# match the predicate.  The predicate may be a string.
def lookup(column, predicate, fields=[]):
  if inspect.isfunction(predicate):
    records = [line for line in SAMPLE_SHEET if predicate(line[column])]
  else:
    records = [line for line in SAMPLE_SHEET if line[column]==predicate]
  return [record[field] for record in records for field in fields]

SAMPLES = [line['name'] for line in SAMPLE_SHEET]

targets = {
    # rule to print all rule descriptions
    'help': {
        'description': "Print all rules and their descriptions.",
        'files': []
    },
    'final-report': {
        'description': "Produce a comprehensive report.  This is the default target.",
        'files':
      [os.path.join(OUTPUT_DIR, 'star_index', "SAindex"),
            os.path.join(OUTPUT_DIR, 'salmon_index', "sa.bin"),
            os.path.join(MULTIQC_DIR, 'multiqc_report.html')] +
	  [os.path.join(COUNTS_DIR, "raw_counts", "counts_from_SALMON.transcripts.tsv"),
            os.path.join(COUNTS_DIR, "raw_counts", "counts_from_SALMON.genes.tsv"),
            os.path.join(COUNTS_DIR, "normalized", "TPM_counts_from_SALMON.transcripts.tsv"),
            os.path.join(COUNTS_DIR, "normalized", "TPM_counts_from_SALMON.genes.tsv"),
            os.path.join(COUNTS_DIR, "raw_counts", "counts_from_star.tsv"),
            os.path.join(COUNTS_DIR, "normalized", "deseq_normalized_counts.tsv",
            os.path.join(COUNTS_DIR, "normalized", "deseq_size_factors.txt"))] +
	  expand(os.path.join(BIGWIG_DIR, '{sample}.forward.bigwig'), sample = SAMPLES) +
      expand(os.path.join(BIGWIG_DIR, '{sample}.reverse.bigwig'), sample = SAMPLES) +
      expand(os.path.join(OUTPUT_DIR, "report", '{analysis}.star.deseq.report.html'), analysis = DE_ANALYSIS_LIST.keys()) +
      expand(os.path.join(OUTPUT_DIR, "report", '{analysis}.salmon.transcripts.deseq.report.html'), analysis = DE_ANALYSIS_LIST.keys()) +
      expand(os.path.join(OUTPUT_DIR, "report", '{analysis}.salmon.genes.deseq.report.html'), analysis = DE_ANALYSIS_LIST.keys())
    },
    'deseq_report_star': {
        'description': "Produce one HTML report for each analysis based on STAR results.",
        'files':
          expand(os.path.join(OUTPUT_DIR, "report", '{analysis}.star.deseq.report.html'), analysis = DE_ANALYSIS_LIST.keys())
    },
    'deseq_report_salmon_transcripts': {
        'description': "Produce one HTML report for each analysis based on SALMON results at transcript level.",
        'files':
          expand(os.path.join(OUTPUT_DIR, "report", '{analysis}.salmon.transcripts.deseq.report.html'), analysis = DE_ANALYSIS_LIST.keys())
    },
    'deseq_report_salmon_genes': {
        'description': "Produce one HTML report for each analysis based on SALMON results at gene level.",
        'files':
          expand(os.path.join(OUTPUT_DIR, "report", '{analysis}.salmon.genes.deseq.report.html'), analysis = DE_ANALYSIS_LIST.keys())
    },
    'star_map' : {
        'description': "Produce a STAR mapping results in BAM file format.",
        'files':
          expand(os.path.join(MAPPED_READS_DIR, '{sample}_Aligned.sortedByCoord.out.bam'), sample = SAMPLES)
    },
    'star_counts': {
        'description': "Get count matrix from STAR mapping results using summarizeOverlaps.",
        'files':
          [os.path.join(COUNTS_DIR, "raw_counts", "counts_from_star.tsv")]
    },
    'genome_coverage': {
        'description': "Compute genome coverage values from BAM files - save in bigwig format",
        'files':
          expand(os.path.join(BIGWIG_DIR, '{sample}.forward.bigwig'), sample = SAMPLES) +
          expand(os.path.join(BIGWIG_DIR, '{sample}.reverse.bigwig'), sample = SAMPLES)
    },
    'fastqc': {
        'description': "post-mapping quality control by FASTQC.",
        'files':
          expand(os.path.join(FASTQC_DIR, '{sample}_Aligned.sortedByCoord.out_fastqc.zip'), sample = SAMPLES)
    },
    'salmon_index' : {
        'description': "Create SALMON index file.",
        'files':
          [os.path.join(OUTPUT_DIR, 'salmon_index', "sa.bin")]
    },
    'salmon_quant' : {
        'description': "Calculate read counts per transcript using SALMON.",
        'files':
          expand(os.path.join(SALMON_DIR, "{sample}", "quant.sf"), sample = SAMPLES) +
	  expand(os.path.join(SALMON_DIR, "{sample}", "quant.genes.sf"), sample = SAMPLES)
    },
    'salmon_counts': {
        'description': "Get count matrix from SALMON quant.",
        'files':
          [os.path.join(COUNTS_DIR, "raw_counts", "counts_from_SALMON.transcripts.tsv"),
	   os.path.join(COUNTS_DIR, "raw_counts", "counts_from_SALMON.genes.tsv"),
	   os.path.join(COUNTS_DIR, "normalized",  "TPM_counts_from_SALMON.transcripts.tsv"),
	   os.path.join(COUNTS_DIR, "normalized", "TPM_counts_from_SALMON.genes.tsv")]
    },
    'multiqc': {
        'description': "Get multiQC report based on STAR alignments and fastQC reports.",
        'files':
          [os.path.join(MULTIQC_DIR, 'multiqc_report.html')]
    }
}

# Selected output files from the above set.
selected_targets = config['execution']['target'] or ['final-report']

# FIXME: the list of files must be flattened twice(!).  We should make
# sure that the targets really just return simple lists.
from itertools import chain
OUTPUT_FILES = list(chain.from_iterable([targets[name]['files'] for name in selected_targets]))

rule all:
  input: OUTPUT_FILES

rule help:
  run:
    for key in sorted(targets.keys()):
      print('{}:\n  {}'.format(key, targets[key]['description']))

# Record any existing output files, so that we can detect if they have
# changed.
expected_files = {}
onstart:
    if OUTPUT_FILES:
        for name in OUTPUT_FILES:
            if os.path.exists(name):
                expected_files[name] = os.path.getmtime(name)

# Print generated target files.
onsuccess:
    if OUTPUT_FILES:
        # check if any existing files have been modified
        generated = []
        for name in OUTPUT_FILES:
            if name not in expected_files or os.path.getmtime(name) != expected_files[name]:
                generated.append(name)
        if generated:
            print("The following files have been generated:")
            for name in generated:
                print("  - {}".format(name))


rule translate_sample_sheet_for_report:
  input: SAMPLE_SHEET_FILE
  output: os.path.join(os.getcwd(), "colData.tsv")
  shell: "{RSCRIPT_EXEC} {SCRIPTS_DIR}/translate_sample_sheet_for_report.R {input}"

# determine if the sample library is single end or paired end
def isSingleEnd(args):
  sample = args[0]
  files = lookup('name', sample, ['reads', 'reads2'])
  count = sum(1 for f in files if f)
  if count == 2:
      return False
  elif count == 1:
      return True

def trim_galore_input(args):
  sample = args[0]
  return [os.path.join(READS_DIR, f) for f in lookup('name', sample, ['reads', 'reads2']) if f]

rule trim_galore_pe:
  input: trim_galore_input
  output:
    r1=os.path.join(TRIMMED_READS_DIR, "{sample}_R1.fastq.gz"),
    r2=os.path.join(TRIMMED_READS_DIR, "{sample}_R2.fastq.gz")
  params:
    tmp1=lambda wildcards, output: os.path.join(TRIMMED_READS_DIR, lookup('name', wildcards[0], ['reads'])[0]).replace('.fastq.gz','_val_1.fq.gz'),
    tmp2=lambda wildcards, output: os.path.join(TRIMMED_READS_DIR, lookup('name', wildcards[0], ['reads2'])[0]).replace('.fastq.gz','_val_2.fq.gz')
  log: os.path.join(LOG_DIR, 'trim_galore_{sample}.log')
  shell: "{TRIM_GALORE_EXEC} -o {TRIMMED_READS_DIR} --paired {input[0]} {input[1]} >> {log} 2>&1 && sleep 10 && mv {params.tmp1} {output.r1} && mv {params.tmp2} {output.r2}"

rule trim_galore_se:
  input: trim_galore_input
  output: os.path.join(TRIMMED_READS_DIR, "{sample}_R.fastq.gz"),
  params: tmp=lambda wildcards, output: os.path.join(TRIMMED_READS_DIR, lookup('name', wildcards[0], ['reads'])[0]).replace('.fastq.gz','_trimmed.fq.gz'),
  log: os.path.join(LOG_DIR, 'trim_galore_{sample}.log')
  shell: "{TRIM_GALORE_EXEC} -o {TRIMMED_READS_DIR} {input[0]} >> {log} 2>&1 && sleep 10 && mv {params.tmp} {output}"


rule star_index:
    input: GENOME_FASTA
    output:
        star_index_file = os.path.join(OUTPUT_DIR, 'star_index', "SAindex")
    params:
        star_index_dir = os.path.join(OUTPUT_DIR, 'star_index')
    log: os.path.join(LOG_DIR, 'star_index.log')
    shell: "{STAR_EXEC_INDEX} --runMode genomeGenerate --runThreadN {STAR_INDEX_THREADS} --genomeDir {params.star_index_dir} --genomeFastaFiles {input} --sjdbGTFfile {GTF_FILE} >> {log} 2>&1"

def map_input(args):
  sample = args[0]
  reads_files = [os.path.join(READS_DIR, f) for f in lookup('name', sample, ['reads', 'reads2']) if f]
  if len(reads_files) > 1:
    return [os.path.join(TRIMMED_READS_DIR, "{sample}_R1.fastq.gz".format(sample=sample)), os.path.join(TRIMMED_READS_DIR, "{sample}_R2.fastq.gz".format(sample=sample))]
  elif len(reads_files) == 1:
    return [os.path.join(TRIMMED_READS_DIR, "{sample}_R.fastq.gz".format(sample=sample))]

rule star_map:
  input:
    # This rule really depends on the whole directory (see
    # params.index_dir), but we can't register it as an input/output
    # in its own right since Snakemake 5.
    index_file = rules.star_index.output.star_index_file,
    reads = map_input
  output:
    os.path.join(MAPPED_READS_DIR, '{sample}_Aligned.out.bam')
  params:
    index_dir = rules.star_index.params.star_index_dir,
    output_prefix=os.path.join(MAPPED_READS_DIR, '{sample}_')
  log: os.path.join(LOG_DIR, 'star_map_{sample}.log')
  shell: "{STAR_EXEC_MAP} --runThreadN {STAR_MAP_THREADS} --genomeDir {params.index_dir} --readFilesIn {input.reads} --readFilesCommand '{GUNZIP_EXEC} -c' --outSAMtype BAM Unsorted --outFileNamePrefix {params.output_prefix} >> {log} 2>&1"

rule sort_bam:
  input: os.path.join(MAPPED_READS_DIR, '{sample}_Aligned.out.bam')
  output: os.path.join(MAPPED_READS_DIR, '{sample}_Aligned.sortedByCoord.out.bam')
  log: os.path.join(LOG_DIR, 'samtools_sort_{sample}.log')
  shell: "{SAMTOOLS_EXEC} sort -o {output} {input} >> {log} 2>&1"

rule index_bam:
  input: os.path.join(MAPPED_READS_DIR, '{sample}_Aligned.sortedByCoord.out.bam')
  output: os.path.join(MAPPED_READS_DIR, '{sample}_Aligned.sortedByCoord.out.bam.bai')
  log: os.path.join(LOG_DIR, 'samtools_index_{sample}.log')
  shell: "{SAMTOOLS_EXEC} index {input} {output} >> {log} 2>&1"

rule fastqc:
  input: os.path.join(MAPPED_READS_DIR, '{sample}_Aligned.sortedByCoord.out.bam')
  output: os.path.join(FASTQC_DIR, '{sample}_Aligned.sortedByCoord.out_fastqc.zip')
  log: os.path.join(LOG_DIR, 'fastqc_{sample}.log')
  shell: "{FASTQC_EXEC} -o {FASTQC_DIR} -f bam {input} >> {log} 2>&1"

rule salmon_index:
  input:
      CDNA_FASTA
  output:
      salmon_index_file = os.path.join(OUTPUT_DIR, 'salmon_index', "sa.bin")
  params:
      salmon_index_dir = os.path.join(OUTPUT_DIR, 'salmon_index')
  log: os.path.join(LOG_DIR, 'salmon_index.log')
  shell: "{SALMON_EXEC} index -t {input} -i {params.salmon_index_dir} -p {SALMON_INDEX_THREADS} >> {log} 2>&1"

rule salmon_quant:
  input:
      # This rule really depends on the whole directory (see
      # params.index_dir), but we can't register it as an input/output
      # in its own right since Snakemake 5.
      index_file = rules.salmon_index.output.salmon_index_file,
      reads = map_input
  output:
      os.path.join(SALMON_DIR, "{sample}", "quant.sf"),
      os.path.join(SALMON_DIR, "{sample}", "quant.genes.sf")
  params:
      index_dir = rules.salmon_index.params.salmon_index_dir,
      outfolder = os.path.join(SALMON_DIR, "{sample}")
  log: os.path.join(LOG_DIR, 'salmon_quant_{sample}.log')
  run:
    if(len(input.reads) == 1):
        COMMAND = "{SALMON_EXEC} quant -i {params.index_dir} -l A -p {SALMON_QUANT_THREADS} -r {input.reads} -o {params.outfolder} --seqBias --gcBias -g {GTF_FILE} >> {log} 2>&1"
    elif(len(input.reads) == 2):
        COMMAND = "{SALMON_EXEC} quant -i {params.index_dir} -l A -p {SALMON_QUANT_THREADS} -1 {input.reads[0]} -2 {input.reads[1]} -o {params.outfolder} --seqBias --gcBias -g {GTF_FILE} >> {log} 2>&1"
    shell(COMMAND)

rule counts_from_SALMON:
  input:
      quantFiles = expand(os.path.join(SALMON_DIR, "{sample}", "quant.sf"), sample=SAMPLES),
      quantGenesFiles = expand(os.path.join(SALMON_DIR, "{sample}", "quant.genes.sf"), sample=SAMPLES),
      colDataFile = rules.translate_sample_sheet_for_report.output
  output:
      os.path.join(COUNTS_DIR, "raw_counts", "counts_from_SALMON.transcripts.tsv"),
      os.path.join(COUNTS_DIR, "raw_counts", "counts_from_SALMON.genes.tsv"),
      os.path.join(COUNTS_DIR, "normalized", "TPM_counts_from_SALMON.transcripts.tsv"),
      os.path.join(COUNTS_DIR, "normalized", "TPM_counts_from_SALMON.genes.tsv")
  log: os.path.join(LOG_DIR, 'salmon_import_counts.log')
  shell: "{RSCRIPT_EXEC} {SCRIPTS_DIR}/counts_matrix_from_SALMON.R {SALMON_DIR} {COUNTS_DIR} {input.colDataFile} >> {log} 2>&1"


rule genomeCoverage:
  input:
    size_factors_file=os.path.join(COUNTS_DIR, "normalized", "deseq_size_factors.txt"),
    bam=os.path.join(MAPPED_READS_DIR, '{sample}_Aligned.sortedByCoord.out.bam'),
    bai=os.path.join(MAPPED_READS_DIR, '{sample}_Aligned.sortedByCoord.out.bam.bai')
  output:
    os.path.join(BIGWIG_DIR, '{sample}.forward.bigwig'),
    os.path.join(BIGWIG_DIR, '{sample}.reverse.bigwig')
  log: os.path.join(LOG_DIR, 'genomeCoverage_{sample}.log')
  shell: "{RSCRIPT_EXEC} {SCRIPTS_DIR}/export_bigwig.R {input.bam} {wildcards.sample} {input.size_factors_file} {BIGWIG_DIR} >> {log} 2>&1"

rule multiqc:
  input:
    salmon_output=expand(os.path.join(SALMON_DIR, "{sample}", "quant.sf"), sample = SAMPLES),
    star_output=expand(os.path.join(MAPPED_READS_DIR, '{sample}_Aligned.sortedByCoord.out.bam'), sample=SAMPLES),
    fastqc_output=expand(os.path.join(FASTQC_DIR, '{sample}_Aligned.sortedByCoord.out_fastqc.zip'), sample=SAMPLES),
  output: os.path.join(MULTIQC_DIR, 'multiqc_report.html')
  log: os.path.join(LOG_DIR, 'multiqc.log')
  shell: "{MULTIQC_EXEC} -o {MULTIQC_DIR} {OUTPUT_DIR} >> {log} 2>&1"

rule count_reads:
  input:
    bam = os.path.join(MAPPED_READS_DIR, "{sample}_Aligned.sortedByCoord.out.bam"),
    bai = os.path.join(MAPPED_READS_DIR, "{sample}_Aligned.sortedByCoord.out.bam.bai")
  output:
    os.path.join(MAPPED_READS_DIR, "{sample}.read_counts.csv")
  log: os.path.join(LOG_DIR, "{sample}.count_reads.log")
  params:
    single_end = isSingleEnd,
    mode = config['counting']['counting_mode'],
    nonunique = config['counting']['count_nonunique'],
    strandedness = config['counting']['strandedness'],
    feature = config['counting']['feature'],
    group_by = config['counting']['group_feature_by'],
    yield_size = config['counting']['yield_size']
  shell:
    "{RSCRIPT_EXEC} {SCRIPTS_DIR}/count_reads.R {wildcards.sample} {input.bam} {GTF_FILE} \
        {params.single_end} {params.mode} {params.nonunique} {params.strandedness} \
        {params.feature} {params.group_by} {params.yield_size} >> {log} 2>&1"

rule collate_read_counts:
  input:
    expand(os.path.join(MAPPED_READS_DIR, "{sample}.read_counts.csv"), sample = SAMPLES)
  output:
    os.path.join(COUNTS_DIR, "raw_counts", "counts_from_star.tsv")
  log: os.path.join(LOG_DIR, "collate_read_counts.log")
  params:
    out_file = os.path.join(COUNTS_DIR, "raw_counts", "counts_from_star.tsv"),
    script = os.path.join(SCRIPTS_DIR, "collate_read_counts.R")
  shell:
    "{RSCRIPT_EXEC} {params.script} {MAPPED_READS_DIR} {params.out_file} >> {log} 2>&1"


rule htseq_count:
  input: expand(os.path.join(MAPPED_READS_DIR, "{sample}_Aligned.sortedByCoord.out.bam"), sample = SAMPLES)
  output:
    stats_file = os.path.join(COUNTS_DIR, "raw_counts", "htseq_stats.txt"),
    counts_file = os.path.join(COUNTS_DIR, "raw_counts", "counts_from_star_htseq-count.txt")
  log: os.path.join(LOG_DIR, "htseq-count.log")
  params:
    tmp_file = os.path.join(COUNTS_DIR, "raw_counts", "htseq_out.txt")
  shell:
    """
    echo {SAMPLES} | {SED_EXEC} 's/ /\t/g' > {params.tmp_file}
    {HTSEQ_COUNT_EXEC} {input} {GTF_FILE} 1>> {params.tmp_file} 2>> {log};
    ## move feature count stats (e.g. __no_feature etc) to another file
    echo {SAMPLES} > {output.stats_file}; tail -n 5 {params.tmp_file} >> {output.stats_file};
    ## only keep feature counts in the counts table (remove stats)
    head -n -5 {params.tmp_file} > {output.counts_file};
    # remove temp file
    rm {params.tmp_file}
    """

# create a normalized counts table including all samples
# using the median-of-ratios normalization procedure of
# deseq2
rule norm_counts_deseq:
    input:
        counts_file = os.path.join(COUNTS_DIR, "raw_counts", "counts_from_star.tsv"),
        colDataFile = rules.translate_sample_sheet_for_report.output
    output:
        size_factors = os.path.join(COUNTS_DIR, "normalized", "deseq_size_factors.txt"),
        norm_counts = os.path.join(COUNTS_DIR, "normalized", "deseq_normalized_counts.tsv")
    log:
        os.path.join(LOG_DIR, "norm_counts_deseq.log")
    params:
        script=os.path.join(SCRIPTS_DIR, "norm_counts_deseq.R"),
        outdir=os.path.join(COUNTS_DIR, "normalized")
    shell:
        "{RSCRIPT_EXEC} {params.script} {input.counts_file} {input.colDataFile} {params.outdir} >> {log} 2>&1"

rule report1:
  input:
    counts=os.path.join(COUNTS_DIR, "raw_counts", "counts_from_star.tsv"),
    coldata=str(rules.translate_sample_sheet_for_report.output),
  params:
    outdir=os.path.join(OUTPUT_DIR, "report"),
    reportR=os.path.join(SCRIPTS_DIR, "runDeseqReport.R"),
    reportRmd=os.path.join(SCRIPTS_DIR, "deseqReport.Rmd"),
    case = lambda wildcards: DE_ANALYSIS_LIST[wildcards.analysis]['case_sample_groups'],
    control = lambda wildcards: DE_ANALYSIS_LIST[wildcards.analysis]['control_sample_groups'],
    covariates = lambda wildcards: DE_ANALYSIS_LIST[wildcards.analysis]['covariates'],
    logo = LOGO
  log: os.path.join(LOG_DIR, "{analysis}.report.star.log")
  output:
    os.path.join(OUTPUT_DIR, "report", '{analysis}.star.deseq.report.html')
  shell:
    "{RSCRIPT_EXEC} {params.reportR} --logo={params.logo} --prefix='{wildcards.analysis}.star' --reportFile={params.reportRmd} --countDataFile={input.counts} --colDataFile={input.coldata} --gtfFile={GTF_FILE} --caseSampleGroups='{params.case}' --controlSampleGroups='{params.control}' --covariates='{params.covariates}'  --workdir={params.outdir} --organism='{ORGANISM}'  >> {log} 2>&1"

rule report2:
  input:
    counts=os.path.join(COUNTS_DIR, "raw_counts", "counts_from_SALMON.transcripts.tsv"),
    coldata=str(rules.translate_sample_sheet_for_report.output)
  params:
    outdir=os.path.join(OUTPUT_DIR, "report"),
    reportR=os.path.join(SCRIPTS_DIR, "runDeseqReport.R"),
    reportRmd=os.path.join(SCRIPTS_DIR, "deseqReport.Rmd"),
    case = lambda wildcards: DE_ANALYSIS_LIST[wildcards.analysis]['case_sample_groups'],
    control = lambda wildcards: DE_ANALYSIS_LIST[wildcards.analysis]['control_sample_groups'],
    covariates = lambda wildcards: DE_ANALYSIS_LIST[wildcards.analysis]['covariates'],
    logo = os.path.join(config['locations']['pkgdatadir'], "images/Logo_PiGx.png") if os.getenv("PIGX_UNINSTALLED") else os.path.join(config['locations']['pkgdatadir'], "Logo_PiGx.png")
  log: os.path.join(LOG_DIR, "{analysis}.report.salmon.transcripts.log")
  output:
    os.path.join(OUTPUT_DIR, "report", '{analysis}.salmon.transcripts.deseq.report.html')
  shell: "{RSCRIPT_EXEC} {params.reportR} --logo={params.logo} --prefix='{wildcards.analysis}.salmon.transcripts' --reportFile={params.reportRmd} --countDataFile={input.counts} --colDataFile={input.coldata} --gtfFile={GTF_FILE} --caseSampleGroups='{params.case}' --controlSampleGroups='{params.control}' --covariates='{params.covariates}' --workdir={params.outdir} --organism='{ORGANISM}' >> {log} 2>&1"

rule report3:
  input:
    counts=os.path.join(COUNTS_DIR, "raw_counts", "counts_from_SALMON.genes.tsv"),
    coldata=str(rules.translate_sample_sheet_for_report.output)
  params:
    outdir=os.path.join(OUTPUT_DIR, "report"),
    reportR=os.path.join(SCRIPTS_DIR, "runDeseqReport.R"),
    reportRmd=os.path.join(SCRIPTS_DIR, "deseqReport.Rmd"),
    case = lambda wildcards: DE_ANALYSIS_LIST[wildcards.analysis]['case_sample_groups'],
    control = lambda wildcards: DE_ANALYSIS_LIST[wildcards.analysis]['control_sample_groups'],
    covariates = lambda wildcards: DE_ANALYSIS_LIST[wildcards.analysis]['covariates'],
    logo = os.path.join(config['locations']['pkgdatadir'], "images/Logo_PiGx.png") if os.getenv("PIGX_UNINSTALLED") else os.path.join(config['locations']['pkgdatadir'], "Logo_PiGx.png")
  log: os.path.join(LOG_DIR, "{analysis}.report.salmon.genes.log")
  output:
    os.path.join(OUTPUT_DIR, "report", '{analysis}.salmon.genes.deseq.report.html')
  shell: "{RSCRIPT_EXEC} {params.reportR} --logo={params.logo} --prefix='{wildcards.analysis}.salmon.genes' --reportFile={params.reportRmd} --countDataFile={input.counts} --colDataFile={input.coldata} --gtfFile={GTF_FILE} --caseSampleGroups='{params.case}' --controlSampleGroups='{params.control}' --covariates='{params.covariates}' --workdir={params.outdir} --organism='{ORGANISM}' >> {log} 2>&1"
