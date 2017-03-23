# -*- coding: utf-8 -*-

"""
  Level.py
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

#~~~~~~~CLASS~~~~~~~#

class Level (object):
    """
    Compute the level of a given feature on the Annotation track to avoid annotation overlaping
    """
    def __init__ (self,
                  max_depth=10,
                  offset=10,
                  filter_pos=False,
                  filter_neg=False,
                  filter_unstrand=True):
        """
        Define general options for Level class
        * max_depth
            Maximal total number of positive or negative levels.
        * offset
            Minimal distance between 2 contigous annotation features on the same level
        * filter_pos
            Filter-out annotation features on the positive strand [ DEFAULT: False ]
        * filter_neg
            Filter-out annotation features on the negative strand [ DEFAULT: False ]
        * filter_unstrand
            Filter-out annotation features with no strand specified [ DEFAULT: True ]
        """
        # Save general parameter
        self.max_depth = max_depth
        self.offset = offset
        self.pos_arrowstyle = "-|>,head_width=1,head_length=2"
        self.neg_arrowstyle = "<|-,head_width=1,head_length=2"
        self.unstrand_arrowstyle = "-"
        self.filter_pos = filter_pos
        self.filter_neg = filter_neg
        self.filter_unstrand = filter_unstrand

        # Create self containers
        self.level_dict={}
        self.count = Counter()
        self.enhanced_feature = namedtuple('enhanced_feature', ['ID','start', 'end', "arrowstyle", "level"])

    def __str__(self):
        """readable description of the object"""
        msg = "{} instance\n".format(self.__class__.__name__)

        # list all values in object dict in alphabetical order
        for k,v in OrderedDict(sorted(self.__dict__.items(), key=lambda t: t[0])).items():
            msg+="\t{}\t{}\n".format(k, v)
        return (msg)

    def __repr__ (self):
        return ("{}".format(self.__class__.__name__))

    @property
    def min_level(self):
        """Return the minimal level index"""
        return min(self.level_dict.keys())

    @property
    def max_level(self):
        """Return the minimal level index"""
        return max(self.level_dict.keys())

    @property
    def n_level(self):
        """Return the total number of levels index"""
        return len(self.level_dict)

    def __call__ (self, ID, start, end, strand):
        """
        Compute the level of an annnotation feature based on the instance options and the other feautures previously
        analysed, to avoid overlapping. Iterative call of the function has to be done with annotation features sorted
        by start coordinates.
        * ID
            Name of the feature to fit in a level
        * start
            Start coordinate of the feature to fit in a level, on the positive strand
        * end
            End coordinate of the feature to fit in a level, on the positive strand
        * strand
            Strand of the feature. Can be + - or . if unknown
        """
        self.count["all_features"] +=1

        # For features on the positive strand
        if strand == "+" and not self.filter_pos:
            level=1
            self.count["positive_features"] +=1

            while level <= self.max_depth:

                # If level is empty or if the level is free at this position
                if level not in self.level_dict or (self.level_dict[level]+self.offset) < start:
                    self.level_dict[level] = end
                    return self.enhanced_feature (ID, start, end, self.pos_arrowstyle, level)
                level+=1

        # For features on the negative strand
        elif strand == "-" and not self.filter_neg:
            level=-1
            self.count["negative_features"] +=1

            while level >= -self.max_depth:

                # If level is empty or if the level is free at this position
                if level not in self.level_dict or (self.level_dict[level]+self.offset) < start:
                    self.level_dict[level] = end
                    return self.enhanced_feature (ID, start, end, self.neg_arrowstyle, level)
                level-=1

        elif strand == "." and not self.filter_unstrand:
            self.count["unstranded_features"] +=1
            self.level_dict[0] = end
            return self.enhanced_feature (ID, start, end, self.unstrand_arrowstyle, 0)

        return None
