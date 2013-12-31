#!/usr/bin/env python

from feature_tbl_entry import FeatureTblEntry
from translate import *
import sys
import os.path

class Genome:

    def __init__(self):
        self.fasta = None
        self.gff = None
        self.annot = None
        self.entries = []

    def verify_file(self, filename):
        return os.path.exists(filename) 

    def addEntry(self, entry):
        entries.append(entry)
    
    def addEntries(self, entries):
        [self.entries.append(entry) for entry in entries]

    def ducttape_mrna_seq_frames(self):
        for gene in self.gff.genes:
            for mrna in gene.mrnas:
                name = mrna.name
                seq = self.fasta.get_subseq(gene.seq_name, [mrna.cds.indices[0]]) #first segment
                if seq == None:
                    return "Failed to fix "+name+": sequence does not exist.\n" 
                elif len(seq) < 6:
                    return "Failed to fix "+name+": sequence less than 6 base pairs.\n"

                pseq1 = translate(seq, 1, '+')
                pseq2 = translate(seq, 2, '+')
                pseq3 = translate(seq, 3, '+')
                nseq1 = translate(seq, 1, '-')
                nseq2 = translate(seq, 2, '-')
                nseq3 = translate(seq, 3, '-')

                annotEntry = self.annot.get_entry(name)
                if annotEntry:
                    pepSeq = annotEntry[9]
                    if pepSeq == None:
                        return "Failed to fix "+name+": trinotate missing peptide sequence.\n"

                    oldphase = mrna.cds.phase[0]
                    if pseq1 and pepSeq.find(pseq1[:-1]) == 0:
                        gene.strand = '+'
                        mrna.cds.phase[0] = 0
                    elif pseq2 and pepSeq.find(pseq2[:-1]) == 0:
                        gene.strand = '+'
                        mrna.cds.phase[0] = 1
                    elif pseq3 and pepSeq.find(pseq3[:-1]) == 0:
                        gene.strand = '+'
                        mrna.cds.phase[0] = 2
                    elif nseq1 and pepSeq.find(nseq1[:-1]) == 0:
                        gene.strand = '-'
                        mrna.cds.phase[0] = 0
                    elif nseq2 and pepSeq.find(nseq2[:-1]) == 0:
                        gene.strand = '-'
                        mrna.cds.phase[0] = 1
                    elif nseq3 and pepSeq.find(nseq3[:-1]) == 0:
                        gene.strand = '-'
                        mrna.cds.phase[0] = 2
                    else:
                        return "Failed to fix "+name+": no matching translation.\n"
                    return "Fixed "+name+" from phase "+str(oldphase)+" to phase "+str(mrna.cds.phase[0])+"\n"
                else:
                    return "Failed to fix "+name+": trinotate entry doesn't exist.\n"
        return "Failed to fix "+name+": mRNA doesn't exist.\n"

    # this also removes empty genes; could use a better name maybe...
    def remove_mrnas_with_cds_shorter_than(self, min_length):
        if self.gff:
            self.gff.remove_mrnas_with_cds_shorter_than(min_length)

    def remove_first_cds_segment_if_shorter_than(self, min_length):
        if self.gff:
            self.gff.remove_first_cds_segment_if_shorter_than(min_length)

    # maybe should be called 'create_start_codon_GenePart if sequence contains start codon'
    def verify_start_codon(self, mrna, seq_id):
        if mrna.cds:
            indices = mrna.get_cds_indices()
            seq = self.fasta.get_subseq(seq_id, [indices[0]])
            if has_start_codon(seq):
                mrna.add_start_codon(indices[0][0])

    def verify_stop_codon(self, mrna, seq_id):
        if mrna.cds:
            indices = mrna.get_cds_indices()
            last_pair = indices[len(indices)-1]
            seq = self.fasta.get_subseq(seq_id, [last_pair])
            if has_stop_codon(seq):
                mrna.add_stop_codon(last_pair[1])

    def verify_all_starts_and_stops(self):
        for gene in self.gff.genes:
            for mrna in gene.mrnas:
                if not mrna.has_start():
                    self.verify_start_codon(mrna, gene.seq_name)
                if not mrna.has_stop():
                    self.verify_stop_codon(mrna, gene.seq_name)

    def generateEntries(self):
        for gene in self.gff.genes:
            newEntries = gene.to_tbl_entries()
            for entry in newEntries:
                if entry.type == 'gene':
                    self.annot.annotate_gene(entry)
                elif entry.type == 'CDS':
                    self.annot.annotate_cds(entry)
                elif entry.type == 'mRNA':
                    self.annot.annotate_mrna(entry)
                self.entries.append(entry)

    def write_string(self, genes = None, errors = None):
        output = ''

        if self.fasta == None or self.gff == None or self.annot == None:
            return output
       
        output += '>Feature SeqId\n'

        for seq in self.fasta.entries:
            if genes != None and not genes:
                return output

            entries = []
            for gene in self.gff.genes:
                if gene.seq_name != seq[0]:
                    continue

                if genes != None and gene.name not in genes:
                    continue

                if genes != None:
                    genes.remove(gene.name)

                newEntries = gene.to_tbl_entries()
                for entry in newEntries:
                    if entry.type == 'gene':
                        self.annot.annotate_gene(entry)
                    elif entry.type == 'CDS':
                        self.annot.annotate_cds(entry)
                    elif entry.type == 'mRNA':
                        self.annot.annotate_mrna(entry)
                    entries.append(entry)

            # If there are any entries, write this section of the tbl file
            if len(entries) > 0:
                output += '>Feature '+seq[0]+'\n'
                output += '1\t'+str(len(seq[1]))+'\tREFERENCE\n\t\t\tPBARC\t12345\n'

                for entry in entries:    
                    output += entry.write_to_string()+'\n'
        return output

    def remove_all_gene_segments(self, prefix):
        self.gff.remove_all_gene_segments(prefix)

    def obliterate_genes_related_to_mrnas(self, mrna_names):
        self.gff.obliterate_genes_related_to_mrnas(mrna_names)

    def rename_maker_mrnas(self):
        count = 1000000
        for gene in self.gff.genes:
            for mrna in gene.mrnas:
                if mrna.is_maker_mrna():
                    old_name = mrna.name
                    new_name = 'BDOR_' + str(count)
                    mrna.name = new_name
                    self.annot.rename_mrna(old_name, new_name)
                    count += 1

