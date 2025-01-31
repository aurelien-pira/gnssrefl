# toolbox for GPS/GNSS data analysis
import datetime
from datetime import date
import getpass
import json
import math
import os
import pickle
import re
import requests
import subprocess
import sys
import sqlite3
from urllib.parse import urlparse
import time
from ftplib import FTP #import FTP commands from python's built-in ftp library
from ftplib import FTP_TLS


import scipy.signal as spectral
from scipy.interpolate import interp1d

import matplotlib.pyplot as plt
import numpy as np
import wget
from numpy import array

import gnssrefl.read_snr_files as snr
import gnssrefl.karnak_libraries as k

# for future ref
#import urllib.request


# various numbers you need in the GNSS world
# mostly frequencies and wavelengths
class constants:
    c= 299792458 # speed of light m/sec
#   GPS frequencies and wavelengths
    fL1 = 1575.42 # MegaHz 154*10.23
    fL2 = 1227.60 # 120*10.23
    fL5 = 115*10.23 # L5
#  GPS wavelengths
    wL1 = c/(fL1*1e6) # meters wavelength
    wL2 = c/(fL2*1e6)
    wL5 = c/(fL5*1e6)
#   galileo frequency values
    gal_L1 = 1575.420
    gal_L5 = 1176.450
    gal_L6 = 1278.70
    gal_L7 = 1207.140
    gal_L8 = 1191.795
#  galileo wavelengths, meters
    wgL1 = c/(gal_L1*1e6)
    wgL5 = c/(gal_L5*1e6)
    wgL6 = c/(gal_L6*1e6)
    wgL7 = c/(gal_L7*1e6)
    wgL8 = c/(gal_L8*1e6)

#   beidou frequencies and wavelengths
    bei_L2 = 1561.098
    bei_L7 = 1207.14
    bei_L6 = 1268.52
    wbL2 = c/(bei_L2*1e6)
    # these values are defined in Rinex 3 
    wbL7 = c/(bei_L7*1e6)
    wbL6 = c/(bei_L6*1e6)
    # does this even exist? I am using gps l5 for now
    bei_L5 = 1176.45
    wbL5 = c/(bei_L5*1e6)

#   Earth rotation rate used in GPS Nav message
    omegaEarth = 7.2921151467E-5 #	%rad/sec
    mu = 3.986005e14 # Earth GM value


class wgs84:
    """
    wgs84 parameters for Earth radius and flattening
    """
    a = 6378137. # meters Earth radius
    f  =  1./298.257223563 # flattening factor
    e = np.sqrt(2*f-f**2) # 

def useful_t_tools(year, doy): #modified with dictionary
    """
    Original author: Kristine Larson
    Modified by : Aurélien Pira
    Date : 2022oct18
    
    Merging of 'ymd2doy' and 'ydoych' by K. Larson.
    The return of the function is modified with a dictionary.
    
    Parameters
    ----------
    year :      integer
    doy :       integer (day of year)
    
    Returns
    ---------
    year :      integer
    month :     integer
    day :       integer
    cyyyy :     string (four character year)
    cdoy :      string (three character day of year)
    YMD :       string (date as in '19-12-01' for December 1, 2019)
    """
    #Extracts the year, month and day values as an integer since 'doy2ymd' function    
    year, month, day = doy2ymd(year, doy)
    
    #Convert year and doy to various string format
    str_doy = '{:03d}'.format(doy)
    str_yyyy = str(year)
    str_yy = str_yyyy[2:4]
    
    #cyyyy, cyy, cdoy = ydoych(year,doy) delete

    str_dd = '{:02d}'.format(day)
    str_month = char_month_converter(month)
    YMD = str_yy + str_month + str_dd
    
    #Combine all values ​​in a dictionary
    utt_val = {'year':year, 'month':month, 'day':day,
             'str_doy':str_doy, 'str_yyyy':str_yyyy, 'str_yy':str_yy,
             'str_dd':str_dd, 'str_month':str_month, 'YMD': YMD}
    
    return(utt_val)
	
def myfavoriteobs():
    """
    returns list of SNR obs needed for gfzrnx. 

    """
    # not even sure why i have C here for beidou
    gobblygook = 'G:S1C,S2X,S2L,S2S,S2X,S5I,S5Q,S5X+R:S1P,S1C,S2P,S2C+E:S1,S5,S6,S7,S8+C:S2C,S7C,S6C,S2I,S7I,S6I,S2X,S6X,S7X'

    return gobblygook

def myfavoritegpsobs():
    """
    returns list of SNR obs needed for gfzrnx. 

    """
    # can't have non-GPS obs if you ask for only GPS signals 
    gobblygook = 'G:S1C,S2X,S2L,S2S,S2X,S5I,S5Q,S5X'

    return gobblygook

def ydoych(year,doy):
    """
    Converts year and doy to various character strings

    Parameters:
    ---------
    year : integer
        year

    doy : integer
        day of year

    Returns:
    -------
    cyyyy : string
        4 character year

    cyy : string
        2 character year

    cdoy : string
        3 character day of year

    """
    cyyyy = str(year)
    cyy = cyyyy[2:4]
    cdoy = '{:03d}'.format(doy)

    return cyyyy,cyy,cdoy


def define_filename(station,year,doy,snr):
    """
    Return the SNR filename 

    Parameters:
    -----------
    station : string
        name  (4 char lowercase)

    year : integer
        year

    doy : integer
        day of year

    snr : integer
        SNR file type (e.g. 99, 66)

    Returns :
    ---------
    fname : string
        snrfile name to be used

    fname2 : string
        snrfile name to be used - with xz compression extension

    """
    xdir = os.environ['REFL_CODE'] # main directory for SNR files
    cyyyy, cyy, cdoy = ydoych(year,doy) 

    f= station + cdoy + '0.' + cyy + '.snr' + str(snr)
    fname = xdir + '/' + cyyyy + '/snr/' + station + '/' + f 
    fname2 = xdir + '/' + cyyyy  + '/snr/' + station + '/' + f  + '.xz'
    return fname, fname2

def define_and_xz_snr(station,year,doy,snr):
    """
    finds and checks for existence of a SNR file
    uncompresses if that is needed (xz or gz)

    Parameters
    ----------

    station: string
        station name, 4 characters

    year : integer
        year

    doy : integer
        day of year

    snr : integer
        kind of snr file (66,77, 88 etc)

    Returns
    --------------

    fname : string
        name of the SNR file

    fname2 : string
        no longer used but kept for backwards capability

    snre : boolean
        whether the file exists or not

    """
    xdir = os.environ['REFL_CODE']
    cyyyy, cyy, cdoy = ydoych(year,doy)
    f= station + cdoy + '0.' + cyy + '.snr' + str(snr)
    fname = xdir + '/' + cyyyy + '/snr/' + station + '/' + f
    fname2 = xdir + '/' + cyyyy  + '/snr/' + station + '/' + f  + '.xz'
    fname3 = xdir + '/' + cyyyy  + '/snr/' + station + '/' + f  + '.gz'
    snre = False
    # add gzip
    if os.path.isfile(fname):
        snre = True
    else:
        if os.path.isfile(fname2):
            subprocess.call(['unxz', fname2])
        else:
            if os.path.isfile(fname3):
                subprocess.call(['gunzip', fname3])
        # make sure the uncompression worked
        if os.path.isfile(fname):
            snre = True

#   return fname2 but only for backwards compatibility
    return fname, fname2, snre 

def define_filename_prevday(station,year,doy,snr):
    """
    finds filename for day before the input date

    Parameters
    -------------

    station: string
        4 character station name  

    year: integer
        year

    doy: integer
        day of year

    snr: integer
        SNR file type (66,88, etc)

    Returns:
    ---------------
    returns snr filename for the PREVIOUS day

    """
    xdir = os.environ['REFL_CODE']
    year = int(year)
    doy = int(doy)
    if (doy == 1):
        pyear = year -1
        #print('found january 1, so previous day is december 31')
        doyx,cdoyx,cyyyy,cyy = ymd2doy(pyear,12,31)
        pdoy = doyx 
    else:
#       doy is decremented by one and year stays the same
        pdoy = doy - 1
        pyear = year

    # change to characters 
    cyyyy, cyy, cdoy = ydoych(pyear,pdoy)

    f= station + cdoy + '0.' + cyy + '.snr' + str(snr)
    fname = xdir + '/' + cyyyy + '/snr/' + station + '/' + f 
    fname2 = xdir + '/' + cyyyy + '/snr/' + station + '/' + f + '.xz'

    return fname, fname2

def azimuth_angle(RecSat, East, North):
    """
    computes azimuth angle 

    Inputs:
    ------------
    RecSat : 3-vector (numpy?) 
        meters

    East : 

    North : 3-vector (numpy?)

    inputs are receiver satellite vector (meters)
    east and north unit vectors, computed with the up vector
    returns 
    ------

    azangle : float
        azimuth angle in degrees
    """
    staSatE = East[0]*RecSat[0] + East[1]*RecSat[1] + East[2]*RecSat[2]
    staSatN = North[0]*RecSat[0] + North[1]*RecSat[1] + North[2]*RecSat[2]
#    azangle = 0
    azangle = np.arctan2(staSatE, staSatN)*180/np.pi
    if azangle < 0:
        azangle = 360 + azangle
# 
    return azangle

def rot3(vector, angle):
    """
    input a vector (3) and output the same vector rotated by an angle
    in radians apparently.
    original code from ryan hardy
    """
    rotmat = np.matrix([[ np.cos(angle), np.sin(angle), 0],
                        [-np.sin(angle), np.cos(angle), 0],
                        [             0,             0, 1]])
    vector2 = np.array((rotmat*np.matrix(vector).T).T)[0]
    return vector2

def xyz2llh(xyz, tol):
    """
    given xyz vector, computes latitude, longitude and height

    Parameters
    -----------
    xyz: list or np array 
        X,Y,Z in meters

    tol: float
        tolerance in meters for the calculation (1E-8 is good enough)

    Returns
    --------------
    lat : float
        latitude in radians

    lon : float
        longitude in radians

    h : float
        ellipsoidal height in WGS84 in meters

    """
    x=xyz[0]
    y=xyz[1]
    z=xyz[2]
    lon = np.arctan2(y, x)
    p = np.sqrt(x**2+y**2)
    lat0 = np.arctan((z/p)/(1-wgs84.e**2))
    b = wgs84.a*(1-wgs84.f)
    error = 1
    a2=wgs84.a**2
    i=0 # make sure it doesn't go forever
    while error > tol and i < 6:
        n = a2/np.sqrt(a2*np.cos(lat0)**2+b**2*np.sin(lat0)**2)
        h = p/np.cos(lat0)-n
        lat = np.arctan((z/p)/(1-wgs84.e**2*n/(n+h)))
        error = np.abs(lat-lat0)
        lat0 = lat
        i+=1
    return lat, lon, h

def xyz2llhd(xyz):
    """
    converts three vector from cartesian coordinates to latitude,longitude,height

    Parameters:
    --------------
    xyz : three vector of floats
        Cartesian position in meters

    Returns:
    --------------
    lat : float
        latitude in degrees

    lon : float
        longitude in degrees

    h : float
        ellipsoidal height in WGS84 in meters

    """
    x=xyz[0]
    y=xyz[1]
    z=xyz[2]
    lon = np.arctan2(y, x)
    p = np.sqrt(x**2+y**2)
    lat0 = np.arctan((z/p)/(1-wgs84.e**2))
    b = wgs84.a*(1-wgs84.f)
    error = 1
    a2=wgs84.a**2
    i=0 # make sure it doesn't go forever
    tol = 1e-10
    while error > tol and i < 6:
        n = a2/np.sqrt(a2*np.cos(lat0)**2+b**2*np.sin(lat0)**2)
        h = p/np.cos(lat0)-n
        lat = np.arctan((z/p)/(1-wgs84.e**2*n/(n+h)))
        error = np.abs(lat-lat0)
        lat0 = lat
        i+=1
    return lat*180/np.pi, lon*180/np.pi, h



def zenithdelay(h):
    """
    the output is a very simple zenith troposphere delay in meters
    this is NOT to be used for precise geodetic applications

    Parameters:
    -----------
    h: float
        ellipsoidal (height) in meters

    Returns:
    -----------
    zd : float
        simple zenith delay for the troposphere in meters

    """

    zd = 0.1 + 2.31*np.exp(-h/7000.0)
    return zd

def up(lat,lon):
    """
    returns the up unit vector, and local east and north unit vectors needed 
    for azimuth calc.

    Parameters
    ----------
    latitude : float
        radians

    longitude : float
        radians

    returns
    ----------
    East : three vector
        local transformation unit vector

    North : three vector
        local transformation unit vector

    """
    xo = np.cos(lat)*np.cos(lon)
    yo = np.cos(lat)*np.sin(lon)
    zo = np.sin(lat)
    u= np.array([xo,yo,zo])    
#    c ... also define local east/north for station: took these from fortran
    North = np.zeros(3)
    East = np.zeros(3)
    North[0] = -np.sin(lat)*np.cos(lon)
    North[1] = -np.sin(lat)*np.sin(lon)
    North[2] = np.cos(lat)
    East[0] = -np.sin(lon)
    East[1] = np.cos(lon)
    East[2] = 0
    return u, East, North

def norm(vect):
    """
    given a three vector - return its norm
    """  
    nv = np.sqrt(np.dot(vect,vect))
    return nv

def elev_angle(up, RecSat):
    """
    computes satellite elevation angle

    Parameters
    -------------------
    up : 3 vector float 
        unit vector in the up direction

    RecSat : 3 vector numpy 
        Cartesian vector pointing from receiver to satellite in meters

    returns
    --------------
    angle: float
        elevation angle in radians

    """
    ang = np.arccos(np.dot(RecSat,up) / (norm(RecSat)))
    angle = np.pi/2.0 - ang
    return angle

def sp3_interpolator(t, tow, x0, y0, z0, clock0):
    """
    author: originally from ryan hardy  

    Parameters
    -------
    t : float

    tow :  float

    x0 : float

    y0 : float

    z0 : float

    clock0 : float


    inputs are??? tow is GPS seconds
    xyz are the precise satellite coordinates (in meters)
    clocks are likely satellite clock corrections (microseconds)
    i believe n is the order fit, based on what i recall.
    these values do not agree with my test cases in matlab or fortran
    presumably there is an issue with the estimation of the coefficients.
    they are good enough for calculating an elevation angle used in reflectometry
    """
    # ryan set it to 7 - which is not recommended by the paper
    # ryan confirmed that he doesn't know why this doesn't work ...
    n = 7 # don't know why this was being sent before
    coeffs = np.zeros((len(t), 3, n))
    # whatever ryan was doing was not allowed here.  had to make
    # sure these are treated as integers
    s1 = int(-(n-1)/2)
    s2 = int((n-1)/2+1)
#    print(s1,s2)
    
    omega = 2*2*np.pi/(86164.090530833)
    x = np.zeros(len(t))
    y = np.zeros(len(t))
    z = np.zeros(len(t))
    clockf = interp1d(tow, clock0, bounds_error=False, fill_value=clock0[-1])
    clock = clockf(t)
    # looks like it computes it for a number of t values?
    for i in range(len(t)):
        # sets up a matrix with zeros in it - 7 by 7
        independent = np.matrix(np.zeros((n, n)))
        # no idea what this does ...
        m = np.sort(np.argsort(np.abs(tow-t[i]))[:n])
        tinterp = tow[m]-np.median(tow[m])
        # set x, y, and z to zeros
        xr = np.zeros(n)
        yr = np.zeros(n)
        zr = np.zeros(n)
        # coefficients are before and after the time
        for j in range(s1, s2):
            independent[j] = np.cos(np.abs(j)*omega*tinterp-(j > 0)*np.pi/2)
        for j in range(n):
            xr[j], yr[j], zr[j] = rot3(np.array([x0[m], y0[m], z0[m]]).T[j], omega/2*tinterp[j])
 #           print(j, xr[j], yr[j], zr[j])
			
        independent = independent.T
        eig =  np.linalg.eig(independent)
        iinv  = (eig[1]*1/eig[0]*np.eye(n)*np.linalg.inv(eig[1]))
# set up the coefficients
        coeffs[i, 0] = np.array(iinv*np.matrix(xr).T).T[0]
        coeffs[i, 1] = np.array(iinv*np.matrix(yr).T).T[0]
        coeffs[i, 2] = np.array(iinv*np.matrix(zr).T).T[0]
        
        j = np.arange(s1, s2)
        # time since median of the values?
        tx = (t[i]-np.median(tow[m]))
        r_inertial =  np.sum(coeffs[i][:, j]*np.cos(np.abs(j)*omega*tx-(j > 0)*np.pi/2), -1)

        x[i], y[i], z[i] = rot3(r_inertial, -omega/2*tx)
        # returns xyz, in meters ? and satellite clock in microseconds
        return x*1e3, y*1e3, z*1e3, clock
 
def dec31(year):
    """
    Parameters 
    ---------
    input: integer
        year

    Returns :

    doy : integer
        day of year for December 31
    """
    today=datetime.datetime(year,12,31)
    doy = (today - datetime.datetime(year, 1, 1)).days + 1

    return doy

def ymd2doy(year,month,day):
    """
    Parameters
    --------------

    year : integer

    month : integer

    day : integer
        day of the month

    returns
    ---------
    doy : integer
         day of year
    cdoy : string 
         three character day of year
    cyyyy : string 
         four character year
    cyy : string 
         two character year
    """
    today=datetime.datetime(year,month,day)
    doy = (today - datetime.datetime(today.year, 1, 1)).days + 1
    cyyyy, cyy, cdoy = ydoych(year,doy)
    return doy, cdoy, cyyyy, cyy


def rinex_sopac(station, year, month, day):
    """
    picks up a hatanaka RINEX file from SOPAC - converts to o
    can also be called as station, year, doy, 0

    Parameters: 
    -----------
    station : string
        4 char station name  

    year : integer

    month : integer

    day : integer

    """
    if (day == 0):
        doy = month
        year, month, day, cyyyy,cdoy, YMD = ydoy2useful(year,doy)
        cyy = cyyyy[2:4]
    else:
        doy,cdoy,cyyyy,cyy = ymd2doy(year,month,day)

    crnxpath = hatanaka_version()
    if os.path.exists(crnxpath):
        sopac = 'ftp://garner.ucsd.edu'
        oname,fname = rinex_name(station, year, month, day) 
        file1 = fname + '.Z'
        path1 = '/pub/rinex/' + cyyyy + '/' + cdoy + '/' 
        url1 = sopac + path1 + file1 

        try:
            wget.download(url1,file1)
            subprocess.call(['uncompress', file1])
            subprocess.call([crnxpath, fname])
            subprocess.call(['rm', '-f',fname])
        except:
            subprocess.call(['rm', '-f',file1])
            subprocess.call(['rm', '-f',fname])
    else:
        hatanaka_warning()


def hatanaka_warning():
    """
    return warning about missing Hatanaka executable
    """
    print('WARNING WARNING WARNING WARNING')
    print('You are trying to convert Hatanaka files without having the proper')
    print('executable, CRX2RNX. See links in the gnssrefl documentation')



def getnavfile(year, month, day):
    """
    picks up nav file and stores it in the ORBITS directory

    Parameters
    -----------
    year: integer

    month: integer
        if day is zero, the month value is really the day of year

    day: integer
        day

    Returns
    ----------
    navname : string
        name of navigation file

    navdir : string
        location of where the file should be stored

    foundit : boolean
        whether the file was found

    """
    foundit = False
    ann = make_nav_dirs(year)
    if (day == 0):
        doy = month
        year, month, day, cyyyy,cdoy, YMD = ydoy2useful(year,doy)
        cyy = cyyyy[2:4]
    else:
        doy,cdoy,cyyyy,cyy = ymd2doy(year,month,day)
    navname,navdir = nav_name(year, month, day)
    nfile = navdir + '/' + navname
    if not os.path.exists(navdir):
        subprocess.call(['mkdir',navdir])

    if os.path.exists(nfile):
        foundit = True
    if (not foundit) and (os.path.exists(nfile + '.xz' )):
        subprocess.call(['unxz',nfile + '.xz'])
        foundit = True

    if not os.path.exists(nfile):
        navstatus = navfile_retrieve(navname, cyyyy,cyy,cdoy) 
        if navstatus:
            #print('\n navfile being moved to online storage area')
            subprocess.call(['mv',navname, navdir])
            foundit = True
        else:
            print('No navfile found')

    return navname,navdir,foundit

def getsp3file(year,month,day):
    """
    retrieves IGS sp3 precise orbit file from CDDIS
    inputs are year, month, and day 
    modified in 2019 to use wget 
    returns the name of the file and its directory

    year : integer

    month : integer

    day : integer

    20jun14 - add CDDIS secure ftp

    returns
    -----------
    name : string
        filename for the orbits

    fdir : string
        directory for the orbits

    """
    name, fdir = sp3_name(year,month,day,'igs') 
    cddis = 'ftp://cddis.nasa.gov'


    # try new way using secure ftp
    #dir_secure = '/pub/gnss/data/daily/' + cyyyy + '/' + cdoy + '/' + cyy + 'o/'
    #file_secure = file1

    if (os.path.isfile(fdir + '/' + name ) == True):
        okok = 1
        #print('sp3file already exists')
    else:
        gps_week = name[3:7]
        file1 = name + '.Z'
        filename1 = '/gnss/products/' + str(gps_week) + '/' + file1
        url = cddis + filename1 
        # new secure ftp way
        sec_dir = '/gnss/products/' + str(gps_week) + '/'
        sec_file = file1
        try:
            #wget.download(url,file1)
            cddis_download_2022B(sec_file, sec_dir) 
            #cddis_download(sec_file, sec_dir) 
            subprocess.call(['uncompress',file1])
            store_orbitfile(name,year,'sp3') 
        except:
            print('some kind of problem -remove empty file')
            subprocess.call(['rm',file1])

#   return the name of the file so that if you want to store it
    return name, fdir

