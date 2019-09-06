"""
09/04/2019 Creado por Felix Carrasco

This script contains functions to read, extract data from
grib2 files, contained in Pikachu database.

The datafiles correspond to 1999-2009 period of CFS data
with 120 days of forecast between 6 hours.

The project considers a forecast to 30 days.

The functions programmed in this grib_func.py 
allows to read for specific lat lon meteorological
station.
"""
import xarray as xr
import numpy as np
import pandas as pd
import datetime as dt
import glob


def extract_data_files(fname):
    """
    Extract the data from the filename. According to README in NOMADS
    the filename contains the following structure:

    <var>.<ensMem>.<yyyymmddhh t(i)>.<yyyymmddhh t(v)>.<yyyymmdd t(ic)>.grb2

    which means:

    var    : The output weather element
    t(i)   : Initialization or cycle run time.
    t(v)   : Final verification time of the series
    t(ic)  : Date/time of initial condition data used for forecast sequence.
    ensMem : Always/only 01 for this high-priority distribution.

    Each 00:00 UTC cycle contains a sequence of forecast records extended
    to approximately 2920 hours (or 4 months)
    Alternately for 06:00 / 12:00 / 18:00 UTC cycles:
    Each file contains a sequence of forecast records extending out
    to 1080 hours (45 days)
    Some fields, such as ocean, the t(ic) will differ from the t(i) by six
    hours.  in most cases, they are the same.

    """

    aux = fname.split('/')[5]  # Position of the filename
    filen = aux.split('.')
    outd = {'var':filen[0], 'ensMem':filen[1], 'ti':filen[2], 'tv':filen[3],\
            'tic':filen[4]}


    return outd
    

def gen_date_range(dfile):
    """
    Function to generate datetime index
    based on the data provided by the 
    name of the file.
    """
    yri = dfile['ti'][0:4]
    moi = dfile['ti'][4:6]
    dai = dfile['ti'][6:8]
    hri = dfile['ti'][8::]
    yrf = dfile['tv'][0:4]
    mof = dfile['tv'][4:6]
    daf = dfile['tv'][6:8]
    hrf = dfile['tv'][8::]
    strt = dt.datetime(int(yri), int(moi),
                       int(dai), int(hri),
                       0, 0)
    endt = dt.datetime(int(yrf), int(mof),
                       int(daf), int(hrf),
                       0, 0)

    f1 = pd.date_range(start=strt, end=endt, freq='6H')
    outfecha = f1[1::]

    outymd = np.array(outfecha.year*1e4 + outfecha.month*1e2 +\
                      outfecha.day, dtype=int)

    return outfecha, outymd


def gen_date_range_v2(dfile, f_td):
    """
    """
    yri = dfile['ti'][0:4]
    moi = dfile['ti'][4:6]
    dai = dfile['ti'][6:8]
    hri = dfile['ti'][8::]
    str_d = np.datetime64(yri + '-' + moi + '-' + dai + 'T' + hri + ':00')
    out_1 = [str_d + td for td in f_td]
    out_2 = [pd.Timestamp(val).to_pydatetime() for val in out_1]

    return out_2


def get_files_hr(date, dic):
    """
    Function to return the list of the files corresponding for
    date given.

    date: datetime variable
    var: Variable to extract
    folder: Base folder to retrieve the files

    <var>.<ensMem>.<yyyymmddhh t(i)>.<yyyymmddhh t(v)>.<yyyymmdd t(ic)>.grb
    """
    iv = dt.timedelta(days=1)
    d1 = (date - iv).replace(hour=18)
    d2 = date
    d3 = date.replace(hour=6)
    d4 = date.replace(hour=12)

    vr = ['pressfc', 'q2m', 'tmp2m']
    outf = {}
    for var in vr:
        for dx in [d1, d2, d3, d4]:
            wkfolder = dic['dfolder'] + var + '/' + str(dx.year) + '/'
            sd1 = dx.strftime('%Y%m%d%H')
            f1 = glob.glob(wkfolder + var + '_f.01.' + sd1 + '*.grb2')
            lfls = []
            if f1:
                lfls.append(f1[0])
        # End loop of dates
        outf[var] = lfls
    # End of LOOP

    return outf


