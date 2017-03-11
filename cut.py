#!/usr/bin/env python
# TODO pick two files
from obspy.core import UTCDateTime
import obspy
import pandas
from distaz import distaz
import os
from subprocess import Popen,PIPE

VMAX = 8
VMIN = 2
freq_lim = (0.005, 0.006, 1, 1.2)
decim = (2, 5)
file_pairs = 'pair_temp'
in_prefix = 'temp/'
out_prefix = 'out/'
CH = 'BHZ'

def pick(start,end,file_list,file):
    for filename in file_list:
        st = obspy.read(filename,headonly=True)
        b,e = st[0].stats.starttime,st[0].stats.endtime
        if( start > b and end < e ):
            file.append(filename)
            return True
    return False

def read_time(evt,n):
    (year,month,day,hour,minute,sec) = (evt['year'][n],evt['month'][n],evt['day'][n],evt['hour'][n],evt['min'][n],evt['sec'][n])
    return UTCDateTime(year,month,day,hour,minute,sec)

def file_path(dir,ch,type):
    if(type=="sac"):
        return dir + "/*" + ch + "*.SAC"
    elif(type=="resp"):
        return dir + "/RESP*" + ch

def check(stats,file1,file2):
    st = obspy.read(file1,headonly=True)
    st += obspy.read(file2,headonly=True)
    if(st[0].stats.delta == st[1].stats.delta):
        stats.append(st[0].stats.delta)
        return True
    else:
        return False

def trans(file,file_resp,f,d):
    p = Popen(['sac'], stdin=PIPE, stdout=PIPE)
    s = ""
    s += "r %s\n" % file
    s += "decimate %d;decimate %d\n" % (d[0],d[1])
    s += "rmean;rtrend\n"
    s += "transfer from evalresp fname %s to none freq %f %f %f %f\n" % (file_resp,f[0],f[1],f[2],f[3])
    s += "w over\n"
    s += "q\n"
    p.communicate(s.encode())

def cut(file,start,end):
    st = obspy.read(file)
    delta = st[0].stats.delta
    width = end - start
    npts = int(width/delta)
    n = int((start - st[0].stats.starttime)/delta)
    st[0].data = st[0].data[n:n+npts]
    st[0].stats.starttime = start
    st[0].write(outdir + "/" + st[0].stats.station + ".SAC",format='SAC')
    

pair = pandas.read_table(file_pairs,sep='\s+')

for np in range(len(pair)):
    stla1,stlo1 = pair['lat1'][np],pair['lon1'][np]
    stla2,stlo2 = pair['lat2'][np],pair['lon2'][np]
    in_file = in_prefix + pair['sta1'][np] + '_' + pair['sta2'][np] + '.lst'
    evt = pandas.read_table(in_file,sep='\s+')
    for i in range(len(evt)):
        evla,evlo = evt['lat'][i],evt['lon'][i]
        evtime = read_time(evt,i)
        d1 = distaz(evla,evlo,stla1,stlo1).degreesToKilometers()
        d2 = distaz(evla,evlo,stla2,stlo2).degreesToKilometers() 
        dist = (d1+d2)/2.0
        start = evtime + dist/VMAX
        end = evtime + dist/VMIN
        filelist1 = os.popen("ls "+file_path(pair['sta1'][np],CH,'sac')).read().split("\n")
        filelist2 = os.popen("ls "+file_path(pair['sta2'][np],CH,'sac')).read().split("\n")
        resp1 = os.popen("ls "+file_path(pair['sta1'][np],CH,'resp')).read().split("\n")
        resp2 = os.popen("ls "+file_path(pair['sta2'][np],CH,'resp')).read().split("\n")
        file1 = []
        file2 = []
        if(not (pick(start,end,filelist1,file1) and pick(start,end,filelist2,file2)) ):
            continue
        outdir = out_prefix + pair['sta1'][np] + '_' + pair['sta2'][np] + "/" + evtime.strftime("%Y_%m_%d_%H")
        os.system("mkdir -p "+outdir)
        stats = []
        if( not check(stats,file1[0],file2[0]) ):
            continue
        trans(file1[0],resp1[0],freq_lim,decim)
        trans(file2[0],resp2[0],freq_lim,decim)
        cut(file1[0],start,end)
        cut(file2[0],start,end)