def getsp3file_flex(year,month,day,pCtr):
    """
    returns the name of the orbit file and its directory from CDDIS
    only gets the old-style filenames

    Parameters
    ----------
    year : integer

    month : integer

    day : integer

    pCtr : string
        3 character orbit processing center

    Returns
    -----------
    name : string
        filename for the orbits

    fdir : string
        directory for the orbits

    fexist : boolean
        whether the orbit file was successfully found

    """
    # really should use mgex version
    # returns name and the directory
    name, fdir = sp3_name(year,month,day,pCtr) 
    #print(name, fdir)
    gps_week = name[3:7]
    file1 = pCtr + name[3:8] + '.sp3.Z'
    name = pCtr + name[3:8] + '.sp3'
    foundit = False
    ofile = fdir + '/' + name
    # new CDDIS way
    sec_dir = '/gnss/products/' + str(gps_week) + '/'
    sec_file = file1

    if (os.path.isfile(ofile ) == True):
        foundit = True
    elif (os.path.isfile(ofile + '.xz') == True):
        subprocess.call(['unxz', ofile + '.xz'])
        foundit = True
    else:
        filename1 = '/gnss/products/' + str(gps_week) + '/' + file1
        cddis = 'ftp://cddis.nasa.gov'
        url = cddis + filename1 
        try:
            cddis_download_2022B(sec_file, sec_dir) 
            subprocess.call(['uncompress',file1])
            store_orbitfile(name,year,'sp3') 
            foundit = True
        except:
            print('some kind of problem-remove empty file, if it exists')
        if os.path.isfile(sec_file):
            siz = os.path.getsize(sec_file)
            if (siz == 0):
                subprocess.call(['rm','-f',sec_file])

    return name, fdir, foundit

def getsp3file_mgex(year,month,day,pCtr):
    """
    retrieves MGEX sp3 orbit files 

    Parameters
    ---------------
    year : integer

    month : integer

    day : integer

    pCtr : string
        name of the orbit center

    this is spaghetti code, i apologize

    """
    foundit = False
    # this returns sp3 orbit product name
    if day == 0:
        doy = month
        year,month,day= ydoy2ymd(year,doy)
    name, fdir = sp3_name(year,month,day,pCtr) 
    gps_week = name[3:7]
    igps_week = int(gps_week)
    igps_week_at_cddis = 1 + int(gps_week)
    #print('GPS week', gps_week,igps_week)
    file1 = name + '.Z'

    # get the sp3 filename for the new format
    doy,cdoy,cyyyy,cyy = ymd2doy(year,month,day)
    if pCtr == 'gbm': # GFZ
        file2 = 'GFZ0MGXRAP_' + cyyyy + cdoy + '0000_01D_05M_ORB.SP3.gz'
    if pCtr == 'wum': # Wuhan, 
        # used to only use first 24 hours, but now can use whole orbit file
        #nyear, ndoy = nextdoy(year,doy)
        #cndoy = '{:03d}'.format(ndoy); cnyear = '{:03d}'.format(nyear)
        file2 = 'WUM0MGXULA_' + cyyyy + cdoy + '0000_01D_05M_ORB.SP3.gz'
    if pCtr == 'grg': # french group
        file2 = 'GRG0MGXFIN_' + cyyyy + cdoy + '0000_01D_15M_ORB.SP3.gz'
    if pCtr == 'sha': # shanghai observatory
        # change to 15 min 2020sep08
        # this blew up - do not know why. removing Shanghai for now
        file2 = 'SHA0MGXRAP_' + cyyyy + cdoy + '0000_01D_15M_ORB.SP3.gz'
    # try out JAXA - should have GPS and glonass
    if pCtr == 'jax':
        file2 = 'JAX0MGXFIN_' + cyyyy + cdoy + '0000_01D_05M_ORB.SP3.gz'
    # this is name without the gzip
    name2 = file2[:-3] 

     
    # this is the default setting - no file exists
    mgex = 0
    n1 = os.path.isfile(fdir + '/' + name)
    n1c = os.path.isfile(fdir + '/' + name + '.xz')
    if (n1 == True):
        print('first kind of MGEX sp3file already exists online')
        mgex = 1
        foundit = True
    elif (n1c  == True): 
        print('xz first kind of MGEX sp3file already exists online-unxz it')
        fx =  fdir + '/' + name + '.xz'
        subprocess.call(['unxz', fx])
        mgex = 1
        foundit = True

    n2 = os.path.isfile(fdir + '/' + name2)
    n2c = os.path.isfile(fdir + '/' + name2 + '.xz')
    if (n2 == True):
        print('MGEX sp3file already exists online')
        mgex = 2 ; foundit = True
    elif (n2c == True):
        print('MGEX sp3file already exists online')
        mgex = 2 ; foundit = True
        fx =  fdir + '/' + name2 + '.xz'
        subprocess.call(['unxz', fx])

    if (mgex == 2):
        name = name2
    if (mgex == 1):
        name = file1[:-2]

    if not foundit:
        print('Type 1 filename',file1)
        print('Type 2 filename',file2)
        if (mgex == 0):
            if (igps_week > 2137):
            # filename without the compression ending
                name = file2[:-3] 
                secure_file = file2
                print('check the correct GPS week ')
                secure_dir = '/gps/products/mgex/' + str(igps_week) + '/'
                foundit = orbfile_cddis(name, year, secure_file, secure_dir, file2)

                if not foundit:
                    print('use the wrong GPS week at CDDIS')
                    secure_dir = '/gps/products/mgex/' + str(igps_week_at_cddis) + '/'
                    foundit = orbfile_cddis(name, year, secure_file, secure_dir, file2)
            else:
                secure_dir = '/gps/products/mgex/' + str(igps_week) + '/'
                secure_file = file1 # Z compressed
                name = file1[:-2]
                foundit = orbfile_cddis(name, year, secure_file, secure_dir, file1)
                if (not foundit):
                    name = file2[:-3]
                    secure_file = file2
                    foundit = orbfile_cddis(name, year, secure_file, secure_dir, file2)

    return name, fdir, foundit

def orbfile_cddis(name, year, secure_file, secure_dir, file2):
    """
    tries to download a file from a directory at CDDIS
    file2 is like this: GFZ0MGXRAP_' + cyyyy + cdoy + '0000_01D_05M_ORB.SP3.gz
    it then stores it the year directory (with a given name)

    Parameters:
    ------------
    name : string
        the name of the orbit file you want to download from CDDIS

    year : integer

    secure_file : string
        name of the file at CDDIS
 
    secure_dir : string
        where the file lives at CDDIS

    file2 : string
        name without the compression???

    Returns:

    foundit : boolean
        whether the file was found

    now checks that file size is not zero. allows old file name downloads
    ------------

    """
    # assume file was not found
    foundit = False
    print(secure_dir, secure_file)
    # Z or gz expected ...
    if secure_file[-3:] == '.gz':
        gzip = True
    else:
        gzip = False
    try:
        cddis_download_2022B(secure_file, secure_dir)
    except:
        ok = 1
    # found a file
    if os.path.isfile(secure_file):
        siz = os.path.getsize(secure_file)
        #print('File size', siz)
        if (siz == 0):
            subprocess.call(['rm', secure_file])
        else:
            foundit = True
            if gzip:
                subprocess.call(['gunzip', secure_file])
                store_orbitfile(name,year,'sp3') ; 
            else:
                subprocess.call(['uncompress', secure_file])
                store_orbitfile(name,year,'sp3') ; 

    return foundit

def kgpsweek(year, month, day, hour, minute, second):
    """
    Parameters
    ----------
    year : string
        4 char
    month : string 
        2 char
    day : string
        2 char
    hour: string
        2 char
    minute : string
        2 char

    second : integer?

    returns
    --------
    GPS_wk : integer
        GPS week
    GPS_sec_wk : intger
        GPS second of the week

    """

    year = np.int(year)
    M = np.int(month)
    D = np.int(day)
    H = np.int(hour)
    minute = np.int(minute)
    
    UT=H+minute/60.0 + second/3600. 
    if M > 2:
        y=year
        m=M
    else:
        y=year-1
        m=M+12
        
    JD=np.floor(365.25*y) + np.floor(30.6001*(m+1)) + D + (UT/24.0) + 1720981.5
    GPS_wk=np.floor((JD-2444244.5)/7.0);
    GPS_wk = np.int(GPS_wk)
    GPS_sec_wk=np.rint( ( ((JD-2444244.5)/7)-GPS_wk)*7*24*3600)            
     
    return GPS_wk, GPS_sec_wk

def kgpsweekC(z):
    """
    takes in time tag from a RINEX file and converts to gps week/sec
    so the input is a character string of length 26.  in this 
    kind of string, the year is only two characters

    returns
    --------
    gpsw : integer
        GPS week

    gpss : integer
        GPS seconds

    """
    y= np.int(z[1:3])
    m = np.int(z[4:6])
    d=np.int(z[7:9])
    hr=np.int(z[10:12])
    mi=np.int(z[13:15])
    sec=np.float(z[16:26])
    gpsw,gpss = kgpsweek(y+2000,m,d,hr,mi,sec)
    return gpsw, gpss

def igsname(year,month,day):
    """
    returns the name of an IGS orbit file

    Parameters
    -----------
    year : integer
        four character year

    month : integer

    day : integer 

    Returns
    ------------
    name : str
        IGS orbit name

    clockname : string
        COD clockname 

    """
    [wk,sec]=kgpsweek(year,month,day,0,0,0)
    x=int(sec/86400)
    dd = str(wk) + str(x) 
    name = 'igs' + str(wk) + str(x) + '.sp3'
    # i think at some point they changed to lower case?
   # clockname = 'COD' + dd + '.CLK_05S.txt'
    clockname = 'cod' + dd + '.clk_05s'

    return name, clockname

def read_sp3(file):
    """
    borrowed from Ryan Hardy, who got it from David Wiese ... 
    """
    try:      
        f = open(file)
        raw = f.read()
        f.close()
        lines  = raw.splitlines()
        nprn = np.int(lines[2].split()[1])
        lines  = raw.splitlines()[22:-1]
        epochs = lines[::(nprn+1)]
        nepoch =  len(lines[::(nprn+1)])
        week, tow, x, y, z, clock, prn = np.zeros((nepoch*nprn, 7)).T
        for i in range(nepoch):
            year, month, day, hour, minute, second = np.array(epochs[i].split()[1:], dtype=float)
            week[i*nprn:(i+1)*nprn], tow[i*nprn:(i+1)*nprn] = \
				kgpsweek(year, month, day, hour, minute, second)
            for j in range(nprn):
                prn[i*nprn+j] =  int(lines[i*(nprn+1)+j+1][2:4])
                x[i*nprn+j] = np.float(lines[i*(nprn+1)+j+1][4:18])
                y[i*nprn+j] = np.float(lines[i*(nprn+1)+j+1][18:32])
                z[i*nprn+j] = np.float(lines[i*(nprn+1)+j+1][32:46])
                clock[i*nprn+j] = np.float(lines[(i)*(nprn+1)+j+1][46:60])
    except:
        print('sorry - the sp3file does not exist')
        week,tow,x,y,z,prn,clock=[0,0,0,0,0,0,0]
		
    return week, tow, prn, x, y, z, clock

def myreadnav(file):
    """
    input is navfile name
    output is complicated - broadcast ephemeris blocks
    """
# input is the nav file
    try:
        f = open(file, 'r')
        nav = f.read()
        f.close()
        nephem = (len(nav.split('END OF HEADER')[1].splitlines())-1)/8
        nephem = int(nephem) #    print(nephem)         
        lines = nav.split('END OF HEADER')[1].splitlines()[1:]
        table = np.zeros((nephem, 32))
        #print('Total number of ephemeris messages',nephem)
        for i in range(nephem):
            for j in range(8):
                if j == 0:
                    prn = int(lines[i*8+j][:2])
                    year = int(lines[i*8+j].split()[1])
                    if year > 76:
                        year += 1900
                    else:
                        year += 2000
                    month = int(lines[i*8+j].split()[2])
                    day = int(lines[i*8+j].split()[3])
                    hour = int(lines[i*8+j].split()[4])
                    minute = int(lines[i*8+j].split()[5])
                    second = float(lines[i*8+j][17:22])
                    table[i, 0] = prn
#                    print('Ephem for: ', prn, year, month, day, hour, minute)
                    week, Toc = kgpsweek(year, month, day, hour, minute, second)
                    table[i, 1] =  week
                    table[i, 2] = Toc
                    Af0 = np.float(lines[i*8][-3*19:-2*19].replace('D', 'E'))
                    Af1 = np.float(lines[i*8][-2*19:-1*19].replace('D', 'E'))
                    Af2 = np.float(lines[i*8][-19:].replace('D', 'E'))
                    table[i,3:6] = Af0, Af1, Af2
                elif j != 7:
                    for k in range(4):
                        value = np.float(lines[i*8+j][19*k+3:19*(k+1)+3].replace('D', 'E'))
                        table[i,2+4*j+k] = value
                elif j== 7:
                    table[i,-2]= np.float(lines[i*8+j][3:19+3].replace('D', 'E'))
                    if not lines[i*8+7][22:].replace('D', 'E').isalpha():
                        table[i,-1]= 0
                    else:
                        table[i, -1] = np.float(lines[i*8+7][22:41].replace('D', 'E'))
# output is stored as:
#
# 0-10   prn, week, Toc, Af0, Af1, Af2, IODE, Crs, delta_n, M0, Cuc,\
# 11-22    ecc, Cus, sqrta, Toe, Cic, Loa, Cis, incl, Crc, perigee, radot, idot,\
# 23-24?                   l2c, week, l2f, sigma, health, Tgd, IODC, Tob, interval 
# week would be 24 by this scheme?
# Toe would be 14 
#	
        ephem = table
    except:
        #print('This ephemeris file does not exist',file)
        ephem = []
    return ephem
def myfindephem(week, sweek, ephem, prn):
    """
# inputs are gps week, seconds of week
# ephemerides and PRN number
# returns the closest ephemeris block after the epoch
# if one does not exist, returns the first one    
"""
    t = week*86400*7+sweek
# defines the TOE in all the ephemeris 
# he is taking the week and adding ToE (14?)
# poorly coded is all i'm gonna say

    teph = ephem[:, 24]*86400*7+ephem[:, 14]     
    prnmask = np.where(ephem[:, 0]== prn)    

    [nr,nc]=np.shape(prnmask)
#    print(nr,nc)
    if nc == 0:
        print('no ephemeris for that PRN number')
        closest_ephem = []
    else:
        try:          
            signmask = np.where(t >= teph[prnmask])
            proxmask =  np.argmin(t-teph[prnmask][signmask])
            closest_ephem = ephem[prnmask][signmask][proxmask]
        except:
#           print('using first ephemeris - but not after epoch')
            closest_ephem = ephem[prnmask][0]
        
  
    return closest_ephem

def findConstell(cc):
    """
    cc : string  is one character (from rinex satellite line)
        constellation definition
        G : GPS
        R : Glonass
        E : Galileo
        C : Beidou

    out : integer
        value added to satellite number for our system,
        0 for GPS, 100 for Glonass, 200 for Galileo, 300 for everything else
    """
    if (cc == 'G' or cc == ' '):
        out = 0
    elif (cc == 'R'): # glonass
        out = 100
    elif (cc == 'E'): # galileo
        out = 200
    else:
        out = 300
        
    return out

def myscan(rinexfile):
    """
    stripping the header code came from pyrinex.  
    data are stored into a variable called table
    columns 0,1,2 are PRN, GPS week, GPS seconds, and observables
    rows are the different observations. these should be stored 
    properly - this is a kluge
    """
    f=open(rinexfile,'r')
    lines = f.read().splitlines(True)
    lines.append('')
    # setting up a set or directionary
    # sets must be unique - so that is hwy he checks to see if it already exists
    header={}        
    eoh=0
# looks like it reads all the header lines, so you can extract them as you like
    for i,line in enumerate(lines):
        if "END OF HEADER" in line:
            eoh=i
            break
#        print(line[60:].strip())
        if line[60:].strip() not in header:
            header[line[60:].strip()] = line[:60].strip()
        else:
            header[line[60:].strip()] += " "+line[:60].strip()
    
    header['APPROX POSITION XYZ'] = [float(i) for i in header['APPROX POSITION XYZ'].split()]
    w = header['APPROX POSITION XYZ']
#    print(w)
#    approxpos = [float(i) for i in header['APPROX POSITION XYZ'].split()]
    header['# / TYPES OF OBSERV'] = header['# / TYPES OF OBSERV'].split()
#    typesObs = header['# / TYPES OF OBSERV'].split()
    aa=header['# / TYPES OF OBSERV']
    types = aa[1:] # this means from element 1 to the end
    # these are from the pyrinex verison of hte code
    header['# / TYPES OF OBSERV'][0] = int(header['# / TYPES OF OBSERV'][0])
    header['INTERVAL'] = float(header['INTERVAL'])
    # need to get approx position of the receiver
    x,y,z = header['APPROX POSITION XYZ']
    numobs = int(np.ceil(header['# / TYPES OF OBSERV'][0]))

# initial three columns in the newheader variable
    newheader = 'PRN\tWEEK\tTOW'
# add in the observation types from this file
    for j in range(numobs):
        newheader += '\t'+types[j]
# header using the Ryan Hardy style
#    print(newheader)

#    # set the line reader to after the end of the header
    # this tells it where to start
    i=eoh+1
    # so try to implement ryan hardy's storing procedure, where 0 is prn,
    # 1 is week, 2 is seconds of week, 3-N are the observables
    table = np.zeros((0, numobs+3))
    print('number of observables ', numobs)
    if numobs > 10:
        print('Tooooo many observables. I cannot deal with this')
        return
    print('line number ' , eoh)
    l = 0 # start counter for blocks
    while True:
        if not lines[i]: break
        if not int(lines[i][28]):
#            print(lines[i])
#            z=lines
            [gw,gs]=kgpsweekC(lines[i])
#            print('week and sec', gw,gs)    
            numsvs = int(lines[i][30:32])  # Number of visible satellites at epoch
#            print('number of satellites',numsvs)
            # strictly speaking i don't understand this line.
            table = np.append(table, np.zeros((numsvs, numobs+3)), axis=0)
            table[l:l+numsvs, 1] = gw
            table[l:l+numsvs, 2] = gs
            #headlength.append(1 + numsvs//12)
            sp = []
                
            if(numsvs>12):
                for s in range(numsvs):
                    xv = findConstell(lines[i][32+(s%12)*3:33+(s%12)*3]) 
                    sp.append(xv + int(lines[i][33+(s%12)*3:35+(s%12)*3]))
                    if s>0 and s%12 == 0:
                        i+= 1  # For every 12th satellite there will be a new row with satellite names                sats.append(sp) # attach satellites here
            else:
                for s in range(numsvs):
                    xv = findConstell(lines[i][32+(s%12)*3:33+(s%12)*3])
                    sp.append(xv + int(lines[i][33+(s%12)*3:35+(s%12)*3]))

#            print(len(sp), 'satellites in this block', sp)
            for k in range(numsvs): 
                table[l+k,0]=sp[k]
                if (numobs > 5):
                    for d in range(5):
                        gg = d*16
                        f=lines[i+1+2*k][gg:gg+14]
                        if not(f == '' or f.isspace()):
                            val = np.float(lines[i+1+2*k][gg:gg+14])
                            table[l+k, 3+d] = val
                    for d in range(numobs-5):
                        gg = d*16
                        f=lines[i+2+2*k][gg:gg+14]
                        if not (f == '' or f.isspace()):
                            val = np.float(lines[i+2+2*k][gg:gg+14])
                            table[l+k, 3+5+d] = val
                else:
                    for d in range(numobs):
                        gg = d*16
                        f = lines[i+1+2*k][gg:gg+14]
                        if (f == '' or f.isspace()):
                            val = np.float(lines[i+2+2*k][gg:gg+14])
                            table[l+k, 3+d] = val

            i+=numsvs*int(np.ceil(header['# / TYPES OF OBSERV'][0]/5))+1
            l+=numsvs
        else:
            print('there was a comment or some header info in the rinex')
            flag=int(lines[i][28])
            if(flag!=4):
                print('this is a flag that is not 4', flag)
            skip=int(lines[i][30:32])
            print('skip this many lines',skip)
            i+=skip+1
            print('You are now on line number',i)
    [nr,nc]=np.shape(table)
    print('size of the table variable is ',nr, ' by ', nc)    
    # code provided by ryan hardy - but not needed???
#    format = tuple(np.concatenate((('%02i', '%4i', '%11.7f'), 
#							((0, numobs+3)[-1]-3)*['%14.3f'])))
# I think this takes the newheader and combines it with the information in
# the table variable
    obs =  dict(zip(tuple(newheader.split('\t')), table.T))
    return obs,x,y,z

def read_files(year,month,day,station):
    """
    """   

    doy,cdoy,cyyyy,cyy = ymd2doy(year,month,day)
    # i have a function for this ....
    rinexfile = station + cdoy + '0.' + cyy + 'o'
    navfilename = 'auto'  + cdoy + '0.' + cyy +  'n'
    if os.path.isfile(rinexfile):
        print('rinexfile exists')
    else:
        print(rinexfile)
        print('get the rinex file')
        rinex_unavco(station, year, month, day)
    # organize the file names
    print('get the sp3 and clock file names')
    sp3file, cname = igsname(year,month,day)

    # define some names of files
    if os.path.isfile(navfilename):
        print('nav exists')
    else:
        print('get nav')
        navname,navdir,foundit = getnavfile(year,month,day)
    print('read in the broadcast ephemeris')
    ephemdata = myreadnav(navfilename)
    if os.path.isfile(cname):
        print('file exists')
    else:        
        print('get the CODE clock file')
        codclock(year,month,day)
    pname = cname[0:9] + 'pckl'
    print('pickle', pname)
    # if file exists already     
    if os.path.isfile(pname):
        print('read existing pickle file')
        f = open(pname, 'rb')
        [prns,ts,clks] = pickle.load(f)
        f.close()
    else:
        print('read and save as pickle')
        prns, ts, clks = readPreciseClock(cname)
        # and then save them
        f = open(pname, 'wb')
        pickle.dump([prns,ts,clks], f)
        f.close()
    if os.path.isfile(sp3file):
        print('sp3 exsts')
    else:
        print('get sp3')
        getsp3file(year,month,day)
    print('read in the sp3 file', sp3file)
    
    sweek, ssec, sprn, sx, sy, sz, sclock = read_sp3(sp3file)
    