def get_files_o(date, dic):
    """
    Function to obtain files to extract
    wmd10m, dswsfc, tmax, tmin
    In this case for these particular variables
    the idea is to get a file with prognostic
    for the four hours of the date and to work
    with those four values
    """
    lfls = []
    if date == dt.datetime(1999,1,1):
        d1 = date.replace(hour=0)
        wkfolder = dic['dfolder'] + dic['var'] + '/' + str(d1.year) + '/'
        sd1 = d1.strftime('%Y%m%d%H')
        f1 = glob.glob(wkfolder + dic['var'] + '_f.01.' + sd1 + '*grb2')
        if f1:
            lfls.append(f1[0])
    else:
        # Test all dates from previous day and all hours
        iv = dt.timedelta(days=1)
        d1 = (date - iv).replace(hour=18) # forecast from previous day at 18
        d2 = (date - iv).replace(hour=12)
        d3 = (date - iv).replace(hour=6)
        d4 = (date - iv).replace(hour=0)
        wkfolder = dic['dfolder'] + dic['var'] + '/' + str(d1.year) + '/'
        for dx in [d1, d2, d3, d4]:
            sd1 = dx.strftime('%Y%m%d%H')
            n_file = wkfolder + dic['var'] + '_f.01.' + sd1
            f1 = glob.glob(n_file + '*.grb2')
            if f1:
                lfls.append(f1[0])
    # End IF
    return lfls


def get_daily_value(files, date, dic):
    """
    From the list of files given, it extracts
    one value for the date given

    - files: List of files
    - fecha: Date to use as a value
    - dic: Dictionary containing data from var, folders, etc
    """
    if not files:
        sd = date.strftime('%Y-%m-%d')
        valores = {dic['var'] + '_00': np.nan, dic['var'] + '_06': np.nan,
                   dic['var'] + '_12': np.nan, dic['var'] + '_18': np.nan}
    else:
        valores = {dic['var'] + '_00': np.nan, dic['var'] + '_06': np.nan,
                   dic['var'] + '_12': np.nan, dic['var'] + '_18': np.nan}
        for item in files:
            d_file = extract_data_files(item)
            grbs = xr.open_dataset(item, engine='pynio')
            nvar = list(grbs.data_vars.keys())[0]
            xe = np.array(dic['lon_e']) % 360  # Pasamos de [-180, 180] a [0, 360]
            ye = dic['lat_e']
            data = grbs[nvar].sel(lon_0=xe, lat_0=ye, method='nearest')
            vec_date = gen_date_range_v2(d_file, data.coords[data.dims[0]].values)
            datos = data.values
            if dic['var'] == 'wnd10m':
                # Solo valido dado que extraemos comp U y V keys=0 o keys=1
                nvar2 = list(grbs.data_vars.keys())[1]
                data2 = grbs[nvar2].sel(lon_0=xe, lat_0=ye, method='nearest')
                vec_date2 = gen_date_range_v2(d_file, data2.coords[data2.dims[0]].values)
                aux2 = [dt.datetime(a.year, a.month, a.day) for a in vec_date2]
                idate2 = [a == date for a in aux2]
                datos2 = data2.values
                # ------------------
                nvar2 = None
                data2 = None
            # Eliminamos memoria
            grbs.close()
            grbs = None
            data = None
            # ----------
            aux = [dt.datetime(a.year, a.month, a.day) for a in vec_date]
            idate = [a == date for a in aux]
            if dic['var'] == 'tmax':
                kval = dic['var'] + '_' + d_file['ti'][8::]
                for key in valores.keys():
                    if key == kval:
                        valores[ key ] = np.max(np.array(datos[idate]))
            elif dic['var'] == 'tmin':
                kval = dic['var'] + '_' + d_file['ti'][8::]
                for key in valores.keys():
                    if key == kval:
                        valores[ key ] = np.min(np.array(datos[idate]))
            elif dic['var'] == 'wnd10m':
                kval = dic['var'] + '_' +  d_file['ti'][8::]
                for key in valores.keys():
                    if key == kval:
                        speed = np.sqrt(datos[idate]**2 + datos2[idate2]**2)
                        valores[ key ] = np.nanmean(speed)
                        vec_date2 = None

            else:
                valores[ dic['var'] + '_' + d_file['ti'][8::] ] = np.nan
            # Eliminamos memoria
            d_file = None
            vec_date = None
            # -------
        # End of LOOP

    return valores


def create_summary_file(dic, fval, fmat):
    """
    Function to create a summary file to save the results
    """

    columnas = ['fecha'] 
    columnas.extend([dic['var'] + '_' + hr for hr in ['00', '06', '12', '18']]) 
    df = pd.DataFrame(columns=columnas)
    df['fecha'] = fval
    df[columnas[1::]] = fmat

    return df


if __name__ == "__main__":
    print('Hola Main')

