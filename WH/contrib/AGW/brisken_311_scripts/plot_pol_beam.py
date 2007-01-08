#!/usr/bin/env python

import biggles
import Numeric
import sys
import math
from string import split, strip

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

	print '%d comments' % i
	
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

def func_linewidth( i, n, z0, z_min, z_max ):
	f = float(n-i)/(1.5*float(n))
	r = int(255*f)
	return 0x10101*r
	

def usage( prog ):
	print 'usage : %s <infile> [-{l|L} <d>]' % prog
	return 1

def getlevs( a1, b1, a2, b2 ):
	levs1 = []
	levs2 = []

	print a1, b1, a2, b2

	print 'R = %f\n' % (b2/b1)
	
	w1 = b1
	w2 = b1/100.0
	for i in range(7):
		w1 = w1/1.99526
		w2 = w2/1.99526
		print w1, w2
		if w1 > a1 and w1 < b1:
			levs1.append(w1)
		if w2 > a2 and w2 < b2:
			levs2.append(w2)

	print 'levs1 : ', levs1
	print 'levs2 : ', levs2

	return levs1, levs2

def func_color1(i,n,z0,zmin, zmax):
	return 'black'

def func_color2(i,n,z0,zmin, zmax):
	return 'grey'

def plot( Z1, Z2, scale, nx, outfile, levs ):
	X = Numeric.zeros( (nx), Numeric.Float )
	Y = Numeric.zeros( (nx), Numeric.Float )

	min1 = 1e9
	max1 = 0.0
	min2 = 1e9
	max2 = 0.0

	for i in range(nx):
		for j in range(nx):
			if Z1[j][i] < min1:
				min1 = Z1[j][i]
			if Z1[j][i] > max1:
				max1 = Z1[j][i]
			if Z2[j][i] < min2:
				min2 = Z2[j][i]
			if Z2[j][i] > max2:
				max2 = Z2[j][i]

	levs1, levs2 = getlevs(min1, max1, min2, max2)

	start = -scale*(nx-1.0)/2.0

	for x in range(nx):
		X[x] = start + x*scale
		Y[x] = start + x*scale
	
	P = biggles.FramedPlot()
	P.xlabel='[Degrees]'
	P.ylabel='[Degrees]'
	cntrs1 = biggles.Contours(Z1, X, Y, levels=levs1, linewidth=0.5)
	cntrs2 = biggles.Contours(Z2, X, Y, levels=levs2, linewidth=0.5)
	cntrs1.func_color = func_color1
	cntrs2.func_color = func_color2
	P.add(cntrs1);
	P.add(cntrs2);
	P.show()
	P.save_as_eps(outfile)
	P.write_img(300, 300, "polbeam.png")

def copolpower( data, nx ):
	Z = Numeric.zeros( (nx, nx), Numeric.Float )
	C = len(data)
	for y in range(nx):
		for x in range(nx):	
			i = y + nx*x
			s = 0.0;
			for j in range(0, 2):
				s = s + data[j][i]*data[j][i];
			Z[x][y] = s

	return Z

def crosspolpower( data, nx ):
	Z = Numeric.zeros( (nx, nx), Numeric.Float )
	L = len(data[0])
	for y in range(nx):
		for x in range(nx):	
			i = y + nx*x
			s = 0.0;
			for j in range(2, 4):
				s = s + data[j][i]*data[j][i];
			Z[x][y] = s

	return Z

def totalpower( data, nx ):
	Z = Numeric.zeros( (nx, nx), Numeric.Float )
	C = len(data)
	L = len(data[0])
	m = 0.0
	for y in range(nx):
		for x in range(nx):	
			i = y + nx*x
			s = 0.0;
			for j in range(C):
				s = s + data[j][i]*data[j][i];
			Z[x][y] = s
			if s > m:
				m = s;

	Z = Z/m
	
	return Z

def amplitude( data, nx ):
	Z = Numeric.zeros( (nx, nx), Numeric.Float )
	C = len(data)
	L = len(data[0])
	m = 0.0
	for y in range(nx):
		for x in range(nx):	
			i = x + nx*y
			s = 0.0;
			for j in range(C):
				s = s + data[j][i]*data[j][i];
			s = math.sqrt(s)
			Z[y][x] = s
			if s > m:
				m = s;

	Z = Z/m
	
	return Z

def linlevs( spacing ):
	levs = []
	l = 1.0
	while(1):
		l = l - spacing
		if(l <= 0.0):
			break
		levs.append(l);
	return levs

def loglevs( factor ):
	levs = []
	l = 1.0
	for i in range(8):
		l = l*factor
		levs.append(l)
	return levs

def main( argv ):
	data, scale = getdata(argv[1])

	levs = loglevs(0.5)

	if len(argv) > 2:
		if(argv[2] == '-l'):
			if len(argv) > 3:
				levs = linlevs(float(argv[3]))
		if(argv[2] == '-L'):
			if len(argv) > 3:
				levs = loglevs(float(argv[3]))

	ncomp = len(data)
	if(ncomp <= 0): 
		return 1

	size = len(data[0])

	nx = int(math.sqrt(size))
	if(nx*nx != size):
		print 'data not square'
		return 1

	print 'nx = %d' % nx
	print 'scale = %f deg / pix' % scale

	Z1 = copolpower(data, nx);
	Z2 = crosspolpower(data, nx);
	plot(Z1, Z2, scale, nx, "polbeam.eps", levs)

if len(sys.argv) < 2:
	usage(sys.argv[0])
else:
	main(sys.argv)