#20    print('len returned data', len(ephemdata), navfilename
    rinexpickle = rinexfile[0:11] + 'pclk'
    if os.path.isfile(rinexpickle):
        print('rinex pickle exists')
        f=open(rinexpickle,'rb')
        [obs,x,y,z]=pickle.load(f)
        f.close()
    else:     
        print('read the RINEX file ', rinexfile)
        obs,x,y,z = myscan(rinexfile)
        print('save as pickle file')
        f=open(rinexpickle,'wb')
        pickle.dump([obs,x,y,z], f)
        f.close()
        
    return ephemdata, prns, ts, clks, sweek, ssec, sprn, sx, sy,sz,sclock,obs,x,y,z

def propagate(week, sec_of_week, ephem):
    """
    inputs are GPS week, seconds of the week, and the appropriate 
    ephemeris block from the navigation message
    returns the x,y,z, coordinates of the satellite 
    and relativity correction (also in meters), so you add,
    not subtract

    """

# redefine the ephem variable
    prn, week, Toc, Af0, Af1, Af2, IODE, Crs, delta_n, M0, Cuc,\
    ecc, Cus, sqrta, Toe, Cic, Loa, Cis, incl, Crc, perigee, radot, idot,\
    l2c, week, l2f, sigma, health, Tgd, IODC, Tob, interval = ephem
    sweek = sec_of_week
    # semi-major axis
    a = sqrta**2
    t = week*7*86400+sweek
    tk = t-Toe
    # no idea if Ryan Hardy is doing this correctly - it should be in a function
    tk  =  (tk - 302400) % (302400*2) - 302400
    n0 = np.sqrt(constants.mu/a**3)
    n = n0+ delta_n
    Mk = M0 + n*tk
    i = 0
    Ek = Mk
    E0 = Mk + ecc*np.sin(Mk)
    # solve kepler's equation
    while(i < 15 or np.abs(Ek-E0) > 1e-12):
        i +=1
        Ek = Mk + ecc*np.sin(E0) 
        E0 = Mk + ecc*np.sin(Ek)
    nuk = np.arctan2(np.sqrt(1-ecc**2)*np.sin(Ek),np.cos(Ek)-ecc)
    Phik = nuk + perigee
    duk = Cus*np.sin(2*Phik)+Cuc*np.cos(2*Phik)
    drk = Crs*np.sin(2*Phik)+Crc*np.cos(2*Phik)
    dik = Cis*np.sin(2*Phik)+Cic*np.cos(2*Phik)
    uk = Phik + duk
    rk = a*(1-ecc*np.cos(Ek))+drk
       
    ik = incl+dik+idot*tk
    xkp = rk*np.cos(uk)
    ykp = rk*np.sin(uk)
    Omegak = Loa + (radot-constants.omegaEarth)*tk -constants.omegaEarth*Toe
    xk = xkp*np.cos(Omegak)-ykp*np.cos(ik)*np.sin(Omegak)
    yk = xkp*np.sin(Omegak)+ykp*np.cos(ik)*np.cos(Omegak)
    zk = ykp*np.sin(ik) 
    # using class
    F = -2*np.sqrt(constants.mu)/constants.c
    relcorr = F*ecc*sqrta*np.sin(Ek)
#    return [xk, yk, zk], relcorr
    return [xk[0], yk[0], zk[0]], relcorr


def get_ofac_hifac(elevAngles, cf, maxH, desiredPrec):
    """
    computes two factors - ofac and hifac - that are inputs to the
    Lomb-Scargle Periodogram code.
    We follow the terminology and discussion from Press et al. (1992)
    in their LSP algorithm description.

    INPUT
    elevAngles:  vector of satellite elevation angles in degrees 
    cf:(L-band wavelength/2 ) in meters    
    maxH:maximum LSP grid frequency in meters
    desiredPrec:  the LSP frequency grid spacing in meters
    i.e. how precise you want he LSP reflector height to be estimated
    OUTPUT
    ofac: oversampling factor
    hifac: high-frequency factor
    """
# in units of inverse meters
    X= np.sin(elevAngles*np.pi/180)/cf     

# number of observations
    N = len(X) 
# observing Window length (or span)
# units of inverse meters
    W = np.max(X) - np.min(X)         

# characteristic peak width, meters
    cpw= 1/W

# oversampling factor
    ofac = cpw/desiredPrec 

# Nyquist frequency if the N observed data samples were evenly spaced
# over the observing window span W, in meters
    fc = N/(2*W)

# Finally, the high-frequency factor is defined relative to fc
    hifac = maxH/fc  

    return ofac, hifac

def strip_compute(x,y,cf,maxH,desiredP,pfitV,minH):
    """
    strips snr data
    Parameters
    -----------
    x : numpy array 
        elevation angles in degrees
    y : numpy array
        SNR data 

    cf : float
        scale factor for given frequency

    maxH : float
        maximum reflector height in meters

    desiredP : float
        precision of Lomb Scargle in meters

    pfitV : integer
        polynomial order for DC model

    minH : float
        minimum reflector height in meters

    returns 
    ----------
    maxF : float
        maximum Reflector height (meters)
    maxAmp : float
        amplitude of periodogram
    eminObs : float
        minimum observed elevation angle in degrees
    emaxObs : float
        maximum observed elevation angle in degrees
    riseSet : integer
        1 for rise and -1 for set
    px : numpy array
        periodogram, x-axis, RH, meters
    pz : numpy array
        periodogram, y-axis, volts/volts 
    """
    ofac,hifac = get_ofac_hifac(x,cf,maxH,desiredP)
#   min and max observed elevation angles
    eminObs = min(x); emaxObs = max(x)
    if x[0] > x[1]:
        riseSet = -1
    else:
        riseSet = 1

#   change so everything is rising, i.e. elevation angle is increasing
    ij = np.argsort(x)
    x = x[ij]
    y = y[ij]

    x = np.sin(x*np.pi/180)
#   polynomial fit done before

#   scale by wavelength
    x=x/cf
#    y=newy
#   get frequency spacing
    px = freq_out(x,ofac,hifac) 
#   compute spectrum using scipy
    scipy_LSP = spectral.lombscargle(x, y, 2*np.pi*px)

#   find biggest peak
#   scaling required to get amplitude spectrum
    pz = 2*np.sqrt(scipy_LSP/len(x))
#   now window
#    ij = np.argmax(px > minH)
#    new_px = px[ij]
    new_pz = pz[(px > minH)]
    new_px = px[(px > minH)]
    px = new_px
    pz = new_pz
#   find the max
#   was causing it to crash.  check that pz has anything in it
    if len(pz) == 0:
        print('invalid LSP, no data returned. If this is pervasive, check your inputs')
        maxF = 0; maxAmp = 0
    else:
        ij = np.argmax(pz)
        maxF = px[ij]
        maxAmp = np.max(pz)

    return maxF, maxAmp, eminObs, emaxObs,riseSet, px,pz

def window_data(s1,s2,s5,s6,s7,s8, sat,ele,azi,seconds,edot,f,az1,az2,e1,e2,satNu,pfitV,pele,screenstats):
    """

    also calculates the scale factor for various GNNS frequencies.  currently
    returns meanTime in UTC hours and mean azimuth in degrees
    cf, which is the wavelength/2
    currently works for GPS, GLONASS, GALILEO, and Beidou
    new: pele are the elevation angle limits for the polynomial fit. these are appplied
    before you start windowing the data

    Parameters
    -----------
    s1 : numpy array 
        SNR L1 data, floats
    s2 : numpy array 
        SNR L2 data, floats 
    s5 : numpy array
        SNR L5 data
    s6 : numpy array
        SNR L6 data
    s7 : numpy array
        SNR L7 data
    s8 : numpy array
        SNR L8 data
    sat : numpy array
        satellite number
    ele : numpy array
        elevation angle (Degrees)
    azi : numpy array
        azimuth angle (Degrees)
    seconds : numpy array
        seconds of the day (GPS time)
    edot : numpy array
    f : integer
        requested frequency
    az1 : float
        minimum azimuth limit, degrees
    az2 : float
        maximum azimuth limit, degrees
    e1 : float
        minimum elevation angle limit, degrees
    e2 : float
        maximum elevation angle limit, degrees
    satNu : integer
        requested satellite number
    pfitV : integer
        polynomial order for DC fit
    screenstats : boolean
        Whether statistics come to the screen

    Returns
    ---------
    x : numpy array of 
        float
    y : numpy array of 
        float
    Nvv : integer
        number of points in x
    cf : float
        scale factor
    meanTime : float
        UTC hour
    avgAzim : float
        average azimuth of the tracks
    outFact1 : float
        TBD
    outFact2 : float
        TBD
    delT : float
        track length in minutes (I think)

    """
    cunit = 1
    dat = []; x=[]; y=[]
#   get scale factor
#   added glonass, 101 and 102
    if (f == 1) or (f==101) or (f==201) or (f==301):
        dat = s1
    if (f == 2) or (f == 20) or (f == 102) or (f==302):
        dat = s2
    if (f == 5) or (f==205):
        dat = s5
#   these are galileo frequencies (via RINEX definition)
    if (f == 206) or (f == 306):
        dat = s6
    if (f == 207) or (f == 307):
        dat = s7
    if (f == 208):
        dat = s8
#   get the scaling factor for this frequency and satellite number
    cf = arc_scaleF(f,satNu)

#   if not, frequency does not exist, will be tripped by Nv
#   this does remove the direct signal component - but gets you ready to do that
    if (cf > 0):
        x,y,sat,azi,seconds,edot  = removeDC(dat, satNu, sat,ele, pele, azi,az1,az2,edot,seconds) 

#
    Nv = len(y); Nvv = 0 ; 
#   some defaults in case there are no data in this region
    meanTime = 0.0; avgAzim = 0.0; avgEdot = 1; Nvv = 0
    avgEdot_fit =1; delT = 0.0
#   no longer have to look for specific satellites. some minimum number of points required 
    #if screenstats:
    #    print('Starting Npts', Nv)
    if Nv > 30:
        model = np.polyfit(x,y,pfitV)
        fit = np.polyval(model,x)
#       redefine x and y as old variables
        ele = x
        dat = y - fit
#       ok - now figure out what is within the more restricted elevation angles
        x =   ele[(ele > e1) & (ele < e2) & (azi > az1) & (azi < az2)]
        y =   dat[(ele > e1) & (ele < e2) & (azi > az1) & (azi < az2)]
        ed = edot[(ele > e1) & (ele < e2) & (azi > az1) & (azi < az2)]
        a =   azi[(ele > e1) & (ele < e2) & (azi > az1) & (azi < az2)]
        t = seconds[(ele > e1) & (ele < e2) & (azi > az1) & (azi < az2)]
        ifound = 0
        if screenstats:
            print('Starting/Windowed Npts', Nv, len(x))
        if len(x) > 0:
            ijkl = np.argmax(x)
            if (ijkl == 0):
            #print('ok, at the beginning ')
                ifound = 1;
            elif (ijkl == len(x)-1):
            #print('ok, at the end')
                ifound = 2;
            else:
                ifound = 3;
                if screenstats:
                    iamok = True
                    #print('Rising Setting Arc ' %5.0f and peak %5.0f "% (len(x),ijkl) )
                    #print("Rising/Setting Arc, length: %5.0f eangles begin %6.2f end %6.2f peak %6.2f"% (len(x), x[0],x[-1], x[ijkl] ) )
                edif1 = x[ijkl] - x[0]
                edif2 = x[ijkl] - x[-1]
                if edif1 > edif2:
                    x = x[0:ijkl]; y = y[0:ijkl]; ed = ed[0:ijkl]
                    a = a[0:ijkl]; t = t[0:ijkl]
                else:
                    x = x[ijkl:-1]; y = y[ijkl:-1]; ed = ed[ijkl:-1]
                    a = a[ijkl:-1]; t = t[ijkl:-1]
                #if screenstats:
                     #print('length of the arc is now', len(x))
        sumval = np.sum(y)
        kristine = True
        if sumval == 0:
            x = []; y=[] ; Nv = 0 ; Nvv = 0
#   since units were changed to volts/volts, the zeros got changed to 1 values
        if sumval == Nv:
            x = []; y=[] ; Nv = 0 ; Nvv = 0
        Nvv = len(y)
#       calculate average time in UTC (actually it is GPS time) in hours and average azimuth
#       this is fairly arbitrary, but can't be so small you can't fit a polymial to it
        if (Nvv > 10):
            dd = np.diff(t)
#           edot, in radians/sec
            model = np.polyfit(t,x*np.pi/180,1)
#  edot in radians/second
            avgEdot_fit = model[0]
            avgAzim = np.mean(a)
            meanTime = np.mean(t)/3600
            avgEdot = np.mean(ed) 
#  delta Time in minutes
            delT = (np.max(t) - np.min(t))/60 
# average tan(elev)
            cunit =np.mean(np.tan(np.pi*x/180))
#           return tan(e)/edot, in units of one over (radians/hour) now. used for RHdot correction
#           so when multiplyed by RHdot - which would be meters/hours ===>>> you will get a meter correction
    if avgEdot == 0:
        outFact1 = 0
    else:
        outFact1 = cunit/(avgEdot*3600) 
    outFact2 = cunit/(avgEdot_fit*3600) 
    return x,y,Nvv,cf,meanTime,avgAzim,outFact1, outFact2, delT

def arc_scaleF(f,satNu):
    """
    calculates LSP scale factor cf 

    Parameters
    --------
    f : integer
        satellite frequency
    satNu : integer
        satellite number (1-400)

    Returns
    ----------
    cf : float
        wavelength/2 (meters)

    """ 
#   default value for w so that if someone inputs an illegal frequency, it does not crash
    w = 0
    if f == 1:
        w = constants.wL1
    if (f == 2) or (f == 20):
        w = constants.wL2
    if f == 5:
        w = constants.wL5
#   galileo satellites
#   must be a smarter way to do this
    if (f > 200) and (f < 210):
        if (f == 201):
            w = constants.wgL1
        if (f == 205):
            w = constants.wgL5
        if (f == 206):
            w = constants.wgL6
        if (f == 207):
            w = constants.wgL7
        if (f == 208):
            w = constants.wgL8
#
#   add beidou 18oct15
#  i am confused about this ...
    if (f > 300) and (f < 310):
        if (f == 301):
            w = constants.wbL1
        if (f == 302):
            w = constants.wbL2
        if (f == 306):
            w = constants.wbL6
        if (f == 307):
            w = constants.wbL7

#   glonass satellite frequencies
    if (f == 101) or (f == 102):
        w = glonass_channels(f,satNu) 
    cf = w/2
    return cf 

def freq_out(x,ofac,hifac):
    """

    Parameters
    ------------
    x : numpy array
        sine(elevation angle)
    ofac: float
        oversamping factor
    hifac : float
        how far to calculate RH frequencies  (in meters)

    Returns
    ------------
    pd: float numpy arrays
        frequencies 

    """
#
# number of points in input array
    n=len(x)
#
# number of frequencies that will be used
    nout=np.int(0.5*ofac*hifac*n)
	 
    xmax = np.max(x) 
    xmin = np.min(x) 
    xdif=xmax-xmin 
# starting frequency 
    pnow=1.0/(xdif*ofac) 
    pstart = pnow
    pstop = hifac*n/(2*xdif)
# 
# output arrays
#    px = np.zeros(nout)
#    for i in range(0,nout):
#        px[i]=pnow
#        pnow=pnow+1.0/(ofac*xdif)
# simpler way
    pd = np.linspace(pstart, pstop, nout)
    return pd

def find_satlist(f,snrExist):
    """
    DEPRECATED. DO NOT USE 

    Parameters
    ----------
    f : integer
        frequency 

    snrExist : boolean numpy array
        tells you if a signal is (potentially) legal

    satlist: list of integers
        satellites to use 

    """
# set list of GPS satellites for now
# 
# Block III will be 4, 18, 23, 
#   these are the only L2C satellites as of 18oct10
    #l2c_sat = [1, 3, 5, 6, 7, 8, 9, 10, 12, 15, 17, 24, 25, 26, 27, 29, 30, 31, 32]
    # updated on  march 26, 2021 - really should make this time dependent ....
    l2c_sat = [1, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 15, 17, 18, 23, 24, 25, 26, 27, 29, 30, 31, 32]

#   only L5 satellites thus far
    l5_sat = [1, 3,  4, 6,  8, 9, 10, 14, 18, 23, 24, 25, 26, 27, 30,  32]
    # l5_sat = [1, 3,  4, 6,  8, 9, 10, 24, 25, 26, 27, 30,  32]
#   assume l1 and l2 can be up to 32
    l1_sat = np.arange(1,33,1)
    satlist = []
    if f == 1:
        satlist = l1_sat
    if f == 20:
        satlist = l2c_sat
    if f == 2:
        satlist = l1_sat
    if f == 5:
        satlist = l5_sat
#   i do not think they have 26 - but ....
#   glonass L1
    if (f == 101) or (f==102):
# only have 24 frequencies defined
        satlist = np.arange(101,125,1)
#   galileo - 40 max?
#   use this to check for existence, mostly driven by whether there are 
#   extra columns (or if they are non-zero)
    gfs = int(f-200)

    if (f >  200) and (f < 210) and (snrExist[gfs]):
        satlist = np.arange(201,241,1)
#   galileo has no L2 frequency, so set that always to zero
    if f == 202:
        satlist = []
#   pretend there are 32 Beidou satellites for now
    if (f > 300):
        satlist = np.arange(301,333,1)

    # minimize screen output
    #if len(satlist) == 0:
    #    print('     illegal frequency: no sat list being returned')
    return satlist

def find_satlist_wdate(f,snrExist,year,doy):
    """
    find satellite list for a given frequency and date

    parameters
    -------------
    f : integer
        frequency

    snrExist : boolean numpy array
        tells you if a signal is (potentially) legal

    returns
    --------
    satlist: list of integers
        satellites to use

    june 24, 2021: updated for SVN78
    """
    # get list of relevant satellites
    l2c_sat, l5_sat = l2c_l5_list(year,doy)

    l1_sat = np.arange(1,33,1)
    satlist = []
    if f == 1:
        satlist = l1_sat
    if f == 20:
        satlist = l2c_sat
    if f == 2:
        satlist = l1_sat
    if f == 5:
        satlist = l5_sat
#   i do not think they have 26 - but ....
#   glonass L1
    if (f == 101) or (f==102):
# only have 24 frequencies defined
        satlist = np.arange(101,125,1)
#   galileo - 40 max?
#   use this to check for existence, mostly driven by whether there are
#   extra columns (or if they are non-zero)
    gfs = int(f-200)

    if (f >  200) and (f < 210) and (snrExist[gfs]):
        satlist = np.arange(201,241,1)
#   galileo has no L2 frequency, so set that always to zero
    if f == 202:
        satlist = []
#   pretend there are 32 Beidou satellites for now
    if (f > 300):
        satlist = np.arange(301,333,1)

    # minimize screen output
    #if len(satlist) == 0:
    #    print('     illegal frequency: no sat list being returned')
    return satlist



def glonass_channels(f,prn):
    """
    inputs frequency and prn number
    returns wavelength for glonass satellite in meters
    logic from Simon Williams, matlab
    converted to function by KL, 2017 November
    converted to python by KL 2018 September
    """
#   we define glonass by adding 100.  remove this for definition of the wavelength
    if (prn > 100):
        prn = prn - 100
    lightSpeed = 299792458
    slot = [14,15,10,20,19,13,12,1,6,5,22,23,24,16,4,8,3,7,2,18,21,9,17,11]
    channel = [-7,0,-7,2,3,-2,-1,1,-4,1,-3,3,2,-1,6,6,5,5,-4,-3,4,-2,4,0]
    slot = np.matrix(slot)
    channel = np.matrix(channel)
#   main frequencies
    L1 = 1602e6
    L2 = 1246e6
#   deltas
    dL1 = 0.5625e6
    dL2 = 0.4375e6

    ch = channel[(slot == prn)]
    ch = int(ch)
#   wavelengths in meters
#    print(prn,ch,f)
    l = 0.0
    if (f == 101):
        l = lightSpeed/(L1 + ch*dL1)
    if (f == 102):
        l = lightSpeed/(L2 + ch*dL2)
    return l
def open_outputfile(station,year,doy,extension):
    """
    inputs: station name, year, doy, and station name
    opens output file in REFL_CODE/year/results/station directory
    return fileID
    if the results directory does not exist, it tries to make it. i think
    june 2019, added snrending to output name
    july 2020, no longer open frej file
    """
    if os.path.isdir('logs'):
        skippingxist = True
        #print('log directory exists')
    else:
        #print('making log directory ')
        subprocess.call(['mkdir', 'logs'])
    fout = 0
#   primary reflector height output goes to this directory
    xdir = os.environ['REFL_CODE']
    cdoy = '{:03d}'.format(doy)
#   extra file with rejected arcs
    w = 'logs/reject.' + str(year) + '_' + cdoy  + station + '.txt'
#    print('open output file for rejected arcs',w)
    #frej=open(w,'w+')
#    frej=open('reject.txt','w+')
#   put a header in the file
#    frej.write("%year, doy, maxF,sat,UTCtime, Azim, Amp,  eminO, emaxO,  Nv,freq,rise,Edot, PkNoise,  DelT,   MJD \n")
    filedir = xdir + '/' + str(year)  + '/results/' + station 
#    filepath1 =  filedir + '/' + cdoy  + '.txt'
#   changed to a function
    filepath1,fexit = LSPresult_name(station,year,doy,extension)
    #print('Output will go to:', filepath1)
    try:
        fout=open(filepath1,'w+')
#       put a header in the output file
        fout.write("% gnssrefl, https://github.com/kristinemlarson \n")
        fout.write("% Phase Center corrections have NOT been applied \n")
        fout.write("% year, doy, RH, sat,UTCtime, Azim, Amp,  eminO, emaxO,NumbOf,freq,rise,EdotF, PkNoise  DelT     MJD   refr-appl\n")
        fout.write("% (1)  (2)   (3) (4)  (5)     (6)   (7)    (8)    (9)   (10)  (11) (12) (13)    (14)     (15)    (16)   (17)\n")
        fout.write("%             m        hrs    deg   v/v    deg    deg  values            hrs               min         1 is yes  \n")
    except:
        print('problem on first attempt - so try making results directory')
        f1 = xdir + '/' + str(year) + '/results/'
        subprocess.call(['mkdir',f1])
        # os.system(cm)
        f2 = xdir + '/' + str(year) + '/results/' + station
        subprocess.call(['mkdir',f2])
        # os.system(cm)
        try:
            fout=open(filepath1,'w+')
            print('successful open')
        except:
            print('problems opening the file')
            sys.exit()
    frej = 100
    return fout, frej

