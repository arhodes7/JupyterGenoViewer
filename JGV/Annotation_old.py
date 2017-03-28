# -*- coding: utf-8 -*-

"""
  JGV is a Python3 package for an embed genomic viewer in Jupyter notebook. Do not import the package in a
  non-interactive environment

  Copyright 2016 Adrien Leger <aleg@ebi.ac.ul>
  [Github](https://github.com/a-slide)

  This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
  License as published by the Free Software Foundation; either version 3 of the License, or(at your option) any later
  version

  This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
  warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
  (http://www.gnu.org/licenses/gpl-3.0.html).

  You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
  Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
"""

# Strandard library imports
from collections import OrderedDict, namedtuple, Counter
from os import access, R_OK
import csv

# Third party import
import pysam
import pandas as pd

# Local lib import
from JGV_helper_fun import *
from JGV_helper_fun import jprint as print

#~~~~~~~CLASS~~~~~~~#

class Annotation(object):

    #~~~~~~~FUNDAMENTAL METHODS~~~~~~~#

    def __init__ (self, fp, name=None, verbose=False):
        """
         * fp
            A standard gff3 file (http://www.ensembl.org/info/website/upload/gff3.html) or gtf
            (http://www.ensembl.org/info/website/upload/gff.html)containing features annotations. Could be uncompressed
            or archived in gz format. Ideally the file would be already indexed with tabix bgzip. If not the program
            will sort the features and index the file (can take time)
        *  name
            Name of the data file that will be used as track name for plotting. If not given, will be deduced from fp
            file name
        * verbose
            If True, will print more information during initialisation and calls of all the object methods.
        """
        #Save self variable
        self.name = name if name else file_basename(fp)
        self.verbose=verbose
        self.counted = False

        # Verify that the file is readable
        if not access(fp, R_OK):
            raise IOError ("{} is not readable".format(fp))

        # Define file format and attributes field parser
        if extensions(fp)[0] == "gtf":
            self.format = "gtf"
            self.get_ID = self._get_gtf_ID
        elif extensions(fp)[0] == "gff3":
            self.format = "gff3"
            self.get_ID = self._get_gff3_ID
        else:
            raise ValueError ("The file is not in gtf/gff3 format (.gff3/.gtg/+-.gz). \
            Please provide a correctly formated file")

        # Save the file path list
        self.fp = fp

        # If not indexed, sort and compress and index the original file with tabix
        if not access(fp+".tbi", R_OK):

            # Import in a panda dataframe, remove empty rows, and convert coordinates in integer
            if self.verbose:  print("Indexing file with tabix\n\tImport annotation file and clean data")
            col_names = ["seqname","source","feature","start","stop","score","strand","frame","attribute"]
            df = pd.read_csv(fp, names=col_names, sep="\t")
            df.dropna(inplace=True)
            df[['start', 'stop']] = df[['start', 'stop']].astype(int)

            # Sort the dataframe
            if self.verbose: print("\tSort lines by coordinates")
            df.sort_values(by=["seqname","start","stop"], inplace=True)

            # Remove the extension, name the output file and write in file
            if self.verbose: print("\tWrite a new sorted annotation file")
            temp_file = "{}/{}_sorted.{}".format(dir_path(fp), file_basename(fp),extensions(fp)[0])
            df.to_csv(temp_file, sep="\t", header=False, index=False, quoting=csv.QUOTE_NONE)

            # Compress and index the sorted file with tabix
            if self.verbose: print("\tCompress and index with tabix")
            self.fp = pysam.tabix_index(temp_file, preset="gff", force=True)

        with pysam.TabixFile(self.fp, parser=pysam.asGTF()) as tbf:
            self.seqid_list = [i.decode() for i in tbf.contigs]
            self.n_seq = len(self.seqid_list)


    def __str__(self):
        """readable description of the object"""
        msg = "{} instance\n".format(self.__class__.__name__)
        # list all values in object dict in alphabetical order
        for k,v in OrderedDict(sorted(self.__dict__.items(), key=lambda t: t[0])).items():
            msg+="\t{}\t{}\n".format(k, v)
        return (msg)


    def __repr__ (self):
        return ("{}_{}_{} seq".format(self.__class__.__name__, self.name, self.n_seq))

    #~~~~~~~PROPERTY METHODS~~~~~~~#

    @property
    def seqid_count(self):
        """List of all the sequence ids found in the annotation file"""
        if not self.counted: self._count()
        return self._seqid_count

    @property
    def feature_type_count(self):
        """List of all the sequence ids found in the annotation file"""
        if not self.counted: self._count()
        return self._feature_type_count

    @property
    def all_feature_count(self):
        """List of all the sequence ids found in the annotation file"""
        if not self.counted: self._count()
        return self._all_feature_count


    #~~~~~~~PRIVATE METHODS~~~~~~~#

    def _count(self):
        """Count all features, seqid, and feature type in the annotation file in one pass"""
        # Counters
        seqid_count = Counter()
        feature_type_count = Counter()
        all_feature_count = 0

        # Iterate throught file and count
        with pysam.TabixFile(self.fp, parser=pysam.asGTF()) as tbf:
            for line in tbf.fetch():
                seqid_count[line.contig]+=1
                feature_type_count[line.feature]+=1
                all_feature_count+=1

        # Convert Seqid_table in dataframe
        self._seqid_count = pd.DataFrame.from_dict(seqid_count, orient='index', dtype=int)
        self._seqid_count.columns = ['count']
        self._seqid_count.sort_values(by="count", inplace=True, ascending=False)

        # Convert Seqid_table in dataframe
        self._feature_type_count = pd.DataFrame.from_dict(feature_type_count, orient='index', dtype=int)
        self._feature_type_count.columns = ['count']
        self._feature_type_count.sort_values(by="count", inplace=True, ascending=False)

        # Store the all feature counter
        self._all_feature_count = all_feature_count

        # Set the flag to True so we don't have to do it again
        self.counted = True

    def _get_gtf_ID (self, line):
        """
        Parse a gtf line and extract the feature ID corresponding to the feature type of the line, if possible.
        If not found, then an empty string will be returned.
        """
        if line.feature == "exon":
            id_field = "exon_id"
        elif line.feature == "CDS":
            id_field = "cdsid"
        elif line.feature == "transcript":
            id_field = "transcript_id"
        elif line.feature == "gene":
            id_field = "gene_id"
        else:
            return ""

        for a in line.attributes.strip().split(";"):
            if a:
                l = a.strip().split(" ")
                if len(l) == 2:
                    if l[0] ==  id_field:
                        return l[1][1:-1]
        return ""

    def _get_gff3_ID (self, line):
        """
        Parse a gff3 line and extract the feature ID.
        If not found, then an empty string will be returned.
        """
        for a in line.attributes.strip().split(";"):
            if a:
                l = a.strip().split("=")
                if len(l) == 2:
                    if l[0] == "ID":
                        return l[1]
        return ""

    #~~~~~~~PUBLIC METHODS~~~~~~~#

    def interval_features (self, seqid, start, end, feature_types=[]):
        """
        Parse the annotation file for the given seqid and interval and return a dataframe containing all the features
        found for each original line in the gff or gtf file. Features are identified by their ID for gff3 file. For gtf
        file the ID is parsed only for exon, cds, transcript or genes, if found.
        * seqid
            Name of the sequence from the initial fasta file to display
        * start
            Start of the window to display. If not given will start from 0 [ DEFAULT: None ]
        * end
            End of the window to display. If not given will start from end of the sequence [ DEFAULT: None ]
        * feature_types
            List of features types for which a track will be displayed if at least 1 feature of this type was found in
            the requested interval ( "exon"|"transcript"|"gene"|"CDS"...). If not given, all features type found in the
            interval will be displayed [ DEFAULT: [] ]
        """
        # Init list to collect data and a custume named tuple to store the info
        feature = namedtuple('feature', ["ID","start","end","strand","type"])
        feature_list = []

        # Verify that the sequence is in the seqid list
        if seqid not in self.seqid_list:
            if self.verbose:
                print("Seqid ({}) not found in the list for the annotation {}".format(seqid, self.name))
            return pd.DataFrame()

        # Iterate over the indexed file containing the features
        with pysam.TabixFile(self.fp, parser=pysam.asGTF()) as f:

            for l in f.fetch(seqid, start, end, parser=pysam.asGTF()):
                if not feature_types or l.feature in feature_types:
                    feature_list.append(feature( self.get_ID (l), l.start, l.end, l.strand, l.feature))

            df= pd.DataFrame(feature_list)

            if self.verbose and not df.empty:
                for k,v in df.groupby("type"):
                    print ("{}: {}".format(k, len(v)))

            return df
