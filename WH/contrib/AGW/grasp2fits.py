#!/usr/bin/env python

#% $Id$ 

#
# Copyright (C) 2006
# ASTRON (Netherlands Foundation for Research in Astronomy)
# and The MeqTree Foundation
# P.O.Box 2, 7990 AA Dwingeloo, The Netherlands, seg@astron.nl
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

# a python script to convert GRASP 'grd' files to 
# FITS files. Thanks to Walter Brisken (NRAO) for
# the code that reads in the GRASP data.

import os
import sys
import numarray
import pyfits
import math 
from string import split, strip

def usage( prog ):
        print 'usage : %s <infile_grasp> <outfile_fits> ' % prog
        return 1

def getdata( filename ):
	text = open(filename, 'r').readlines()
	data = []
	L = len(text)
	i = 0
	while(text[i][0:4] != '++++'):
		i = i+1
		if i >= L:
			print 'bogus input file : ++++ never found'
			return data,0

	print 'input grd file contains %d comments' % i
	
	info = split(strip(text[i+1]))
	if(info[0] != '1'):
		print 'bogus input file'
		return data,0
	
	info = split(strip(text[i+2]))
	icomp = int(info[1])
	ncomp = int(info[2])
	igrid = int(info[3])
	if igrid != 1:
		print 'not a UV grid'
		return data,0
	if icomp != 3:
		print 'not linear polarization'
		return data,0
	
	info = split(strip(text[i+5]))
	nx = int(info[0])
	ny = int(info[1])
	if nx != ny:
		print 'unsupported : nx != ny'
		return data, 0
	
	info = split(strip(text[i+4]))
	scale = (float(info[2])-float(info[0]))/float(nx-1)
	
	for j in range(2*ncomp):
		data.append([])
	
	for j in range(i+6, L):
		comps = split(strip(text[j]))
		for k in range(2*ncomp):
			data[k].append(float(comps[k]))

	return data, (scale*180.0/math.pi)

def totalpower( data, nx ):
	Z = numarray.zeros( (nx, nx), numarray.Float32 )
	C = len(data)
	L = len(data[0])
	m = 0.0
        y_max = -1000
        x_max = -1000
        data_max = -1000000.0
	for y in range(nx):
		for x in range(nx):	
			i = y + nx*x
			s = 0.0;
			for j in range(C):
				s = s + data[j][i]*data[j][i];
			Z[x][y] = s
                        if Z[x][y] > data_max:
                          data_max = Z[x][y]
                          x_max = x
                          y_max = y

			if s > m:
				m = s;

	Z = Z/m
	
	return Z, x_max, y_max

def main( argv ):
        data, scale = getdata(argv[1])

	ncomp = len(data)
	if(ncomp <= 0): 
		exit

	size = len(data[0])

	nx = int(math.sqrt(size))
	if(nx*nx != size):
		print 'data not square'
		exit

	print 'grd file x, y dimensions = %d' % nx
	print 'grd file scale = %f deg / pix' % scale

        # convert to radians'
        scale = math.pi * scale  / 180.0

        # presently get data array as total power 
        # we may want additional formats
	Z, x_max, y_max = totalpower(data, nx);
        
        # turn 2D array into a 4D array so that pyfits will
        # generate an image with NAXIS = 4
        temp_array = numarray.zeros((1,1,Z.shape[0],Z.shape[1]),type=Z.type())
        temp_array[0,0,:Z.shape[0],:Z.shape[1]] = Z
        # create basic FITS file
        hdu = pyfits.PrimaryHDU(temp_array)
        hdu.header.update('CTYPE1', 'M')
        hdu.header.update('CDELT1', scale, 'in radians')
        hdu.header.update('CRPIX1', y_max+1, 'in pixels (one relative)')
        hdu.header.update('CRVAL1', 0.0, ' M = 0 at field centre')
        hdu.header.update('CTYPE2', 'L')
        hdu.header.update('CDELT2', scale, 'in radians')
        hdu.header.update('CRPIX2', x_max+1, 'in pixels (one relative)')
        hdu.header.update('CRVAL2', 0.0, 'L = 0 at field centre')

        # add dummy stuff for time (axis 3) / frequency (axis4)
        # as a Vells must always have time and frequency axes
        hdu.header.update('CTYPE3', 'TIME')
        hdu.header.update('CDELT3', 1, 'in sec')
        hdu.header.update('CRPIX3', 1, 'in pixels (one relative)')
        hdu.header.update('CRVAL3', 1.0, 'equates to grid point')
        hdu.header.update('CTYPE4', 'FREQ')
        hdu.header.update('CDELT4', 1, 'in Hz')
        hdu.header.update('CRPIX4', 1, 'in pixels (one relative)')
        hdu.header.update('CRVAL4', 1.0, 'equates to grid point')
        hdu.header.update('CPLX', 0, 'false as data is real ')
        hdu.header.update('CELLS', 1, 'true as we want cells')

        # write out FITS file
        outfile = argv[2]
        # delete any previous file
        if os.path.exists(outfile):
          os.remove(outfile)
        hdu.writeto(outfile)
#=============================
if __name__ == "__main__":
  if len(sys.argv) < 3:
    usage(sys.argv[0])
  else:
    main(sys.argv)