def removeDC(dat,satNu, sat,ele, pele, azi,az1,az2,edot,seconds):
    """
#   remove direct signal using given elevation angle (pele) and azimuth 
    (az1,az2) constraints, return x,y as primary used data and windowed
    azimuth, time, and edot
#   removed zero points, which 10^0 have value 1.  used 5 to be sure?
    """
    p1 = pele[0]; p2 = pele[1]
#   look for data within these azimuth and elevation angle constraints
    x = ele[(sat == satNu) & (ele > p1) & (ele < p2) & (azi > az1) & (azi < az2) & (dat > 5)]
    y = dat[(sat == satNu) & (ele > p1) & (ele < p2) & (azi > az1) & (azi < az2) & (dat > 5)]
    edot = edot[(sat == satNu) & (ele > p1) & (ele < p2) & (azi > az1) & (azi < az2) & (dat > 5)]
    seconds = seconds[(sat == satNu) & (ele > p1) & (ele < p2) & (azi > az1) & (azi < az2) & (dat > 5)]
    azi = azi[(sat == satNu) & (ele > p1) & (ele < p2) & (azi > az1) & (azi < az2) & (dat > 5)]

    return x,y,sat,azi,seconds,edot

def quick_plot(plt_screen, gj,station,pltname,f):
    """
    inputs plt_screen variable (1 means go ahead) and integer variable gj
    which if > 0 there is something to plot
    also station name for the title
    pltname is png filename, if requested
    """
    if (plt_screen == 1  and gj > 0):
        plt.subplot(212)
        plt.xlabel('Reflector height(m)')
        plt.ylabel('SNR Spectral Amplitude')
        plt.subplot(211)
        plt.title('Station:' + station + '/freq:' + str(f))
        plt.ylabel('SNR (volts/volts)')
        plt.xlabel('elevation angle(degrees)')
        if pltname != 'None':
            plt.savefig(pltname)
        else:
            print('plot file not saved ')
        plt.show()

def print_file_stats(ele,sat,s1,s2,s5,s6,s7,s8,e1,e2):
    """
    inputs 

    ele

    sat

    s1 

    s2 

    """
    gps = ele[(sat > 0) & (sat < 33) & (ele < e2) ]
    glonass = ele[(sat > 100) & (sat < 125) & (ele < e2) ]
    beidou = ele[(sat > 300) & (sat < 340) & (ele < e2) ]
    galileo = ele[(sat > 200) & (sat < 240) & (ele < e2) ]
    print('GPS     obs ', len(gps) )
    print('Glonass obs ', len(glonass))
    print('Galileo obs ', len(galileo))
    print('Beidou  obs ', len(beidou))

    return



def diffraction_correction(el_deg, temp=20.0, press=1013.25):
    """ Computes and return the elevation correction for refraction in the atmosphere.

    Computes and return the elevation correction for refraction in the atmosphere such that the elevation of the
    satellite plus the correction is the observed angle of incidence.

    Based on an empirical model by G.G. Bennet.
    This code was provided by Chalmers Group, Joakim Strandberg and Thomas Hobiger

    Parameters
    ----------
    el_deg : array_like
        A vector of true satellite elevations in degrees for which the correction is calculated.

    temp : float, optional
        Air temperature at ground level in degrees celsius, default 20 C.

    press : float, optional
        Air pressure at ground level in hPa, default 1013.25 hPa.

    Returns
    -------
    corr_el_deg : 1d-array
        The elevation correction in degrees.

    References:
    ----------
        Bennett, G. G. 'The calculation of astronomical refraction in marine navigation.'
        Journal of Navigation 35.02 (1982): 255-259.
    """
    el_deg = np.array(el_deg)

    corr_el_arc_min = 510/(9/5*temp + 492) * press/1010.16 * 1/np.tan(np.deg2rad(el_deg + 7.31/(el_deg + 4.4)))

    corr_el_deg = corr_el_arc_min/60

    return corr_el_deg


def fdoy2mjd(year,fdoy):
    """
    input year and fractional doy??
    returns MJD - maybe?
    """
    doy = math.floor(fdoy)
    yy,mm,dd, cyyyy, cdoy, YMD = ydoy2useful(year,doy)
    fract_hour = 24*(fdoy - doy)

    mjd = getMJD(year,mm,dd,fract_hour)

    return mjd



def mjd(y,m,d,hour,minute,second):
    """
    inputs: year, month, day, hour, minute,second
    output: modified julian day
    using information from http://infohost.nmt.edu/~shipman/soft/sidereal/ims/web/MJD-fromDatetime.html
    """
    if  (m <= 2):
        y, m = y-1, m+12
    if ((y, m, d) >= (1582, 10, 15)):
        A = int(y / 100)
        B = 2 - A + int(A / 4)
    else:
        B = 0
    C = int(365.25 * y)
    D = int(30.6001 *(m + 1))
    mjd = B + C + D + d - 679006
#   calculate seconds
    s = hour*3600 + minute*60 + second
    fracDay = s/86400
    return mjd, fracDay


def doy2ymd(year, doy):
    """
    inputs: year and day of year (doy)
    returns: some kind of datetime construct which can be used to get MM and DD
    """

    d = datetime.datetime(year, 1, 1) + datetime.timedelta(days=(doy-1))
    #print('ymd',d)
    return d 

def getMJD(year,month,day,fract_hour):
    """
    inputs are year, month, day and fractional hour
    return is modified julian day (real8)
    """
#   convert fract_hour to HH MM SS
#   ignore fractional seconds for now
    hours = math.floor(fract_hour) 
    leftover = fract_hour - hours
    minutes = math.floor(leftover*60)
    seconds = math.floor(leftover*3600 - minutes*60)
#    print(fract_hour, hours, minutes, seconds)
    MJD, fracS = mjd(year,month,day,hours,minutes,seconds)
    MJD = MJD + fracS
    return MJD

def update_plot(plt_screen,x,y,px,pz):
    """
    input plt_screen integer value from gnssIR_lomb.
    (value of one means update the SNR and LSP plot)
    and values of the SNR data (x,y) and LSP (px,pz)
    """
    if (plt_screen == 1):
        plt.subplot(211)  
        plt.plot(x,y)
        #plt.title(station)
        plt.subplot(212)  
        plt.plot(px,pz)
def open_plot(plt_screen):
    """
    simple code to open a figure, called by gnssIR_lomb
    """
    if (plt_screen == 1):
        plt.figure()


def store_orbitfile(filename,year,orbtype):
    """
    the function moves the file into the appropriate directory

    inputs:

    orbit filename 

    year : integer 

    orbtype : string 
        (nav or sp3)


    """
    # parent directory of the orbits for that year
    xdir = os.environ['ORBITS'] + '/' + str(year)
    # check that directories exist
    if not os.path.isdir(xdir): #if year folder doesn't exist, make it
        os.makedirs(xdir)
    xdir = os.environ['ORBITS'] + '/' + str(year) + '/' + orbtype
    if not os.path.isdir(xdir): #if year folder doesn't exist, make it
        os.makedirs(xdir)
    if (os.path.isfile(filename) == True):
        #print('moving ', filename, ' to ', xdir)
        status = subprocess.call(['mv','-f', filename, xdir])
    else:
        print('The orbit file did not exist, so it was not stored')
    return xdir

def make_snrdir(year,station):
    """
    given a year and station name, it makes various directories needed
    for SNR file/analysis outputs
    """
    xdir = os.environ['REFL_CODE'] + '/' + str(year)
    # check that directories exist
    if not os.path.isdir(xdir): #if year folder doesn't exist, make it
        os.makedirs(xdir)
    xdir = xdir + '/snr'
    if not os.path.isdir(xdir): #if year folder doesn't exist, make it
        os.makedirs(xdir)
    xdir = xdir + '/' + station 
    if not os.path.isdir(xdir): #if year folder doesn't exist, make it
        os.makedirs(xdir)

def store_snrfile(filename,year,station):
    """
    simple code to move an snr file to the right place 
    inputs are the filename, the year, and the station name
    """
    xdir = os.environ['REFL_CODE'] + '/' + str(year)
    # check that directories exist
    if not os.path.isdir(xdir): #if year folder doesn't exist, make it
        os.makedirs(xdir)
    xdir = xdir + '/snr'
    if not os.path.isdir(xdir): #if year folder doesn't exist, make it
        os.makedirs(xdir)
    xdir = xdir + '/' + station 
    if not os.path.isdir(xdir): #if year folder doesn't exist, make it
        os.makedirs(xdir)
    if (os.path.isfile(filename) == True):
        status = subprocess.call(['mv','-f', filename, xdir])
    else:
        print('the SNR file does not exist, so nothing was moved')

def rinex_name(station, year, month, day):
    """
    given station (4 char), year, month, day, return rinexfile name
    and the hatanaka equivalent
    """
    if day == 0:
        doy = month
        cyyyy, cyy, cdoy = ydoych(year,doy)
    else:
        doy,cdoy,cyyyy,cyy = ymd2doy(year,month,day)

    fnameo = station + cdoy + '0.' + cyy + 'o'
    fnamed = station + cdoy + '0.' + cyy + 'd'
    return fnameo, fnamed

def snr_name(station, year, month, day,option):
    """
    parameters
    --------
    station : string

    year : integer

    month : integer

    day : integer

    option : integer
        snr filename delimeter

    returns
    -----------
    fname : string
        snr filename 
    """
    doy,cdoy,cyyy,cyy = ymd2doy(year,month,day)

    fname = station + cdoy + '0.' + cyy + '.snr' + str(option)

    return fname

def nav_name(year, month, day):
    """
    returns the name and location of the navigation file

    parameters
    -------------
    year : integer

    month : integer

    day : integer

    returns
    ----------
    navfilename : string
        name of the navigation file

    navfiledir : string
        local directory where navigation file will be stored
    """
    if (day == 0):
        cyyyy, cyy, cdoy = ydoych(year,doy)
    else:
        doy,cdoy,cyyyy,cyy = ymd2doy(year,month,day)
    navfilename = 'auto'  + cdoy + '0.' + cyy  +  'n'
    navfiledir = os.environ['ORBITS'] + '/' + cyyyy + '/nav'
    return navfilename,navfiledir

def sp3_name(year,month,day,pCtr):
    """
    inputs are year month and day and processing center
    returns sp3 file name and directory
    """
    name,clkn=igsname(year,month,day)
    gps_week = name[3:7]
    sp3name = pCtr + name[3:8] + '.sp3'
    sp3dir = os.environ['ORBITS'] + '/' + str(year) + '/sp3'
    return sp3name, sp3dir


def rinex_unavco_highrate(station, year, month, day):
    """
    picks up a RINEX file from unavco.  it tries to pick up an o file,
    but if it does not work, it tries the "d" version, which must be
    decompressed.  the location of this executable is defined in the crnxpath
    variable. This is from the main unavco directory - not the highrate directory.

    WARNING: only rinex version 2 in this world
    21sep02 - update from ftp to https, also added doy work around
    """
    crnxpath = hatanaka_version()
    # added this for people that submit doy instead of month and day
    if day == 0:
        doy = month
        cyyyy = str(year)
        cdoy = '{:03d}'.format(doy)
        cyy = '{:02d}'.format(year-2020)
    else:
        doy,cdoy,cyyyy,cyy = ymd2doy(year,month,day)
    rinexfile,rinexfiled = rinex_name(station, year, month, day)
    unavco= 'https://data.unavco.org/archive/gnss/highrate/1-Hz/rinex/'

    filename1 = rinexfile + '.Z'
    filename2 = rinexfiled + '.Z'
    url1 = unavco+  cyyyy + '/' + cdoy + '/' + station + '/' + filename1
    url2 = unavco+  cyyyy + '/' + cdoy + '/' + station + '/' + filename2

    # hatanaka executable has to exist
    s1 = time.time()
    if os.path.isfile(crnxpath): 
        try:
            wget.download(url2,filename2)
            subprocess.call(['uncompress',filename2])
            subprocess.call([crnxpath, rinexfiled])
            subprocess.call(['rm','-f',rinexfiled])
        except:
            okok = 1
    if not os.path.isfile(rinexfile):
        print('Did not find Hatanaka. Try for obs file')
        try:
            wget.download(url1,filename1)
            subprocess.call(['uncompress',filename1])
        except:
            okok = 1
    s2 = time.time()
    print('That took ', int(s2-s1), ' seconds.')


def new_big_Disk_in_DC(station, year, month, day):
    """
    21aug28 uses https instead of ftp

    picks up gzip o file 
    removed Z option and now only use gz with d file
    """
    # get the proper path/name of the hatanaka code
    crnxpath = hatanaka_version()
    if day == 0:
        doy = month
        year, month, day, cyyyy,cdoy, YMD = ydoy2useful(year,doy)
        cyy = cyyyy[2:4]
    else:
        doy,cdoy,cyyyy,cyy = ymd2doy(year,month,day)
    rinexfile,rinexfiled = rinex_name(station, year, month, day)
    # as i understand it this file type has gone away
    comp_rinexfiled = rinexfiled + '.Z'
    gzip_rinexfile = rinexfile + '.gz'
    # added 21aug30
    gzip_rinexfiled = rinexfiled + '.gz'
    #mainadd = 'ftp://www.ngs.noaa.gov/cors/rinex/'
    # KL updated august 28, 2021
    mainadd = 'https://geodesy.noaa.gov/corsdata/rinex/'
    url = mainadd + str(year) + '/' + cdoy+ '/' + station + '/' + gzip_rinexfile 
    try:
        wget.download(url, out=gzip_rinexfile)
        status = subprocess.call(['gunzip', gzip_rinexfile])
    except:
        okok = 1

    if os.path.isfile(rinexfile):
        okok = 1
        #print('found it')
    else:
        print('Look for hatanaka file with gzip')
        try:
            url = mainadd + str(year) + '/' + cdoy+ '/' + station + '/' + gzip_rinexfiled 
            wget.download(url, out=gzip_rinexfiled)
            subprocess.call(['gunzip',gzip_rinexfiled])
            # un hatanaka
            subprocess.call([crnxpath, rinexfiled])
            # remove d file
            subprocess.call(['rm','-f',rinexfiled])
        except:
            okok = 1

def big_Disk_in_DC(station, year, month, day):
    """
    picks up a RINEX file from CORS.  
    changed it to pick up gzip o file instead of d file.  Not sure why they have 
    both but the d file appears to be 30 sec, and that I do not want
    allow doy to be sent to code in the month spot.  set day to zero
    """
    # get the proper path/name of the hatanaka code
    crnxpath = hatanaka_version()
    if day == 0:
        doy = month
        year, month, day, cyyyy,cdoy, YMD = ydoy2useful(year,doy)
        cyy = cyyyy[2:4]
    else:
        doy,cdoy,cyyyy,cyy = ymd2doy(year,month,day)
    rinexfile,rinexfiled = rinex_name(station, year, month, day)
    comp_rinexfiled = rinexfiled + '.Z'
    gzip_rinexfile = rinexfile + '.gz'
    mainadd = 'ftp://www.ngs.noaa.gov/cors/rinex/'
    #url = mainadd + str(year) + '/' + cdoy+ '/' + station + '/' + comp_rinexfiled 
    url = mainadd + str(year) + '/' + cdoy+ '/' + station + '/' + gzip_rinexfile 
    try:
        wget.download(url, out=gzip_rinexfile)
        status = subprocess.call(['gunzip', gzip_rinexfile])
    except:
        okok = 1

    if os.path.isfile(rinexfile):
        print('found it')
    else:
        print('try hatanaka')
        try:
            url = mainadd + str(year) + '/' + cdoy+ '/' + station + '/' + comp_rinexfiled 
            wget.download(url, out=comp_rinexfiled)
            subprocess.call(['uncompress',comp_rinexfiled])
            #subprocess.call([crnxpath,comp_rinexfiled])
            # get rid of d file
            #subprocess.call(['rm',comp_rinexfiled])
        except:
            okok = 1

def ydoy2ymd(year, doy):
    """
    inputs: year and day of year (doy)
    returns: year, month, day
    """

    d = datetime.datetime(year, 1, 1) + datetime.timedelta(days=(doy-1))
    month = int(d.month)
    day = int(d.day)
    return year, month, day

def rewrite_UNR_highrate(fname,station,year,doy):
    """
    takes a filename from was already retrieved? from 
    UNReno, reads it, rewrites as all numbers for other uses.
    no header, but year, month, day, day of year, seconds vertical, east, north
    the latter three are in meters
    stores in $REFL_CODE/yyyy/pos/station
    """
# make sure the various output directories  are there
    xdir = os.environ['REFL_CODE'] 
    dir1 = xdir + '/' + str(year)
    if not os.path.isdir(dir1):
        status = subprocess.call(['mkdir', dir1])

    dir1 = xdir + '/' + str(year) + '/' + 'pos'
    if not os.path.isdir(dir1):
        status = subprocess.call(['mkdir', dir1])

    dir1 = xdir + '/' + str(year) + '/' + 'pos' + '/' + station
#   make filename for the output
    yy,mm,dd, cyyyy, cdoy, YMD = ydoy2useful(year,doy)
    outputfile = dir1 + '/' + cdoy + '_hr.txt'
    print('file will go to: ' , outputfile)
    if not os.path.isdir(dir1):
        print('use subprocess to make directory')
        status = subprocess.call(['mkdir', dir1])
    try:
        x=np.genfromtxt(fname, skip_header=1, usecols = (3, 4, 5, 6, 7, 8, 9, 10))
        N = len(x)
        print('open outputfile',outputfile)
        f=open(outputfile,'w+')
        for i in range(0,N):
            f.write(" {0:4.0f} {1:2.0f} {2:2.0f} {3:3.0f} {4:7.0f} {5:9.4f} {6:9.4f} {7:9.4f} \n".format(x[i,0], x[i,1],x[i,2],x[i,3], x[i,4],x[i,5],x[i,6],x[i,7]))
        print('delete the original Blewitt file')
        subprocess.call(['rm','-f', fname])
        f.close()
    except:
        print('problem with accessing the file')

def month_converter(month):
    """
    brendan gave this to me - give it a 3 char month, returns integer
    """
    months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
    return months.index(month) + 1

def char_month_converter(month):
    """
    integer month to 3 character month
    """
    months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
    return months[(month-1)]

def UNR_highrate(station,year,doy):
    """
    picks up the 5 minute time series from UNR website for a given station

    parameters
    -----------
    station : string
        4 character station name

    year : integer

    doy : integer

    returns
    -----------
    filename : string
        output filename

    goodDownload : boolean
        whether you were successful

    """
    yy,mm,dd, cyyyy, cdoy, YMD = ydoy2useful(year,doy)
    stationUP = station.upper()
    dirdir = 'ftp://gneiss.nbmg.unr.edu/rapids_5min/kenv/' + cyyyy + '/' + cdoy + '/'
    filename = YMD + station.upper() + '_fix.kenv'
    url = dirdir + filename
    if (os.path.isfile(filename) == True):
        print('file already exists')
        goodDownload = True
    else:
        try:
            wget.download(url,filename)
            goodDownload = True
        except:
            print(url)
            print('could not get the highrate file from UNR')
            goodDownload = False
    return filename, goodDownload

def mjd_to_date(jd):
    """
    https://gist.github.com/jiffyclub/1294443

    Converts Modified Julian Day to y,m,d
    
    Algorithm from 'Practical Astronomy with your Calculator or Spreadsheet', 
        4th ed., Duffet-Smith and Zwart, 2011.
    
    Parameters
    ----------
    jd : float
        Julian Day
        
    Returns
    -------
    year : int
        Year as integer. Years preceding 1 A.D. should be 0 or negative.
        The year before 1 A.D. is 0, 10 B.C. is year -9.
        
    month : int
        Month as integer, Jan = 1, Feb. = 2, etc.
    
    day : float
        Day, may contain fractional part.
        
    
    """
   # first step is to change MJD to jd, since original code expected it 
    jd = jd + 2400000.5
    # start of the original code
    jd = jd + 0.5
    
    F, I = math.modf(jd)
    I = int(I)
    
    A = math.trunc((I - 1867216.25)/36524.25)
    
    if I > 2299160:
        B = I + 1 + A - math.trunc(A / 4.)
    else:
        B = I
        
    C = B + 1524
    
    D = math.trunc((C - 122.1) / 365.25)
    
    E = math.trunc(365.25 * D)
    
    G = math.trunc((C - E) / 30.6001)
    
    day = C - E + F - math.trunc(30.6001 * G)
    
    if G < 13.5:
        month = G - 1
    else:
        month = G - 13
        
    if month > 2.5:
        year = D - 4716
    else:
        year = D - 4715
        
    day = int(day)
    return year, month, day

def getseries(site):
    """
    originally from brendan crowell.
    picks up two UNR time series - stores in subdirectory called tseries 
    input is station name (four character, lower case)
    """
    # i changed this to download ENV instead of XYZ (or both?)
    #if tseries folder doesn't exist, make it
    if not os.path.exists('tseries'): 
        os.makedirs('tseries')
    # change station to uppercase
    siteid = site.upper()
    # why still ITRF 2008?
    fname = 'tseries/' + siteid + '.IGS08.tenv3'
    # NA12 env time series
    fname2 = 'tseries/' + siteid + '.NA12.tenv3'
    # NA12 env rapid time series
    fname3 = 'tseries/' + siteid + '.NA12.rapid.tenv3'

    if (os.path.isfile(fname) ):
        print ('Timeseries file ' + fname + ' already exists')
    else:
        url = 'http://geodesy.unr.edu/gps_timeseries/tenv3/IGS08/' + siteid + '.IGS08.tenv3'
        wget.download(url, out='tseries/')
#
    if (os.path.isfile(fname2)):
        print ('Timeseries file ' + fname2 + ' already exists')
    else:
        url = 'http://geodesy.unr.edu/gps_timeseries/tenv3/NA12/' + siteid + '.NA12.tenv3'
        wget.download(url, out='tseries/')

    if (os.path.isfile(fname3)):
        print ('Timeseries file ' + fname3 + ' already exists')
    else:
        url = 'http://geodesy.unr.edu/gps_timeseries/rapids/tenv3/NA12/' + siteid + '.NA12.tenv3'
        wget.download(url, out=fname3)

def rewrite_tseries(station):
    """
    given a station name, look at a daily blewitt position (ENV) 
    file and write a new file that is more human friendly

    parameters
    -----------
    station : string
        4 character station name
    """
    siteid = station.upper()
    # NA12 env time series
    fname = 'tseries/' + siteid + '.NA12.tenv3'
    fname_rapid = 'tseries/' + siteid + '.NA12.rapid.tenv3'
    outputfile = 'tseries/' + station+ '_na12.env'
    print(fname,outputfile)
    try:
        x=np.genfromtxt(fname, skip_header=1, usecols = (3, 7, 8, 9, 10, 11, 12,13))
        N = len(x)
        print(N,'open outputfile',outputfile)
        f=open(outputfile,'w+')
        for i in range(0,N):
            mjd = x[i,0]
            yy,mm,dd = mjd_to_date(mjd) 
            doy, cdoy, cyyyy, cyy = ymd2doy(yy,mm,dd)
            east = x[i,1] + x[i,2]
            north= x[i,3] + x[i,4]
            # adding in the antenna
            vert = x[i,5] + x[i,6] +  x[i,7]
            f.write(" {0:4.0f} {1:2.0f} {2:2.0f} {3:3.0f} {4:13.4f} {5:13.4f} {6:13.4f} \n".format(yy,mm,dd,doy,east,north,vert))
        f.close()
    except:
        print('some problem writing the new output file')

def rewrite_tseries_igs(station):
    """
    given a station name, look at a daily blewitt position (ENV)
    file and write a new file that is less insane to understand
    """
    siteid = station.upper()
    # NA12 env time series
    fname = 'tseries/' + siteid + '.IGS08.tenv3'
    outputfile = 'tseries/' + station + '_igs08.env'
    print(fname,outputfile)
    try:
        x=np.genfromtxt(fname, skip_header=1, usecols = (3, 7, 8, 9, 10, 11, 12,13))
        N = len(x)
        print(N)
        print(N,'open outputfile',outputfile)
        f=open(outputfile,'w+')
        for i in range(0,N):
            mjd = x[i,0]
            yy,mm,dd = mjd_to_date(mjd)
            doy, cdoy, cyyyy, cyy = ymd2doy(yy,mm,dd)
            east = x[i,1] + x[i,2]
            north= x[i,3] + x[i,4]
            # adding in the antenna
            vert = x[i,5] + x[i,6] +  x[i,7]
            f.write(" {0:4.0f} {1:2.0f} {2:2.0f} {3:3.0f} {4:13.4f} {5:13.4f} {6:13.4f} \n".format(yy,mm,dd,doy,east,north,vert))
        f.close()
    except:
        print('some problem writing the output')


def llh2xyz(lat,lon,height):
    """
    inputs lat,lon (in degrees) and ellipsoidal height (in meters)
    returns Cartesian values in meters.

    parameters
    -----------
    lat : float
        latitude in degrees

    lon : float
        longitude in degrees

    height : float
        ellipsoidal height in meters

    returns
    ---------
    x : float

    y : float

    z : float

    Ref: Decker, B. L., World Geodetic System 1984,
    Defense Mapping Agency Aerospace Center.
    modified from matlab version kindly provided by CCAR
    """
    A_EARTH = 6378137;
    f= 1/298.257223563;
    NAV_E2 = (2-f)*f; # also e^2
    deg2rad = math.pi/180.0
    if ((lat+lon+height) == 0):
        print('You have entered all zero values')
        x=0; y=0; z=0
    else:
        slat = math.sin(lat*deg2rad);
        clat = math.cos(lat*deg2rad);
        r_n = A_EARTH/(math.sqrt(1 - NAV_E2*slat*slat))
        x= (r_n + height)*clat*math.cos(lon*deg2rad)
        y= (r_n + height)*clat*math.sin(lon*deg2rad)
        z= (r_n*(1 - NAV_E2) + height)*slat

    return x, y, z

def LSPresult_name(station,year,doy,extension):
    """
    given station name, year, doy, and extension
    returns the location of the LSP result
    also returns boolean if it already exists (so that
    information can be used)
    extension is now used
    """
    # for testing
    xdir = os.environ['REFL_CODE']
    cyear = str(year)
    cdoy = '{:03d}'.format(doy)
    # this is default location where the results will go
    filedir = xdir + '/' + cyear  + '/results/' + station
    # this is now also done in the result_directories function,
    # but I guess no harm is done
    if not os.path.isdir(filedir):
        #print('making new results bdirectory ')
        subprocess.call(['mkdir', filedir])
    filedirx = filedir + '/' + extension
    # this is what you do if there is an extension
    if not os.path.isdir(filedirx):
        #print('making new results subdirectory ')
        subprocess.call(['mkdir', filedirx])

    filepath1 =  filedirx + '/' + cdoy  + '.txt'

    #print('output for this date will go to:', filepath1)
    if os.path.isfile(filepath1):
        #print('A result file already exists')
        fileexists = True
    else:
        #print('A result file does not exist')
        fileexists = False
    return filepath1, fileexists

def result_directories(station,year,extension):
    """
    inputs station, year, and extension
    makes output directories for results

    """
    xdir = os.environ['REFL_CODE']
    cyear = str(year)

    f1 = xdir + '/' + cyear
    if not os.path.isdir(f1):
        subprocess.call(['mkdir',f1])

    f1 = f1 + '/results'
    if not os.path.isdir(f1):
        subprocess.call(['mkdir',f1])


    f1 = f1 + '/' + station
    if not os.path.isdir(f1):
        subprocess.call(['mkdir',f1])

    if (extension != ''):
        f1 = f1 + '/' + extension
        if not os.path.isdir(f1):
            subprocess.call(['mkdir',f1])
    #else:
        #print('no extension')

    f1 = xdir + '/' + cyear + '/phase'
    if not os.path.isdir(f1):
        subprocess.call(['mkdir',f1])

    f1 = f1 + '/' + station
    if not os.path.isdir(f1):
        subprocess.call(['mkdir',f1])

def write_QC_fails(delT,delTmax,eminObs,emaxObs,e1,e2,ediff,maxAmp, Noise,PkNoise,reqamp,tooclose2edge):
    """
    prints out various QC fails to the screen

    """
    if tooclose2edge:
        print('     Retrieved reflector height too close to the edge of the RH space')

    if delT > delTmax:
        print('     Obs delT {0:.1f} minutes vs {1:.1f} requested limit '.format(delT,delTmax ))
    if eminObs  > (e1 + ediff):
        print('     Obs emin {0:.1f} is higher than {1:.1f} +- {2:.1f} degrees '.format(eminObs, e1, ediff ))
    if emaxObs  < (e2 - ediff):
        print('     Obs emax {0:.1f} is lower than {1:.1f} +- {2:.1f} degrees'.format(emaxObs, e2, ediff ))
    if maxAmp < reqamp:
        print('     Obs Ampl {0:.1f} vs {1:.1f} required '.format(maxAmp,reqamp  ))
    if maxAmp/Noise < PkNoise:
        print('     Obs PkN  {0:.1f} vs {1:.1f} required'.format(maxAmp/Noise, PkNoise ))
        
def define_quick_filename(station,year,doy,snr):
    """
    given station name, year, doy, snr type
    returns snr filename but without default directory structure
    19mar25: return compressed filename too
    """
    cyyyy, cyy, cdoy = ydoych(year,doy)
    f= station + str(cdoy) + '0.' + cyy + '.snr' + str(snr)
    return f

def update_quick_plot(station, f):
    """
    input plt_screen integer value from gnssIR_lomb.
    (value of one means update the SNR and LSP plot)
    and values of the SNR data (x,y) and LSP (px,pz)
    """
    plt.subplot(212)
    plt.xlabel('reflector height (m)'); plt.title('SNR periodogram')
    plt.subplot(211)
    plt.xlabel('elev Angles (deg)')
    #ftitle(freq)
    plt.title(station + ' SNR Data/' + ftitle(f) + ' Frequency') 

    return True

def navfile_retrieve(navfile,cyyyy,cyy,cdoy):
    """
    retrieves navfile from either SOPAC or CDDIS

    parameters 
    ----------
    navfile : string
        name of the broadcast orbit file
    cyyyy :  string
        4 character yaer
    cyy : string
        2 character year
    cdoy : string
        3 character day of year

    returns
    -----------
    FileExists : boolean
        whether the file was found

    """
    navname = navfile
    FileExists = False
    get_sopac_navfile(navfile,cyyyy,cyy,cdoy) 
    
    cddis_is_failing = True
    cddis_is_failing = False
    if not os.path.isfile(navfile) :
        if not cddis_is_failing:
            print('SOPAC download did not work, so will try CDDIS')
            get_cddis_navfile(navfile,cyyyy,cyy,cdoy) 
        else:
            print('CDDIS is unreliable and is being blocked by us')
    else:
        print('found nav file at SOPAC')

    if os.path.isfile(navfile):
        FileExists = True
    else:
        FileExists = False

    return FileExists

def make_nav_dirs(yyyy):
    """
    input year and it makes sure output directories are created for orbits
    """
    n = os.environ['ORBITS']
    # if parent nav dir does not exist, exit
    if not os.path.isdir(n):
        print('You have not defined ORBITS environment variable properly. Exiting')
        print(n)
        sys.exit()
    cyyyy = '{:04d}'.format(yyyy)
    navfiledir = os.environ['ORBITS'] + '/' + cyyyy 
    if not os.path.exists(navfiledir):
        subprocess.call(['mkdir',navfiledir])
        #print('making year directory')
    navfiledir1 = os.environ['ORBITS'] + '/' + cyyyy + '/nav' 
    if not os.path.exists(navfiledir1):
        subprocess.call(['mkdir',navfiledir1])
        #print('making nav specific directory')
    navfiledir2 = os.environ['ORBITS'] + '/' + cyyyy + '/sp3'
    if not os.path.exists(navfiledir2):
        #print('making sp3 specific directory')
        subprocess.call(['mkdir',navfiledir2])

    return True


def check_inputs(station,year,doy,snr_type):
    """
    inputs to Lomb Scargle and Rinex translation codes
    are checked for sensibility. Returns true or false to 
    code can exit. Error messages sent to the screen
    2019sep22
    """
    exitSys = False
    if len(station) != 4:
        print('Station name must be four characters. Exiting')
        exitSys = True

    if len(str(year)) != 4:
        print('Year must be four characters. Exiting')
        exitSys = True

    if (doy < 1) or (doy > 366):
        print('Day of year must be bewteen 1 and 366. Exiting')
        exitSys = True

    s = snr_type
    if (s == 99) or (s == 50) or (s==66) or (s==88) or (s==77):
        okokok = 1
        #print('You have picked a proper SNR file format ending.' )
    else:
        print('You have picked an improper SNR file format ending: ' + str(s))
        print('Allowed values are 99, 66, 88, 77, or 50. Exiting')
        exitSys = True

    return exitSys


def rewrite_tseries_wrapids(station):
    """
    given a station name, look at a daily blewitt position (ENV)
    file and write a new file that is less insane to understand
    """
    siteid = station.upper()
    # NA12 env time series
    fname = 'tseries/' + siteid + '.NA12.tenv3'
    fname_rapid = 'tseries/' + siteid + '.NA12.rapid.tenv3'
    outputfile = 'tseries/' + station+ '_na12.env'
    print(fname,outputfile)
    try:
        x=np.genfromtxt(fname, skip_header=1, usecols = (3, 7, 8, 9, 10, 11, 12,13))
        y=np.genfromtxt(fname_rapid, skip_header=1, usecols = (3, 7, 8, 9, 10, 11, 12,13))
        N = len(x)
        N2 = len(y)
        print(N,'open outputfile',outputfile)
        f=open(outputfile,'w+')
        for i in range(0,N):
            mjd = x[i,0]
            yy,mm,dd = mjd_to_date(mjd)
            doy, cdoy, cyyyy, cyy = ymd2doy(yy,mm,dd)
            east = x[i,1] + x[i,2]
            north= x[i,3] + x[i,4]
            # adding in the antenna
            vert = x[i,5] + x[i,6] +  x[i,7]
            f.write(" {0:4.0f} {1:2.0f} {2:2.0f} {3:3.0f} {4:13.4f} {5:13.4f} {6:13.4f} \n".format(yy,mm,dd,doy,east,north,vert))
# write out the rapid numbers
        for i in range(0,N2):
            mjd = y[i,0]
            yy,mm,dd = mjd_to_date(mjd)
            doy, cdoy, cyyyy, cyy = ymd2doy(yy,mm,dd)
            east = y[i,1] + y[i,2]
            north= y[i,3] + y[i,4]
            # adding in the antenna
            vert = y[i,5] + y[i,6] +  y[i,7]
            f.write(" {0:4.0f} {1:2.0f} {2:2.0f} {3:3.0f} {4:13.4f} {5:13.4f} {6:13.4f} \n".format(yy,mm,dd,doy,east,north,vert))
#  then close it
        f.close()
    except:
        print('some problem writing the output')

def back2thefuture(iyear, idoy):
    """
    user inputs iyear and idoy
    and the code checks that this is not a day in the future
    also don't allow the dates to agree exactly because we 
    do not have the current day's orbit file available (though
    it could be chagned to allow it.

    reject data before the year 2000
    """
    # find out today's date
    year = int(date.today().strftime("%Y"));
    month = int(date.today().strftime("%m"));
    day = int(date.today().strftime("%d"));

    today=datetime.datetime(year,month,day)
    doy = (today - datetime.datetime(today.year, 1, 1)).days + 1

    badDay = False
    if (iyear > year):
        badDay = True
    elif (iyear == year) & (idoy >= doy):
        badDay = True
    elif (iyear < 2000):
        badDay = True

    return badDay


def rinex_ga_highrate(station, year, month, day):
    """
    no longer supported

    parameters
    ------------
    station : string
        4 character station ID, lowercase

    year : integer

    month : integer

    day : integer


    inputs: station name, year, month, day
    picks up a higrate RINEX file from Geoscience Australia
    you can input day =0 and it will assume month is day of year
    not sure if it merges them ...
    2020 September 2 - moved to gz and new ftp site
    ??? does not appear to have Rinex 2 files anymore ???
    ??? goes they switched in 2020 .... ???
    """
    crnxpath = hatanaka_version()
    teqcpath = teqc_version()
    alpha='abcdefghijklmnopqrstuvwxyz'
    # if doy is input
    if day == 0:
        doy=month
        d = doy2ymd(year,doy);
        month = d.month; day = d.day
    doy,cdoy,cyyyy,cyy = ymd2doy(year,month,day)

    GAstopday = 2020 + 196/365.25 # date i got the email saing they weren't going to have v2.11 anymore 
    if (year + doy/365.25) > GAstopday:
        print('GA no longer provides high-rate v 2.11 RINEX files')
        print('If there is significant interest, I will try to port this function over to RINEX 3')
        return
    # old directory
    #gns = 'ftp://ftp.ga.gov.au/geodesy-outgoing/gnss/data/highrate/' + cyyyy + '/' + cyy + cdoy 
    if not os.path.isfile(teqcpath):
        print('You need to install teqc to use high-rate RINEX data from GA.')
        return

    gns = 'ftp://ftp.data.gnss.ga.gov.au/highrate/' + cyyyy + '/' + cdoy + '/'
    print('WARNING: Downloading high-rate GPS data takes a long time.')
    fileF = 0
    for h in range(0,24):
        # subdirectory
        ch = '{:02d}'.format(h)
        print('Hour: ', ch)
        for e in ['00', '15', '30', '45']:
            dname = station + cdoy + alpha[h] + e + '.' + cyy + 'd.gz'
            dname1 = station + cdoy + alpha[h] + e + '.' + cyy + 'd'
            dname2 = station + cdoy + alpha[h] + e + '.' + cyy + 'o'
            url = gns + '/' + ch + '/' + dname
            #print(url)
            try:
                wget.download(url,dname)
                subprocess.call(['gunzip',dname])
                subprocess.call([crnxpath, dname1])
                # delete the d file
                subprocess.call(['rm',dname1])
                fileF = fileF + 1
            except:
                okok = 1
                #print('download failed for some reason')

    # you cannot merge things that do not exist
    if (fileF > 0):
        foutname = 'tmp.' + station + cdoy
        rinexname = station + cdoy + '0.' + cyy + 'o'
        print('merge the 15 minute files and move to ', rinexname)
        mergecommand = [teqcpath + ' +quiet ' + station + cdoy + '*o']
        fout = open(foutname,'w')
        subprocess.call(mergecommand,stdout=fout,shell=True)
        fout.close()
        cm = 'rm ' + station + cdoy + '*o'
        print(cm)
        # if the output is made (though I guess this does not check to see if it is empty)
        if os.path.isfile(foutname):
            # try to remove the 15 minute files
            subprocess.call(cm,shell=True)
            subprocess.call(['mv',foutname,rinexname])
    else:
        print('No files were available for you from GA.')


def highrate_nz(station, year, month, day):
    """
    inputs: station name, year, month, day
    picks up a RINEX file from GNS New zealand
    you can input day =0 and it will assume month is day of year
    you can also try this site - not coded up yet, but I think
    the data stay there for a couple months for some sites.
    ftp://ftp.geonet.org.nz/rtgps/rinex1Hz/PositioNZ/2021/062/
    21sep02 - started to change from ftp to https - but did not finish
    """
    doy,cdoy,cyyyy,cyy = ymd2doy(year,month,day)
    gns = 'ftp://ftp.geonet.org.nz/gnss/event.highrate/1hz/raw/' + cyyyy +'/' + cdoy + '/'
    gns = 'https://data.geonet.org.nz/gnss/event.highrate/1hz/raw/' + cyyyy +'/' + cdoy + '/'
    print(gns)
    stationU=station.upper()
    # will not work for all days but life is short
    cmm  = '{:02d}'.format(month)
    cdd  = '{:02d}'.format(day)
    exedir = os.environ['EXE']
    trimbleexe = exedir + '/runpkr00' 
    #teqc = exedir + '/teqc' 
    teqc = teqc_version()
    if not os.path.exists(teqc):
        print('teqc executable does not exist. Exiting')
        print('This could be replaced with gfzrnx. Please submitting a pull request.')
        sys.exit()
         
    for h in range(0,24):
        # subdirectory
        chh = '{:02d}'.format(h)
        file1= stationU + cyyyy + cmm + cdd  + chh + '00b.T02'
        file1out= stationU + cyyyy + cmm + cdd  + chh + '00b.tgd'
        file2= stationU + cyyyy + cmm + cdd  + chh + '00b.rnx'
        url = gns + file1
        try:
            wget.download(url,file1)
            subprocess.call([trimbleexe, '-g','-d',file1])
            print(file1out, file2)
            f = open(file2, 'w')
            subprocess.call([teqc, '-week', '2083', '-O.obs', 'S1+S2+C2+L2', file1out], stdout=f)
            f.close()
            print('successful download from GeoNet New Zealand')
        except:
            print('some kind of problem with download',file1)


def get_orbits_setexe(year,month,day,orbtype,fortran):
    """
    picks up and stores orbits as needed
    also sets executable location (gpsonly vs gnss)
    parameters
    ---------
    year : integer

    month : integer

    day : integer

    orbtype : string
        orbit source, e.g. nav, gps...

    fortran : boolean
        whether you are using forran code for translation

    returns
    -------------

    foundit : boolean
        whether orbit file was found
    f : string
        name of the orbit file
    orbdir : string
        location of the orbit file
    snrexe : string 
        location of SNR executable. only relevant for fortran users
    """
    #default values
    foundit = False
    f=''; orbdir=''
    # define directory for the conversion executables
    exedir = os.environ['EXE']
    if (orbtype == 'grg'):
        # French multi gnss, but there are no Beidou results
        f,orbdir,foundit=getsp3file_mgex(year,month,day,'grg')
        snrexe = gnssSNR_version() ; warn_and_exit(snrexe,fortran)
    elif (orbtype == 'gfr'):
        print('uses rapid GFZ orbits, avail as of 2021/137, now pointing to local GFZ directory ')
        f,orbdir,foundit=rapid_gfz_orbits(year,month,day)
        snrexe = gnssSNR_version() ; warn_and_exit(snrexe,fortran)
    elif (orbtype == 'sp3'):
        print('uses default IGS orbits, so only GPS ?')
        f,orbdir,foundit=getsp3file_flex(year,month,day,'igs')
        snrexe = gnssSNR_version() ; warn_and_exit(snrexe,fortran)
    elif (orbtype == 'gfz'):
        print('using gfz sp3 file, GPS and GLONASS') # though I advocate gbm
        f,orbdir,foundit=getsp3file_flex(year,month,day,'gfz')
        snrexe = gnssSNR_version() ; warn_and_exit(snrexe,fortran)
    elif (orbtype == 'igr'):
        print('using rapid IGS orbits, so only GPS')
        f,orbdir,foundit=getsp3file_flex(year,month,day,'igr') # use default
        snrexe = gnssSNR_version() ; warn_and_exit(snrexe,fortran)
    elif (orbtype == 'igs'):
        print('using IGS final orbits, so only GPS')
        f,orbdir,foundit=getsp3file_flex(year,month,day,'igs') # use default
        snrexe = gnssSNR_version(); warn_and_exit(snrexe,fortran)
    elif (orbtype == 'gbm'):
        # this uses GFZ multi-GNSS and is rapid, but not super rapid
        f,orbdir,foundit=getsp3file_mgex(year,month,day,'gbm')
        snrexe = gnssSNR_version() ; warn_and_exit(snrexe,fortran)
    elif (orbtype == 'wum'):
        # this uses WUHAN multi-GNSS which is ultra, but is not rapid ??
        # but only hour 00:00
        f,orbdir,foundit=getsp3file_mgex(year,month,day,'wum')
        snrexe = gnssSNR_version() ; warn_and_exit(snrexe,fortran)
    elif orbtype == 'jax':
        # this uses JAXA, has GPS and GLONASS and appears to be quick and reliable
        f,orbdir,foundit=getsp3file_mgex(year,month,day,'jax')
        snrexe = gnssSNR_version(); warn_and_exit(snrexe,fortran)
    # added iwth help of Makan Karegar 
    elif orbtype == 'esa':
        # this uses ESA, GPS+GLONASS available from Aug 6, 2006 (added by Makan)
        f,orbdir,foundit=getsp3file_flex(year,month,day,'esa')
        snrexe = gnssSNR_version(); 
        warn_and_exit(snrexe,fortran)
    elif orbtype == 'nav':
        #print('getting nav orbits ... i hope')
        f,orbdir,foundit=getnavfile(year, month, day) # use default version, which is gps only
        snrexe = gpsSNR_version() ; warn_and_exit(snrexe,fortran)
    elif orbtype == 'test':
        # i can't even remember this ... 
        print('getting gFZ orbits from CDDIS using test protocol')
        f,orbdir,foundit=getnavfile(year, month, day) # use default version, which is gps only
        snrexe = gnssSNR_version(); warn_and_exit(snrexe,fortran)
    elif orbtype == 'ultra':
        print('getting ultra rapid orbits from GFZ local machine')
        f, orbdir, foundit = ultra_gfz_orbits(year,month,day,0)
        snrexe = gnssSNR_version(); warn_and_exit(snrexe,fortran)
    else:
        print('I do not recognize the orbit type you tried to use: ', orbtype)

    return foundit, f, orbdir, snrexe

def warn_and_exit(snrexe,fortran):
    """
    if snr executable does not exist, exit
    2020sep04 - send it fortran boolean.  
    """
    if not fortran:
        ok = 1
        #print('not using fortran, so it does not matter if translation exe exists')
    else:
        #print('you are using fortran, so good to check now if translation exe exists')
        if (os.path.isfile(snrexe) == False):
            print('This RINEX translation executable does not exist:' + snrexe )
            print('Install it or use -fortran False. Exiting')
            sys.exit()

def new_rinex3_rinex2(r3_filename,r2_filename,dec=1,gpsonly=False):
    """
    assuming gfzrnx executable exists, the rinex 3 file is hatanaka
    uncompressed and translated into a rinex 2 file

    parameters
    ----------
    r3_filename : string
         rinex 3 format filename. either Hatanaka compressed or uncompressed allowed

    r2_filename : string
         rinex 2.11 file

    dec : integer
        decimation factor. default is 0 or 1 which means none

    gpsonly : boolean

        whether you want only GPS signals. Default is false

    returns
    -----------
    fexists : boolean
        whether rinex 2 file was created and exists

    """
    fexists = False
    gexe = gfz_version()
    crnxpath = hatanaka_version()
    #lastbit =  r3_filename[-6:]
    if r3_filename[-3:] == 'crx':
        if not os.path.exists(crnxpath):
            print('You need to install Hatanaka translator. Exiting.')
            sys.exit()
        r3_filename_new = r3_filename[0:35] + 'rnx'
        s1=time.time()
        print('Converting to Hatanaka compressed to uncompressed')
        subprocess.call([crnxpath, r3_filename])
        s2=time.time()
        print(round(s2-s1,2), ' seconds')
        # removing the compressed version - will keep new version
        subprocess.call(['rm', '-f', r3_filename ])
        # now swap name
        r3_filename = r3_filename_new
    gobblygook = myfavoriteobs()
    gobblygook_gps = myfavoritegpsobs()
    #print('decimate value: ', dec)
    if not os.path.exists(gexe):
        print('gfzrnx executable does not exist and this file cannot be translated')
    else:
        s1=time.time()
        if os.path.isfile(r3_filename):
            try:
                if (dec == 1) or (dec == 0):
                    if (gpsonly):
                        subprocess.call([gexe,'-finp', r3_filename, '-fout', r2_filename, '-vo','2','-ot', gobblygook_gps, '-f','-q'])
                    else:
                        subprocess.call([gexe,'-finp', r3_filename, '-fout', r2_filename, '-vo','2','-ot', gobblygook, '-f','-q'])
                    #'-sei','out','-smp',crate
                else:
                    crate = str(dec)
                   #subprocess.call([gfzpath,'-finp', searchpath, '-fout', tmpname, '-vo',str(version),'-sei','out','-smp',crate,'-f','-q'])

                    if (gpsonly):
                        subprocess.call([gexe,'-finp', r3_filename, '-fout', r2_filename, '-vo','2','-ot', gobblygook_gps, '-sei','out','-smp', crate, '-f','-q'])
                    else:
                        subprocess.call([gexe,'-finp', r3_filename, '-fout', r2_filename, '-vo','2','-ot', gobblygook, '-sei','out','-smp', crate, '-f','-q'])
                if os.path.exists(r2_filename):
                    print('Look for the rinex 2.11 file here: ', r2_filename)
                    fexists = True
                else:
                    sigh = 0
            except:
                print('some kind of problem in translation from RINEX 3 to RINEX 2.11')
        else:
            print('RINEX 3 file does not exist', r3_filename)
        s2=time.time()
        print('gfzrnx rinex3 to rinex 2:', round(s2-s1,2), ' seconds')


    return fexists


def ign_orbits(filename, directory,year):
    """
    inputs are filename of MGEX sp3 and directory at IGN
    """
    # without gz
    stripped_name = filename[0:-3]
    url = directory + filename

    try:
        wget.download(url,filename)
        if os.path.exists(filename):
            subprocess.call(['gunzip',filename])
            store_orbitfile(stripped_name,year,'sp3') ; 
            foundit = True
    except:
        #print('some kind of issue at ign_orbits')
        foundit = False

    return foundit 


def ign_rinex3(station9ch, year, doy,srate):
    """
    download rinex 3 from IGN
    inputs: 9 character station name, year, day of year and srate
    is sample rate in seconds
    note: this code works - but it does not turn it into RINEX 2 for you
    """
    fexist = False
    crnxpath = hatanaka_version()
    cyyyy, cyy, cdoy = ydoych(year,doy)

    csrate = '{:02d}'.format(srate)

    url = 'ftp://igs.ensg.ign.fr/pub/igs/data/' + cyyyy + '/' + cdoy + '/'
    ff = station9ch.upper() +   '_R_' + cyyyy + cdoy + '0000_01D_' + csrate + 'S_MO' + '.crx.gz'
    ff1 = station9ch.upper() +   '_R_' + cyyyy + cdoy + '0000_01D_' + csrate + 'S_MO' + '.crx'
    ff2 = station9ch.upper() +   '_R_' + cyyyy + cdoy + '0000_01D_' + csrate + 'S_MO' + '.rnx'
    url = url + ff
    #print(url)
    try:
        wget.download(url,ff)
        subprocess.call(['gunzip',ff])
        subprocess.call([crnxpath,ff1])
        # get rid of compressed file
        subprocess.call(['rm','-f',ff1])
    except:
        print('problem with IGN download')

    if os.path.exists(ff2):
        fexist = True

    return fexist


def hatanaka_version():
    """
    return string with location of hatanaka executable
    """
    exedir = os.environ['EXE']
    hatanakav = exedir + '/CRX2RNX'
    # heroku version should be in the main area
    if not os.path.exists(hatanakav):
        hatanakav = './CRX2RNX'
    return hatanakav

def gfz_version():
    """
    return string with location of gfzrnx executable
    """
    exedir = os.environ['EXE']
    gfzv = exedir + '/gfzrnx'
    # heroku version should be in the main area
    if not os.path.exists(gfzv):
        gfzv = './gfzrnx'
    return gfzv

def gpsSNR_version():
    """
    returns
    -----
    gpse : string
        location of gpsSNR executable
    """
    exedir = os.environ['EXE']
    gpse = exedir + '/gpsSNR.e'
    # heroku version should be in the main area
    if not os.path.exists(gpse):
        gpse = './gpsSNR.e'
    return gpse

def gnssSNR_version():
    """
    returns
    ------
    gpse : string 
        location of gnssSNR executable
    """
    exedir = os.environ['EXE']
    gpse = exedir + '/gnssSNR.e'
    # heroku version should be in the main area
    if not os.path.exists(gpse):
        gpse = './gnssSNR.e'
    return gpse

def teqc_version():
    """

    return
    --------
    gpse : string 
        location of teqcexecutable
    """
    exedir = os.environ['EXE']
    gpse = exedir + '/teqc'
    # heroku version should be in the main area
    if not os.path.exists(gpse):
        gpse = './teqc'
    return gpse

def snr_exist(station,year,doy,snrEnd):
    """
    check to see if the SNR file already exists

    parameters
    -----------
    station : string
        four character station name

    year : integer

    doy : integer

    snrEnd : string
        2 character snr type, i.e. 66, 99

    returns
    ----------
    snre : boolean
        whether SNR file exists

    """
    xdir = os.environ['REFL_CODE']
    cyyyy, cyy, cdoy = ydoych(year,doy)

    f= station + cdoy + '0.' + cyy + '.snr' + snrEnd
    fname = xdir + '/' + cyyyy + '/snr/' + station + '/' + f
    fname2 = xdir + '/' + cyyyy + '/snr/' + station + '/' + f  + '.xz'
    fname3 = xdir + '/' + cyyyy + '/snr/' + station + '/' + f  + '.gz'
    snre = False
    # check for both
    if os.path.isfile(fname):
        snre = True
    if os.path.isfile(fname2) and (not snre):
        snre = True # but needs to be uncompressed
        subprocess.call(['unxz', fname2])
    if os.path.isfile(fname3) and (not snre):
            snre = True # but needs to be ungzipped 
            subprocess.call(['gunzip', fname3])

    return snre 

def get_sopac_navfile(navfile,cyyyy,cyy,cdoy):
    """

    downloads navigation file from SOPAC 

    parameters
    --------------
    navfile : string
        name of GPS broadcast orbit file
    cyyyy : string
        4 char year
    cyy : string
        2 char year
    cdoy : string
        3 char day of year

    returns: 
    ---------
    navfile : string (which was sent)

    """
    sopac = 'ftp://garner.ucsd.edu'
    navfile_sopac1 =  navfile   + '.Z' # regular nav file
    navfile_compressed = navfile_sopac1
    url_sopac1 = sopac + '/pub/rinex/' + cyyyy + '/' + cdoy + '/' + navfile_sopac1

    # sometimes it is not compressed ... but I am going to ignore these times
    navfile_sopac2 =  navfile
    url_sopac2 = sopac + '/pub/rinex/' + cyyyy + '/' + cdoy + '/' + navfile_sopac2


    try:
        wget.download(url_sopac1,navfile_compressed)
        subprocess.call(['uncompress',navfile_compressed])
    except:
        okokok = 1

    return navfile

def get_esa_navfile(cyyyy,cdoy):
    """

    downloads GPS broadcast navigation file from ESA
    tries both Z and gz compressed

    parameters
    --------------
    cyyyy : string
        4 char year
    cdoy : string
        3 char day of year

    returns
    ---------
    fstatus : boolean
        whether file was found or not

    """
    fstatus = False
    cyy = cyyyy[2:4]
    esa = 'ftp://gssc.esa.int/gnss/data/daily/' + cyyyy + '/brdc/'
    # what we want to find
    navfile = 'brdc' + cdoy + '0.' + cyy + 'n' 
    # have to check both Z and gz because ...
    navfilegz = 'brdc' + cdoy + '0.' + cyy + 'n.gz' 
    print(esa+navfilegz)
    navfileZ = 'brdc' + cdoy + '0.' + cyy + 'n.Z' 

    navfile_out = 'auto' + cdoy + '0.' + cyy + 'n' 

    navfile_url =  esa + navfilegz
    try:
        wget.download(navfile_url,navfilegz)
        subprocess.call(['gunzip',navfilegz])
    except:
        okokok = 1

    if not os.path.exists(navfile):
        navfile_url =  esa + navfileZ
        try:
            wget.download(navfile_url,navfileZ)
            subprocess.call(['uncompress',navfileZ])
        except:
            okokok = 1

    # rename it.
    if os.path.exists(navfile):
        print('mv the file to our naming convention')
        subprocess.call(['mv',navfile, navfile_out])
        fstatus = True
    else:
        print('No file was found at ESA')

    return fstatus

def get_cddis_navfile(navfile,cyyyy,cyy,cdoy):
    """
    tries to download navigation file from CDDIS

    parameters
    -----------
    navfile : string
        name of GPS broadcast orbit file
    cyyyy : string
        4 char year
    cyy : string
        2 char year
    cdoy : string
        3 char day of year

    returns
    --------
    navfile : string
    """

    cddisfile = 'brdc' + cdoy + '0.' +cyy  +'n'
    cddisfile_compressed = cddisfile + '.Z'
    cddisfile_gzip = cddisfile + '.gz'
    # where the file should be at CDDIS ....
    mdir = '/gps/data/daily/' + cyyyy + '/' + cdoy + '/' +cyy + 'n/'

    foundit = False
    print('First try the unix compressed version')
    try:
        cddis_download_2022B(cddisfile_compressed,mdir)
    except:
        okokok = 1

    if os.path.isfile(cddisfile_compressed):
        size = os.path.getsize(cddisfile_compressed)
        if (size == 0):
            subprocess.call(['rm',cddisfile_compressed])
        else:
            subprocess.call(['uncompress',cddisfile_compressed])
            foundit = True

    print('Second: try the gzipped version')
    if (not foundit):
        try:
            cddis_download_2022B(cddisfile_gzip,mdir)
        except:
            okokok = 1
        if os.path.isfile(cddisfile_gzip):
            size = os.path.getsize(cddisfile_gzip)
            if (size == 0):
                subprocess.call(['rm',cddisfile_gzip])
            else:
                subprocess.call(['gunzip',cddisfile_gzip])
                foundit = True
    
    if os.path.isfile(cddisfile):
        print('Change the filename to what we use ', navfile)
        subprocess.call(['mv',cddisfile,navfile])

    return navfile

def cddis_download(filename, directory):
    """
    https://cddis.nasa.gov/Data_and_Derived_Products/CDDIS_Archive_Access.html
    attempt to use more secure download protocol that is CDDIS compliant

    input: filename and directory (without leading location)

    this will replace using wget.download when CDDIS turns off anonymous ftp

    was supposed to returns whether file was created but now it just returns true
#   --no-check-certificate

    this is no longer used

    """
    # make sure there is a logs directory
    if not os.path.isdir('logs'):
        subprocess.call(['mkdir', 'logs'])
    station = filename[0:4]
    fn = 'logs/' + station + '_cddis.txt'
    #cddislog = open(fn, 'w+') 
    filename = 'ftps://gdc.cddis.eosdis.nasa.gov' + directory + filename 
    callit = ['wget', '--ftp-user','anonymous','--ftp-password', 'kristine@colorado.edu', '-q','-nv','--no-check-certificate', filename]
    subprocess.call(callit)
    # try this new way - I am trying to send the messages to the file
    #out = subprocess.run(callit, capture_output=True,text=True)
    #cddislog.write(out.stderr)
    #cddislog.close()
    return True 


def ydoy2useful(year, doy):
    """

    parameters
    ----------
    year : integer

    doy : integer
        day of year

    returns
    ---------
    year : integer

    month : integer

    day : integer

    cyyyy : string
        four character year
    cdoy : string
        three character day of year

    YMD : string
         date as in '19-12-01' for December 1, 2019

    """

    d = datetime.datetime(year, 1, 1) + datetime.timedelta(days=(doy-1))
#   not sure you need to do this int step
    month = int(d.month)
    day = int(d.day)
    cyyyy, cyy, cdoy = ydoych(year,doy)

    cdd = '{:02d}'.format(day)
    cmonth = char_month_converter(month)
    YMD = cyy + cmonth + cdd
    return year, month, day, cyyyy,cdoy, YMD

def prevdoy(year,doy):
    """
    given year and doy, return previous year and doy
    parameters
    -------------
    year : integer
    
    doy : integer

    returns
    ----------
    pyear : integer
        previous year

    pdoy : integer 
        previous day of year 
    """
    if (doy == 1):
        pyear = year -1
        doyx,cdoyx,cyyyy,cyy = ymd2doy(pyear,12,31)
        pdoy = doyx
    else:
#       doy is decremented by one and year stays the same
        pdoy = doy - 1
        pyear = year

    return pyear, pdoy

def nextdoy(year,doy):
    """
    given a year/doy returns the subsequent year/doy

    parameters
    ---------
    year : integer

    doy : integer

    returns
    ----------

    nyear : integer
        next year

    ndoy : integer
        next day of year

    """
    dec31,cdoy,ctmp,ctmp2 = ymd2doy(year,12,31)
    if (doy == dec31):
        nyear = year + 1
        ndoy = 1
    else:
        nyear = year
        ndoy = doy + 1

    return nyear, ndoy

def read_sp3file(file_path):
    """ 
    input: file_path is the sp3file name

    Returns
    -------
    sp3 : ndarray
    colums are satnum, gpsweek, gps_sow, x,y,z
    x,y,z are in meters
    satnum has 0, 100, 200, 300 added for gps, glonass, galileo,beidou,
    respectively.  all other satellites are ignored
    some of this code came from joakim

    """
    ignorePoint = False
    max_sat = 150 # not used
    # store as satNu, week, sec of week , x, y, and z?
    sp3 = np.empty(shape=[0, 6])
    count = -1
    firstEpochFound = False

    f = open(file_path, 'r')
    for line in f.readlines():
        #all time tags have a * in first column
        if line[0] == '*':
            year,month,day,hour,minute,second = line.split()[1:]
            wk,swk = kgpsweek(int(year), int(month), int(day), int(hour), int(minute), float(second))
            wk = int(wk) ; swk = float(swk)
            if (not firstEpochFound):
                firstWeek = wk 
                firstEpochFound = True
                #print('first GPS Week and Seconds in the file', firstWeek, swk)
            count += 1
            if (wk != firstWeek):
                #print('this is a problem - this code should not be used with files that crossover GPS weeks ')
                #print('JAXA orbits have this extra point, which is going to be thrown out')
                ignorePoint = True
        if (line[0] == 'P') and (not ignorePoint):
            co = line[1]
            out = findConstell(co)
            satNu = int(line[2:4]) + out
            xs = line.split()
            # do not allow SBAS etc
            if satNu < 400:
                x = float(xs[1])*1000.0
                y = float(xs[2])*1000.0
                z = float(xs[3])*1000.0
                lis = [satNu, wk,swk, x,y,z]
                sp3 = np.vstack((sp3,lis))
    f.close()
    nr,nc = sp3.shape
    #print('number of rows and columns being returned from the sp3 file', nr,nc)
    return sp3

def nicerTime(UTCtime):
    """
    input float hour
    output HH:MM string
    2021 may 3, changed to deal with hour boundaries
    since thsi only does hours and minutes, it rounds up or down
    depending on seconds < or > 30
    fails near midnite ... 
    """
    hour = int(np.floor(UTCtime))
    minute = int ( np.floor(60* ( UTCtime - hour )))
    second = int ( 3600*UTCtime - 3600*hour  - 60*minute)
    #print(hour,minute,second)
    if (second > 30):
        # up the minutes ...
        minute = minute + 1
        # sure hope this works - beyond annoying
        if minute == 60:
            minute = 0
            hour = hour + 1

    chour = '{:02d}'.format(hour)
    cminute = '{:02d}'.format(minute)
    T = chour + ':' + cminute  

    return T


def big_Disk_work_hard(station,year,month,day):
    """
    attempts to pick up subdaily files from the NGS archive
    creates a single RINEX file

    parameters
    -----------

    station: string
        4 character id station name

    year: integer
        year

    month: integer
        month

    day: integer
        day
        if day is 0, then month is presumed to be the day of year

    """
    if (day == 0):
        doy = month
        year, month, day, cyyyy,cdoy, YMD = ydoy2useful(year,doy)
        cyy = cyyyy[2:4]
    else:
        doy,cdoy,cyyyy,cyy = ymd2doy(year,month,day)

    # want to merge the hourly files into this filename
    rinexfile =  station + cdoy + '0.' + cyy + 'o'
    exc = teqc_version()
    if not os.path.exists(exc):
        print('teqc is used for this subroutine - it does not exist, so exiting.')
        print('Please help us by submitting a pull request.')
        sys.exit()

    let = 'abcdefghijklmnopqrstuvwxyz';
    alist = [exc]
    blist = ['rm']
    for i in range(0,24):
        idtag = let[i:i+1]
        fname= station + cdoy + idtag + '.' + cyy + 'o'
        # if it does not exist, try to get it
        if not os.path.isfile(fname):
            big_Disk_in_DC_hourly(station, year, month, day,idtag) 
        else:
            print(fname, ' exists')
        if os.path.isfile(fname):
            alist.append(fname)
            blist.append(fname)

    print(alist)
    fout = open(rinexfile,'w')
    subprocess.call(alist,stdout=fout)
    fout.close()
    print('file created: ', rinexfile)
    # should delete the hourly files
    subprocess.call(blist)


def big_Disk_in_DC_hourly(station, year, month, day,idtag):
    """
    picks up a RINEX file from CORS. and gunzips it

    parameters
    ---------
    station : string
        
    year : integer

    month : integer

    day : integer
        day of the month. if zero, it means month is really day of year
    idtag : character
        small case letter from a to x (i think)
    """
    doy,cdoy,cyyyy,cyy = ymd2doy(year,month,day)
    #rinexfile,rinexfiled = rinex_name(station, year, month, day)
    # compressed rinexfile
    crinexfile = station + cdoy + idtag + '.' + cyy + 'o.gz'
    rinexfile =  station + cdoy + idtag + '.' + cyy + 'o'
    # do not know if this works - but what the hey
    mainadd = 'https://geodesy.noaa.gov/corsdata/rinex/'
    #mainadd = 'ftp://www.ngs.noaa.gov/cors/rinex/'
    url = mainadd + cyyyy + '/' + cdoy+ '/' + station + '/' + crinexfile
    print(url)
    try:
        wget.download(url, out=crinexfile)
        status = subprocess.call(['gunzip', crinexfile])
    except:
        print('some problem in download - maybe the site does not exist on this archive')


def check_environ_variables():
    """
    This is my attempt to make the code useable by people
    that have not set EXE, REFL_CODE, or ORBITS environment
    variables.  If that is the case, these variables will be 
    set to . 
    """
    variables= ['EXE','ORBITS','REFL_CODE']
    for env_var in variables:
        if env_var not in os.environ:
            print(env_var, ' not found, so set to current directory')
            os.environ[env_var] = '.'


def ftitle(freq):
    """
    makes a frequency title for plots 

    parameters
    --------
    freq : integer
        frequency

    returns
    -----------
    returnf : string
        nice string for the constellation/frequency for the title of a plot
    """
    f=str(freq)
    out = {}
    out['1'] = 'GPS L1'
    out['2'] = 'GPS L2'
    out['20'] = 'GPS L2C'
    out['5'] = 'GPS L5'
    out['101'] = 'Glonass L1'
    out['102'] = 'Glonass L2'
    out['201'] = 'Galileo L1'
    out['205'] = 'Galileo L5'
    out['206'] = 'Galileo L6'
    out['207'] = 'Galileo L7'
    out['208'] = 'Galileo L8'
    # still need to work on these because it is confusing!...
    out['301'] = 'Beidou L1'
    out['302'] = 'Beidou L2'
    out['305'] = 'Beidou L5'
    out['306'] = 'Beidou L6'
    out['307'] = 'Beidou L7'
    if freq not in [1,2, 20,5,101,102,201,205,206,207,208,301,302,305,306,307]:
        returnf = ''
    else:
        returnf = out[f]

    return returnf 

def cdate2nums(col1):
    """
    returns fractional year from ch date, e.g. 2012-02-15
    if time is blank, return 3000

    parameters
    ------------
    col1 : string
        date in yyyyy-mm-dd, 2012-02-15

    returns
    -----------
    t : float
        fractional date, year + doy/365.25
    """
    year = int(col1[0:4])
    if year == 0:
        t=3000 # made up very big time!
    else:
        month = int(col1[5:7])
        day = int(col1[8:10])
        #print(col1, year, month, day)
        doy,cdoy,cyyyy,cyy = ymd2doy(year, month, day )
        t = year + doy/365.25

    return t

def l2c_l5_list(year,doy):
    """
    for given year and day of year, returns a satellite list of 
    L2C and L5 transmitting satellites

    parameters
    --------------
    year: integer
        year

    doy: integer
        day of year

    """

    # this numpy array has the satellite number, year, and doy of each launch of a L2C satellite
    l2c=np.array([[1 ,2011 ,290], [3 ,2014 ,347], [4 ,2018 ,357], [5 ,2008 ,240],
        [6 ,2014 ,163], [7 ,2008 ,85], [8 ,2015 ,224], [9 ,2014 ,258], [10 ,2015 ,343],
        [11, 2021, 168],
        [12 ,2006 ,300], [14 ,2020 ,310], [15 ,2007 ,285], [17 ,2005 ,270],
        [18 ,2019 ,234], [23 ,2020 ,182], [24 ,2012 ,319], [25 ,2010 ,240],
        [26 ,2015 ,111], [27 ,2013 ,173], [29 ,2007 ,355], [30 ,2014 ,151], [31 ,2006 ,270], [32 ,2016 ,36]])
    # indices that meet your criteria
    ij=(l2c[:,1] + l2c[:,2]/365.25) < (year + doy/365.25)
    l2csatlist = l2c[ij,0]

    # The L5 list is defined by 2010, doy 148
    firstL5 = 2010 + 148/365.25 # launch may 28, 2010  - some delay before becoming healthy

    newlist = l2c[ij,:]
    ik= (newlist[:,1] + newlist[:,2]/365.25) > firstL5
    l5satlist = newlist[ik,0]

    return l2csatlist, l5satlist


def binary(string):
    """
    changes python string to bytes for use in
    fortran code using f2py via numpy
    input is a string, output is bytes with null at the end
    """
    j=bytes(string,'ascii') + b'\0\0'

    return array(j)

def ymd_hhmmss(year,doy,utc,dtime):
    """
    parameters
    ---------
    year : integer

    doy : integer

    UTC : float

    dtime : logical


    inputs: year, day of year, UTC (fractional hours)
    dtime is a logical for whether you want a datetime object
    since i save things in year, doy and UTC hours ...
    this gives back datetime obj and the input for that
    (year month day hour minute second, in integers i believe)
    """
    year = int(year) # just in case
    d = datetime.datetime(year, 1, 1) + datetime.timedelta(days=(doy-1))
    month = int(d.month)
    day = int(d.day)
    hour = int(np.floor(utc))
    minute = int ( np.floor(60* ( utc- hour )))
    second = int(utc*3600 - (hour*3600 + minute*60))
    if second == 60:
        second = 0
        minute = minute + 1
    if minute == 60:
        minute = 0
        hour = hour + 1
    # i dunno what you do if hour > 24! well, i do, but it is annoying
    bigT = 0
    if dtime:
        bigT = datetime.datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=second)
    return bigT, year, month, day, hour, minute, second


def get_obstimes(tvd):
    """
    send a LSP results, so the variable created when you read 
    in the results file.  return obstimes for plotting 
    """
    nr,nc = tvd.shape
    obstimes = []

    if nr > 0:
        for ijk in range(0,nr):
            dtime, iyear,imon,iday,ihour,imin,isec = ymd_hhmmss(tvd[ijk,0],tvd[ijk,1],tvd[ijk,4],True)
            obstimes.append(dtime)
    else:
        print('empty file')

    return obstimes

def get_obstimes_plus(tvd):
    """
    send a LSP results file, so the variable created when you read
    in the results file.  return obstimes for matplotlib plotting purposes
    2022jun10 - added MJD output
    """
    nr,nc = tvd.shape
    obstimes = []
    modjulian = np.empty(shape=[0,1])

    if nr > 0:
        for ijk in range(0,nr):
            dtime, iyear,imon,iday,ihour,imin,isec = ymd_hhmmss(tvd[ijk,0],tvd[ijk,1],tvd[ijk,4],True)
            obstimes.append(dtime)
            m,f = mjd(iyear,imon,iday,ihour,imin,isec)
            x=[m+f]
            modjulian = np.append(modjulian, [x],axis=0 )
    else:
        print('empty file')

    return obstimes, modjulian


def confused_obstimes(tvd):
    """
    takes lsp results - returns list of MJD values
    """
    nr,nc = tvd.shape
    modifiedjulian = []
    if nr > 0:
        for ijk in range(0,nr):
            dtime, iyear,imon,iday,ihour,imin,isec = ymd_hhmmss(tvd[ijk,0],tvd[ijk,1],tvd[ijk,4],True)
            m,f = mjd(iyear,imon,iday,ihour,imin,isec)
            modifiedjulian = np.append(modifiedjulian, m+f)
    else:
        print('empty file')

    return modifiedjulian


def read_simon_williams(filename,outfilename):
    """
    input: filename of GNSS based water level measurements from 
    the archived at PSMSL created by Simon Williams 

    return lists of datetime obstimes, MJD, and mod-water-level in meters
    2022 july 4
    also returns PRN, frequency, and azimuth numpy arrays
    """

    fout = open(outfilename,'w+')
    print('Writing Simon Williams data to ', outfilename)
    csv = False
    if outfilename[-3:] == 'csv':
        csv = True

    if csv:
        fout.write("# YYYY,MM,DD,HH,MM, Water(m),DOY, MJD, Seconds,Freq, Azim,PRN \n")
    else:
        fout.write("%YYYY  MM  DD  HH  MM  Water(m) DOY    MJD    Sec   Freq  Azim    PRN  raw  fit-tide \n")
        fout.write("% (1) (2) (3) (4)  (5)   (6)    (7)     (8)   (9)   (10)   (11)  (12)  (13)  (14) \n")



    # read the file three times because i am loadtxt impaired
    # string
    tv = np.loadtxt(filename,usecols=(0,1,2,3),skiprows=10,dtype='str',delimiter=',')
    # integers
    ivals = np.loadtxt(filename,usecols=(4,5),skiprows=10, dtype='int',delimiter=',')
    # floats
    fvals = np.loadtxt(filename,usecols=(6),skiprows=10, dtype='float',delimiter=',')
    # store the latter columns directly
    prn = ivals[:,0]
    fr = ivals[:,1]
    az = fvals

    nr = len(tv)
    # these are converted to numpy at the bottom
    obstimes = []
    modjulian = []
    sealevel = []
    s1=time.time()

    for i in range(0,nr):
        year = int(tv[i,0][0:4])
        mm = int(tv[i,0][5:7])
        dd = int(tv[i,0][8:10])
        doy,cdoy,cyyyy,cyy = ymd2doy(year,mm,dd)
        hh = int(tv[i,0][11:13])
        minutes = int(tv[i,0][14:16])
        sec = int(tv[i,0][17:19])
        raw = float(tv[i,1])
        modraw = float(tv[i,2])
        tidefit = float(tv[i,3])
        dtime = datetime.datetime(year=year, month=mm, day=dd, hour=hh, minute=minutes, second=sec)
        imjd, frac = mjd(year,mm,dd,hh,minutes,sec)
        x = [imjd+frac]
        # go ahead and write to a file ... 
        if csv:
            fout.write(" {0:4.0f},{1:2.0f},{2:2.0f},{3:2.0f},{4:2.0f},{5:7.3f},{6:3.0f},{7:15.6f},{8:2.0f},{9:1.0f},{10:8.3f},{11:2.0f},{12:6.3f},{13:6.3f} \n".format(year, mm, dd, hh, minutes, modraw, doy, imjd+frac, sec, fr[i], az[i],prn[i],raw,tidefit))
        else:
            fout.write(" {0:4.0f} {1:3.0f} {2:3.0f} {3:3.0f} {4:3.0f} {5:7.3f} {6:3.0f} {7:15.6f} {8:2.0f} {9:1.0f} {10:8.3f} {11:2.0f} {12:6.3f} {13:6.3f}\n".format(year, mm, dd, hh, minutes, modraw, doy, imjd+frac, sec, fr[i], az[i], prn[i], raw,tidefit))

        obstimes.append(dtime)
        modjulian.append(x)
        sealevel.append(modraw)

    fout.close()

    s2=time.time()
    print('that took ', round(s2-s1,2), ' seconds')

    outobstimes= np.asarray(obstimes)
    outsealevel = np.asarray(sealevel)
    outmjd = np.asarray(modjulian)

    return outobstimes, outmjd, outsealevel, prn, fr, az


def get_noaa_obstimes(t):
    """
    send a noaa file variable. returns datetime obstimes in a list.
    i guess one could learn how to use pandas ... nah
    """
    nr,nc = t.shape
    obstimes = []

    # if i read in the file better, would not have to change from float
    if nr > 0:
        for i in range(0,nr):
            dtime = datetime.datetime(year=int(t[i,0]), month=int(t[i,1]), day=int(t[i,2]), hour=int(t[i,3]), minute=int(t[i,4]), second=0)
            obstimes.append(dtime)
    else:
        print('you sent me an empty variable')

    return obstimes

def get_noaa_obstimes_plus(t):
    """
    send a noaa file variable. returns obstimes.
    updated 2022June11
    and relative gps time (in seconds)
    """
    nr,nc = t.shape
    obstimes = []
    modjulian = np.empty(shape=[0,1])
    #modjulian=[]

    # if i read in the file better, would not have to change from float
    if nr > 0:
        for i in range(0,nr):
            year = int(t[i,0]); month=int(t[i,1]); day=int(t[i,2]); hour=int(t[i,3]); minute=int(t[i,4]); second = 0
            dtime = datetime.datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=second)
            obstimes.append(dtime)
            imjd, fr = mjd(year,month,day,hour,minute,second)
            x = [imjd+fr]
            #modjulian = np.append( modjulian, [x], axis=0 ) 
            modjulian = np.append(modjulian, x)
    else:
        print('you sent me an empty variable')

    return obstimes, modjulian


def queryUNR(station):
    """
    use UNR database to get a priori lat/long in degrees
    and ellipsoidal height (meters)
    """
    xdir = os.environ['REFL_CODE']
    print('Check for the UNR station coordinate database')

    lower = station
    if len(lower) != 4:
        print('No coordinates in the UNR database for ', lower)
        print('The station name must be four characters long')
        return
    # if you used github and run the code from that directory
    nfile = 'gnssrefl/Data.names'
    pfile = 'gnssrefl/Data.pos'
    if os.path.isfile(nfile) and os.path.isfile(pfile):
       print('found the station database files in the gnssrefl directory')
    else:
        nfile = xdir + '/Files/Data.names'
        pfile = xdir + '/Files/Data.pos'
        if os.path.isfile(nfile) and os.path.isfile(pfile):
            print('found the station database files in the REFL_CODE Files directory')
        else:
            print('try to download the station database files from github for you')
            try:
                url1= 'https://github.com/kristinemlarson/gnssrefl/raw/master/gnssrefl/Data.names' 
                url2= 'https://github.com/kristinemlarson/gnssrefl/raw/master/gnssrefl/Data.pos' 
                wget.download(url1,nfile)
                wget.download(url2,pfile)
            except:
                print('failed to get the station database files')
                return
    if os.path.isfile(nfile) and os.path.isfile(pfile):
        labels = np.genfromtxt(nfile, delimiter=' ', dtype=str)
        raw_data = np.genfromtxt(pfile, delimiter=' ' )
        data = {label: row for label, row in zip(labels, raw_data)}
    # should put this in a try
        station = station.upper()
        llat = 0; llon = 0; height = 0;
        try:
            llh = data[station]
            llat =llh[0]; llon =llh[1]; height =llh[2]
        except:
            print('nada-no coordinates in the database')

        if (llat != 0):
            print('\n', lower, llat, llon, height)
            x,y,z=llh2xyz(llat,llon,height)
            print("%15.4f %15.4f %15.4f "% (x,y,z) )
        else:
            print('No coordinates in the UNR database for ', lower)
    else:
        print('Cannot find the requesite UNR files, which usually live in the gnssrefl directory below')
        print('where you installed the gnssrefl code or in $REFL_CODE/Files.')
        return 0,0,0

    # lat and lon are in degrees
    return llat,llon,height

def rapid_gfz_orbits(year,month,day):
    """
    input year, month, day OR
    year, doy, 0
    downloads rapid GFZ sp3 file and stores in $ORBITS
    november 5, 2021 fixed their ftp address
    """
    foundit = False
    dday = 2021 + 137/365.25
    wk,sec=kgpsweek(year,month,day,0,0,0)

    gns = 'ftp://ftp.gfz-potsdam.de/pub/GNSS/products/rapid/'
    if day == 0:
       doy=month
       d = doy2ymd(year,doy);
       month = d.month; day = d.day
    doy,cdoy,cyyyy,cyy = ymd2doy(year,month,day)
    fdir = os.environ['ORBITS'] + '/' + cyyyy + '/sp3'
    littlename = 'gfz' + str(wk) + str(int(sec/86400)) + '.sp3'
    url = gns + 'w' + str(wk) + '/' + littlename + '.gz'
    print(url)
    if (year + doy/365.25) < dday:
        print('No rapid GFZ orbits until 2021/doy137')
        return '', '', foundit
    fullname = fdir + '/' + littlename + '.xz'
    # look for compressed file
    if os.path.isfile(fullname):
        subprocess.call(['unxz', fullname])

    if os.path.isfile(fdir + '/' + littlename):
        print(littlename, ' already exists on disk')
        return littlename, fdir, True 
    try:
        wget.download(url,littlename + '.gz')
        subprocess.call(['gunzip', littlename + '.gz'])
    except:
        print('Problems downloading Rapid GFZ orbit')

    if os.path.isfile(littlename):
       store_orbitfile(littlename,year,'sp3') ; foundit = True

    return littlename, fdir, foundit


def ultra_gfz_orbits(year,month,day,hour):
    """
    input year, month, day OR
    year, doy, 0
    hour is needed to figur out which ultra file to pick up 
    downloads rapid GFZ sp3 file and stores in $ORBITS
    """
    foundit = False
    dday = 2021 + 137/365.25
    wk,sec=kgpsweek(year,month,day,0,0,0)
    gns = 'ftp://ftp.gfz-potsdam.de/pub/GNSS/products/ultra/'
    if day == 0:
       doy=month
       d = doy2ymd(year,doy);
       month = d.month; day = d.day
    doy,cdoy,cyyyy,cyy = ymd2doy(year,month,day)
    fdir = os.environ['ORBITS'] + '/' + cyyyy + '/sp3'
    # change the hour into two character string
    chr = '{:02d}'.format(hour)
    littlename = 'gfu' + str(wk) + str(int(sec/86400)) + '_' + chr + '.sp3'  
    url = gns + 'w' + str(wk) + '/' + littlename + '.gz'
    print(url)
    if (year + doy/365.25) < dday:
        print('No rapid GFZ orbits until 2021/doy137')
        return '', '', foundit

    fullname = fdir + '/' + littlename + '.xz'
    if os.path.isfile(fullname):
        subprocess.call(['unxz', fullname])

    if os.path.isfile(fdir + '/' + littlename):
        print(littlename, ' already exists on disk')
        return littlename, fdir, True


    try:
        wget.download(url,littlename + '.gz')
        subprocess.call(['gunzip', littlename + '.gz'])
    except:
        print('Problems downloading ultrarapid GFZ orbit')

    if os.path.isfile(littlename):
        store_orbitfile(littlename,year,'sp3') ; foundit = True

    return littlename, fdir, foundit

def rinex_unavco(station, year, month, day):
    """
    This is being used by the vegetaiton code!!!!!
    picks up a RINEX file from default unavco area, i.e. not highrate.  
    it tries to pick up an o file,
    but if it does not work, it tries the "d" version, which must be
    decompressed.  the location of this executable is defined in the crnxpath
    variable. 

    station: string 

    year : integer

    month : integer

    day: integer

    WARNING: only rinex version 2.11 in this world

    if day is zero, assumes month is really doy

    21sep01  changed from ftp to https
    """
    exedir = os.environ['EXE']
    crnxpath = hatanaka_version()  # where hatanaka will be
    if day == 0:
        doy = month
        cyyyy = str(year)
        cdoy = '{:03d}'.format(doy)
        cyy = '{:02d}'.format(year-2020)
    else:
        doy,cdoy,cyyyy,cyy = ymd2doy(year,month,day)
    rinexfile,rinexfiled = rinex_name(station, year, month, day)
    unavco= 'https://data.unavco.org/archive/gnss/rinex/obs/'
    filename1 = rinexfile + '.Z'
    filename2 = rinexfiled + '.Z'
    # URL path for the o file and the d file
    url1 = unavco+ cyyyy + '/' + cdoy + '/' + filename1
    url2 = unavco+ cyyyy + '/' + cdoy + '/' + filename2

    try:
        wget.download(url1,filename1)
        status = subprocess.call(['uncompress', filename1])
    except:
        okokok =1

    #print('try hatanaka RINEX at unavco')
    if not os.path.exists(rinexfile):
        #print('look for hatanaka version')
        if os.path.exists(crnxpath):
            try:
                wget.download(url2,filename2)
                status = subprocess.call(['uncompress', filename2])
                status = subprocess.call([crnxpath, rinexfiled])
                status = subprocess.call(['rm', '-f', rinexfiled])
            except:
                okokok =1
            #except Exception as err:
            #    print(err)
        else:
            hatanaka_warning()


def avoid_cddis(year,month,day):
    """
    work around for people that can't use CDDIS ftps
    this will get multi-GNSS files for GFZ from the IGN
    """
    fdir = os.environ['ORBITS'] + '/' + str(year) + '/sp3/'
    doy,cdoy,cyyyy,cyy = ymd2doy(year,month,day)
    foundit = False; 
    wk,swk = kgpsweek(year, month, day, 0,0,0)
    cwk = '{:04d}'.format(wk); cday = str(int(swk/86400))
    # old file name for precise files
    filenameZ = 'gbm' + cwk + cday + '.sp3.Z'
    filename = 'gbm' + cwk + cday + '.sp3'
    if os.path.isfile(fdir + filename):
        print(filename,' orbit file already exists on disk'); foundit = True
        return filename, fdir, foundit
    if os.path.isfile(fdir + filename + '.xz'):
        subprocess.call(['unxz',fdir + filename + '.xz'])
        print(filename, ' orbit file already exists on disk'); foundit = True
        return filename, fdir, foundit

    # only use this for weeks < 2050
    if (wk < 2050):
        url = 'ftp://igs.ensg.ign.fr/pub/igs/products/mgex/' + cwk +  '/' + filenameZ
        try:
            wget.download(url,filenameZ)
            subprocess.call(['uncompress',filenameZ])
            subprocess.call(['mv',filename, fdir])
            foundit = True
        except:
            print('could not find ', filename)
    if (not foundit):
        filename = 'GFZ0MGXRAP_' + cyyyy  + cdoy + '0000_01D_05M_ORB.SP3'
        filenamegz = 'GFZ0MGXRAP_' + cyyyy  + cdoy + '0000_01D_05M_ORB.SP3.gz'

        if os.path.isfile(fdir + filename):
            print(filename, ' orbit file already exists on disk'); foundit = True
            return filename, fdir, foundit
        if os.path.isfile(fdir + filename + '.xz'):
            subprocess.call(['unxz',fdir + filename + '.xz'])
            print(filename, ' orbit file already exists on disk'); foundit = True
            return filename, fdir, foundit

        url = 'ftp://igs.ensg.ign.fr/pub/igs/products/mgex/' + cwk +  '/' + filenamegz
        try:
            wget.download(url, filenamegz)
            if os.path.exists(filenamegz):
                subprocess.call(['gunzip',filenamegz])
                subprocess.call(['mv',filename, fdir])
                foundit=True
        except:
            print('could not find',filename)

    return filename, fdir, foundit

def get_cddis_navfile_test(navfile,cyyyy,cyy,cdoy):
    """
    kristine larson
    inputs navfile name with character string verisons of year, 2ch year and doy
    tries to download from CDDIS archive

    20jun11, implemented new CDDIS security requirements
    21jan06, gz instead of Z
    try to get galileo nav files
    """
    # ths old way
    # just in case you sent it the navfile with auto instead of brdc
    #cddisfile = 'brdc' + navfile[4:] + '.Z'
    #cddis = 'ftp://cddis.nasa.gov'
    # navfile will continue to be called auto
    #navfile_compressed = cddisfile

    # new way
    cddisfile = 'brdc' + cdoy + '0.' +cyy  +'e'
    cddisfile_compressed = cddisfile + '.Z'
    cddisfile_gzip = cddisfile + '.gz'
    # where the file should be at CDDIS ....
    mdir = '/gps/data/daily/' + cyyyy + '/' + cdoy + '/' +cyy + 'n/'

    try:
        cddis_download_2022B(cddisfile_compressed,mdir)
        #cddis_download(cddisfile_compressed,mdir)
        if os.path.isfile(cddisfile_compressed):
            subprocess.call(['uncompress',cddisfile_compressed])
    except:
        okokok = 1
    #except Exception as err:
    #    print(err)
    if not os.path.isfile(cddisfile):
        print('going for the gzip version of the file')
        cddis_download_2022B(cddisfile_gzip,mdir)
        #cddis_download(cddisfile_gzip,mdir)
        if os.path.isfile(cddisfile_gzip):
            subprocess.call(['gunzip',cddisfile_gzip])

    if os.path.isfile(cddisfile):
        print('found it and change the name ')
        subprocess.call(['mv',cddisfile,navfile])

    return navfile

def rinex_jp(station, year, month, day):
    """
    author: Naoya Kadota
    2021oct25
    Picks up RINEX file from Japanese GSI GeoNet archive
    URL : https://www.gsi.go.jp/ENGLISH/index.html

    station : string

    year : integer

    month: integer

    day : integer
    """
    fdir = os.environ['REFL_CODE']
    if not os.path.isdir(fdir):
        print('You need to define the REFL_CODE environment variable')
        return 

    # make sure the directory exists to store passwords
    if not os.path.isdir(fdir + '/Files'):
        subprocess.call(['mkdir',fdir + '/Files'])
    if not os.path.isdir(fdir + '/Files/passwords'):
        subprocess.call(['mkdir',fdir + '/Files/passwords'])

    userinfo_file = fdir + '/Files/passwords/' + 'userinfo.pickle'
    #userinfo.pickle stores your login info
    try:
        with open(userinfo_file, 'rb') as client_info:
            login_info = pickle.load(client_info)
            user_id = login_info[0]
            password = login_info[1]
    except:
        print('User registration is required to use the database')
        print('Access https://www.gsi.go.jp/ENGLISH/geonet_english.html (English)')
        print('or https://terras.gsi.go.jp/ftp_user_regist.php (Japanese) to create an acount')
        print('Please enter your FTP user id (if you do not have an account type none')
        user_id = input()
        if user_id == 'none':
            print('You have no account at Geonet so returning to the main code')
            return
        password= getpass.getpass(prompt='Password: ', stream=None)
        #password = input()
    # if doy is input, convert to month and day
    if day == 0:
        doy=month
        d = doy2ymd(year,doy);
        month = d.month; day = d.day
    doy,cdoy,cyyyy,cyy = ymd2doy(year,month,day)
    gns = 'terras.gsi.go.jp/data/GR_2.11/'
    file1 =station[-4:].upper() + cdoy + '0.' + cyy + 'o' + '.gz'
    url = 'ftp://' + user_id + ':' + password + '@' + gns +  cyyyy + '/' + cdoy +  '/' + file1
    print('attempt to download RINEX file from Jp GeoNet')
    try:
        wget.download(url,file1)
        subprocess.call(['gunzip', file1])
        print('successful download from JP GeoNet')
        if not os.path.isfile(userinfo_file):
            with open(userinfo_file, 'wb') as client_info:
                pickle.dump((user_id,password) , client_info)
                print('user id and password saved to', userinfo_file)
    except:
        print('some kind of problem with Japanese GSI GeoNet download',file1)
        subprocess.call(['rm', '-f',file1])


def queryUNR_modern(station):
    """
    queries the UNR database that has been stored in sql. downloads it if necessary

    parameters
    -----------
    station : string
        4 character station name
    
    returns

    lat : float
        latitude in degrees

    lon : float
        longitude in degrees

    ht : float
        ellipsoidal ht in meters

    """
    lat = 0; lon = 0; ht = 0
    if len(station) != 4:
        print('The station name must be four characters long')
        return lat, lon, ht

    xdir = os.environ['REFL_CODE']
    nfile1 = 'gnssrefl/station_pos.db'
    nfile1_exist = os.path.isfile(nfile1)
    nfile2 = xdir + '/Files/station_pos.db'
    nfile2_exist = os.path.isfile(nfile2)

    if (nfile1_exist) or (nfile2_exist):
        print('found the UNR database')

    if (not nfile1_exist) and (not nfile2_exist):
        url1= 'https://github.com/kristinemlarson/gnssrefl/raw/master/gnssrefl/station_pos.db'
        print('Try to download the station database from github for you:', url1)
        print('If you are not online, it will fail.')
        try:
            #url1= 'https://github.com/kristinemlarson/gnssrefl/raw/master/gnssrefl/station_pos.db'
            wget.download(url1,nfile2)
            nfile2_exist = True
        except:
            print('Could not download the database for you')
            return lat, lon, ht
    # if you used github and run the code from that directory
    if nfile1_exist:
        conn = sqlite3.connect(nfile1)
    elif nfile2_exist:
        conn = sqlite3.connect(nfile2)
    c=conn.cursor()
    c.execute("SELECT * FROM  stations WHERE station=:station",{'station': station})
    w = c.fetchall()
    if len(w) > 0:
        [(name,lat,lon,ht)] = w
        # if longitude is ridiculous, as it often is in the Nevada Reno database make it less so
        if (lon < -180):
            lon = lon + 360
        print(lat,lon,ht)
    else:
        print('Did not find the station in the database:', station)
        # this returns 0 values

    # close the database
    conn.close()

    return lat,lon,ht

def rinex3_nav(year,month,day):
    """
    """
    foundit = False
    fdir = ''
    name = ''
    # https://cddis.nasa.gov/archive/gnss/data/daily/2021/brdc/
    if (day == 0):
        doy = month
        year, month, day, cyyyy,cdoy, YMD = ydoy2useful(year,doy)
        cyy = cyyyy[2:4]
    else:
        doy,cdoy,cyyyy,cyy = ymd2doy(year,month,day)
    dir_secure = '/pub/gnss/data/daily/' + cyyyy + '/brdc/'
    bname = 'BRDC00IGS_R_' + str(year) + cdoy + '0000_01D_MN.rnx'
    filename = bname + '.gz'
    print(dir_secure, filename)
    cddis_download_2022B(filename,dir_secure)
    #cddis_download(filename,dir_secure)
    status = subprocess.call(['gunzip', filename])
    if os.path.exists(bname):
        foundit = True
        name = bname
    return name, fdir, foundit



def rinex_nrcan_highrate(station, year, month, day):
    """
    picks up 1-Hz RINEX 2.11 files from NRCAN
    requires gfzrnx or teqc

    _________________________
    parameters

    station: string
        4 character station name

    year: integer
        year

    month: integer
        month or day of year if day is set to zero

    day: integer
        day



    if day is 0, assume month slot is doy
    """
    crnxpath = hatanaka_version()
    teqcpath = teqc_version()
    gfzrnxpath = gfz_version()
    alpha='abcdefghijklmnopqrstuvwxyz'
    # if doy is input
    if day == 0:
        doy=month
        d = g.doy2ymd(year,doy);
        month = d.month; day = d.day
    doy,cdoy,cyyyy,cyy = ymd2doy(year,month,day)
    # NRCAN moving to new server names,
    gns = 'ftp://cacsa.nrcan.gc.ca/gps/data/hrdata/' +cyy + cdoy + '/' + cyy + 'd/'

    # no point downloading data if the teqc code is not there
    #if not os.path.isfile(teqcpath):
    #    print('FATAL WARNING: You need to install teqc to use gnssrefl with highrate RINEX data from NRCAN.')
    #    print('If you have time, please submit a pull request using gfzrnx instead of teqc for the file merge section.')
    #    print('gfzrnx is supported; teqc is not.')
    #    return

    foundFile = 0
    print('WARNING: downloading highrate RINEX data is a slow process')
    s1 = time.time()
    for h in range(0,24):
        # subdirectory
        ch = '{:02d}'.format(h)
        print('\n Hour: ', ch)
        for e in ['00', '15', '30', '45']:
            dname = station + cdoy + alpha[h] + e + '.' + cyy + 'd.Z'
            dname1 = station + cdoy + alpha[h] + e + '.' + cyy + 'd'
            dname2 = station + cdoy + alpha[h] + e + '.' + cyy + 'o'
            url = gns +  ch + '/' + dname
            if os.path.isfile(dname2):
                print('file exists:',dname2)
                foundFile = foundFile + 1
            else:
                print(url)
                try:
                    wget.download(url,dname)
                    subprocess.call(['uncompress',dname])
                    subprocess.call([crnxpath, dname1])
                    subprocess.call(['rm',dname1])
                    foundFile = foundFile + 1
                except:
                    okok = 1

    print('Found ', foundFile ,' individual files')
    if (foundFile == 0):
        print('Nothing to merge. Exiting.')
        return
    if (not os.path.isfile(gfzrnxpath)) and (not os.path.isfile(teqcpath)):
        print('teqc and gfzrnx are missing. I have nothing to merge these files with. Exiting')
        sys.exit()

    searchpath = station + cdoy + '*.' + cyy + 'o'
    print(searchpath)
    if os.path.isfile(gfzrnxpath) and (foundFile > 0):
        rinexname = station + cdoy + '0.' + cyy + 'o'
        print('Attempt to merge the 15 minute files using gfzrnx and move to ', rinexname)
        tmpname = station + cdoy + '0.' + cyy + 'o.tmp'
        subprocess.call([gfzrnxpath,'-finp', searchpath, '-fout', tmpname, '-vo','2','-f','-q'])
        cm = 'rm ' + station + cdoy + '*o'
        if os.path.isfile(tmpname):
            # try to remove the 15 minute files
            subprocess.call(cm,shell=True)
            subprocess.call(['mv',tmpname,rinexname])
            s2 = time.time(); print('That took ', int(s2-s1), ' seconds.')
        return

    if (os.path.isfile(teqcpath)) and (foundFile > 0):
        foutname = 'tmp.' + station + cdoy
        rinexname = station + cdoy + '0.' + cyy + 'o'
        print('Attempt to merge the 15 minute files with teqc and move to ', rinexname)

        mergecommand = [teqcpath + ' +quiet ' + station + cdoy + '*o']
        fout = open(foutname,'w')
        subprocess.call(mergecommand,stdout=fout,shell=True)
        fout.close()
        cm = 'rm ' + station + cdoy + '*o'
        if os.path.isfile(foutname):
            # try to remove the 15 minute files
            subprocess.call(cm,shell=True)
            subprocess.call(['mv',foutname,rinexname])
            s2 = time.time(); print('That took ', int(s2-s1), ' seconds.')
        return


def translate_dates(year,month,day):
    """
    input integer year month and day
    output???
    i do not think this is used
    """
    if (day == 0):
        doy=month
        d = doy2ymd(year,doy);
        month = d.month; 
        day = d.day
        doy,cdoy,cyyyy,cyy = ymd2doy(year,month,day); 
    else:
        doy,cdoy,cyyyy,cyy = ymd2doy(year,month,day); 

    return doy, cdoy, cyyyy, cyy


def bfg_password():
    """
    Picks up BFG userid and password that is stored in a pickle file
    in your REFL_CODE/Files/passwords area
    If it does not exist, it asks you to input the values and stores them for you.

    returns  
    --------
    userid : string

    password : string 

    """

    fdir = os.environ['REFL_CODE']
    if not os.path.isdir(fdir):
        print('You need to define the REFL_CODE environment variable')
        return

    # make sure the directory exists to store passwords
    if not os.path.isdir(fdir + '/Files'):
        subprocess.call(['mkdir',fdir + '/Files'])
    if not os.path.isdir(fdir + '/Files/passwords'):
        subprocess.call(['mkdir',fdir + '/Files/passwords'])

    userinfo_file = fdir + '/Files/passwords/' + 'bfg.pickle'
    #print('user information file', userinfo_file)

    #print('Will try to pick up BFG account information',userinfo_file)
    if os.path.exists(userinfo_file):
        with open(userinfo_file, 'rb') as client_info:
            login_info = pickle.load(client_info)
            user_id = login_info[0]
            passport = login_info[1]
    else:
        user_id = getpass.getpass(prompt='Userid: ', stream=None)
        passport= getpass.getpass(prompt='Password: ', stream=None)
        # save to a file
        with open(userinfo_file, 'wb') as client_info:
            pickle.dump((user_id,passport) , client_info)
        print('User id and password saved to', userinfo_file)

    return user_id, passport

def bfg_data(fstation, year, doy, samplerate=30,debug=False):
    """
    Picks up a RINEX3 file from BFG network

    Parameters: 
    -----------
    fstation: string
        4 char station ID

    year: integer
        year

    doy: integer
        day of year

    samplerate: integer
        sample rate of the receiver (default is 30)

    debug: boolean
        directory file listing provided if true
        default is false

    """
    cdoy = '{:03d}'.format(doy)
    cyyyy = str(year)

    #### these are for RINEX 3 data from the BFG network
    country_code = 'DEU'#'NLD'#country code for rinex 3 file name
    rinex_rate = '{:02d}'.format(samplerate)  + 'S'
    data_server='ftp.bafg.de' # ftp server
    rinex_dirc='/obs/' #directory on the ftp server

    user_id, passport = bfg_password()

    ftp=FTP(data_server) #log in to server
    ftp.login(user=user_id, passwd = passport)
    ftp.cwd(rinex_dirc) #change to the directory

    command=cyyyy + '/'+ cdoy +'/' #issue command to go to the folder
    #print('Looking at ', year, command, fstation,rinex_rate)
    #print(data_server+rinex_dirc + command)
    #fileid = open('bfg_listing.txt','w+')
    try:
        ftp.cwd(command) #change to that directory
        files=ftp.nlst() #list files in the directory
        for f in files:
            station = f[0:4]
            if (station == fstation.upper()) and ('crx' in f):
                if (rinex_rate in f):
                    print('downloading', f, ' and ', rinex_rate)
                    ftp.retrbinary('RETR '+f, open(f,'wb').write)
    except:
        files = []
        print('Exiting - most likely because that directory -and thus the data - does not exist.')

    if debug:
        for f in files:
            print(f)

    ftp.quit()
    return

def inout(c3gz):
    """
    Takes a Hatanaka rinex3 file that has been gzipped
    gunzips it and decompresses it 

    Parameter
    -----------
    c3gz : string
        name of a gzipped hatanaka compressed RINEX 3 filename

    Returns
    --------
    translated : boolean
        whether file was successfully translated or not 

    rnx : string
        filename of the uncompressed and de-Hatanaka'ed RINEX file

    """

    translated = False # assume failure
    c3 = c3gz[:-3] # crx filename
    rnx = c3.replace('crx','rnx') # rnx filename
    # gunzip
    if os.path.exists(c3gz):
        subprocess.call(['gunzip', c3gz])

    # executable
    crnxpath = hatanaka_version()
    if not os.path.exists(crnxpath):
        hatanaka_warning()
    else:
        if os.path.exists(c3): # file exists
            subprocess.call([crnxpath,c3])
    if os.path.exists(rnx): # file exists
        translated = True
        #print('remove Hatanaka compressed file')
        subprocess.call(['rm','-f',c3])

    return translated, rnx



def ga_highrate(station9,year,doy,dec,deleteOld=True):
    """
    parameters
    -----------
    station9 : string
        nine character station name appropriate for rinex 3
    year : integer

    doy : integer
        day of year

    dec : integer
        decimation value.  1 or 0 means no decimation

    deleteOld : boolean
        delete old rinex 3 files

    returns 
    -----
    rinex2 : string
        rinex2 filename created by merging 96 files!

    fexist : boolean
        whether a rinex2 file was successfully created

    """
    station = station9[0:4].lower()
    cyyyy = str(year)
    cyy  = cyyyy[2:4]
    cdoy = '{:03d}'.format(doy)
    crnxpath = hatanaka_version()
    gexe = gfz_version()
    if not os.path.exists(gexe):
        print('no gfzrnx executable. exiting.')
        return

    if not os.path.exists(crnxpath):
        hatanaka_warning()
        return
    print('WARNING 1: Have some coffee, downloading 96 files of high-rate GPS data takes a long time.')
    print('WARNING 2: Downloading 96 files of high-rate GPS data from Australia takes an even longer time.')
    QUERY_PARAMS, headers = k.ga_stuff_highrate(station9, year, doy)
    API_URL = 'https://data.gnss.ga.gov.au/api/rinexFiles/'
    request = requests.get(API_URL, QUERY_PARAMS, headers=headers)

    gobblygook = myfavoriteobs()
    v=0
    crate = str(dec)
    rinex2 =  station + cdoy + '0.' + cyy + 'o'
    if len(json.loads(request.content)) >= 1:
        for query_response_item in json.loads(request.content):
            file_url = query_response_item['fileLocation']
            file_name = urlparse(file_url).path.rsplit('/', 1)[1]
            newname = file_name[:-3]
            rinexname = newname[:-3] + 'rnx'
            v = v + 1
            cv = '{:02d}'.format(v)
            tmpname=  'tmp' + cv + '.' + station + cdoy + '0.'  + cyy + 'o'
            # if you ran the program previously and have the files online
            if os.path.exists(rinexname):
                print(cv, file_name, tmpname)
                if (dec > 1):
                    subprocess.call([gexe,'-finp', rinexname, '-fout', rinex2, '-vo','2','-ot', gobblygook, '-sei','out','-smp', crate, '-f','-q'])
                else:
                    subprocess.call([gexe,'-finp', rinexname, '-fout', rinex2, '-vo','2','-ot', gobblygook, '-sei','out','-f','-q'])
                subprocess.call(['mv', rinex2,tmpname])
            else:
                if os.path.exists(file_name): # file exists
                    print('file exists so gunzip it')
                    subprocess.call(['gunzip', file_name])
                else:
                    # download and gunzip it
                    print(cv, file_name)
                    wget.download(file_url,file_name)
                    subprocess.call(['gunzip', file_name])

                # hatanaka uncompress it
                if os.path.exists(newname):
                    subprocess.call([crnxpath, newname])

                if os.path.exists(rinexname):
                    if (dec > 1):
                        subprocess.call([gexe,'-finp', rinexname, '-fout', rinex2, '-vo','2','-ot', gobblygook, '-sei','out','-smp', crate, '-f','-q'])
                    else:
                        subprocess.call([gexe,'-finp', rinexname, '-fout', rinex2, '-vo','2','-ot', gobblygook, '-sei','out','-f','-q'])
                    subprocess.call(['mv', rinex2,tmpname])

# now merge them
    searchpath = 'tmp' + '*' + station + cdoy + '0.' + cyy + 'o'
    subprocess.call([gexe,'-finp', searchpath, '-fout', rinex2, '-vo','2','-f'])
    fexist = False
    if os.path.exists(rinex2):
        fexist = True

# remove detritus
    searchpath = 'tmp*' + station + cdoy + '0.' + cyy + 'o'
    cm ='rm -f ' + searchpath
    subprocess.call(cm,shell=True)
    if deleteOld:
        searchpath = station9.upper()  + '*' + cyyyy + cdoy + '*rnx'
        cm ='rm -f ' + searchpath
        subprocess.call(cm,shell=True)
        searchpath = station9.upper()  + '*' + cyyyy + cdoy + '*crx'
        cm ='rm -f ' + searchpath
        subprocess.call(cm,shell=True)
    return rinex2, fexist


def cddis_download_2022(filename,url):
    """
https://cddis.nasa.gov/Data_and_Derived_Products/CDDIS_Archive_Access.html

this does not seem to work
    """
# Reads the URL from the command line argument

# Makes request of URL, stores response in variable r
    r = requests.get(url,timeout=2)

# Opens a local file of same name as remote file for writing to
    with open(filename, 'wb') as fd:
        for chunk in r.iter_content(chunk_size=1000):
            fd.write(chunk)

# Closes local file
    fd.close()


def cddis_download_2022B(filename,directory):
    """
    rewrote because cddis_download was failing
    parameter:

    filename : string
        name of the rinex file or orbit file

    directory : string
        where the file lives at CDDIS

    """
    ftps = FTP_TLS(host = 'gdc.cddis.eosdis.nasa.gov')
    email = 'kristine.larson@colorado.edu'
    ftps.login(user='anonymous', passwd=email)
    ftps.prot_p()
    ftps.cwd(directory)
    ftps.retrbinary("RETR " + filename, open(filename, 'wb').write)
    siz = os.path.getsize(filename)
    # i do not think this is ever seen...
    if siz == 0:
        print('No file found')
        subprocess.call(['rm',filename])



def getnavfile_archive(year, month, day, archive):
    """
    picks up nav file and stores it in the ORBITS directory

    parameters
    -----------
    year: integer

    month: integer
        if day is zero, the month value is really the day of year

    day: integer
        day

    archive : string 
        name of the GNSS archive

    returns
    ----------
    navname : string
        name of navigation file

    navdir : string
        location of where the file should be stored

    foundit : boolean
        whether the file was found

    """
    foundit = False
    ann = make_nav_dirs(year)
    if (day == 0):
        doy = month
        year, month, day, cyyyy,cdoy, YMD = ydoy2useful(year,doy)
        cyy = cyyyy[2:4]
    else:
        doy,cdoy,cyyyy,cyy = ymd2doy(year,month,day)

    navname,navdir = nav_name(year, month, day)
    nfile = navdir + '/' + navname
    if not os.path.exists(navdir):
        subprocess.call(['mkdir',navdir])
    print('Looking for ', navname, navdir)

    if os.path.exists(nfile):
        foundit = True
    if (not foundit) and (os.path.exists(nfile + '.xz' )):
        subprocess.call(['unxz',nfile + '.xz'])
        foundit = True
    if (not foundit) and (os.path.exists(nfile + '.gz' )):
        subprocess.call(['gunzip',nfile + '.gz'])
        foundit = True

    if not os.path.exists(nfile):
        if (archive == 'esa'):
            navstatus=get_esa_navfile(cyyyy,cdoy)
        if (archive == 'sopac'):
            get_sopac_navfile(navname,cyyyy,cyy,cdoy)

        if os.path.exists(nfile):
            subprocess.call(['mv',navname, navdir])
            foundit = True
        else:
            print('No navfile found at ', archive)

    return navname,navdir,foundit

