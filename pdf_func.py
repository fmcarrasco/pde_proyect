import os
import glob
import pyodbc
import numpy as np
import pandas as pd
import datetime as dt

import matplotlib.pyplot as plt


def get_sql_string(tvari, tipo, idestacion):
    """
    This function generate the string to get data from the
    database of ORA (ora.mdb)
    """
    SQL_q2 = ''
    if tvari == 'precip':
        SQL_q1 = '''
            SELECT Fecha, Precipitacion FROM DatoDiario
            WHERE Estacion = {}
            AND (((DatoDiario.Fecha)>#1/1/1999#))
            AND (((DatoDiario.Fecha)<#12/31/2010#))
            '''.format(idestacion)
        print('Hay que programar')
    elif tvari == 'tmin':
        if tipo == 'SMN':
            SQL_q1 = '''
                SELECT Fecha, Tmin FROM DatoDiarioSMN
                WHERE Estacion = {}
                AND (((DatoDiarioSMN.Fecha)>#1/1/1999#))
                AND (((DatoDiarioSMN.Fecha)<#12/31/2010#))
                '''.format(idestacion)
    elif tvari == 'tmax':
        if tipo == 'SMN':
            SQL_q1 = '''
                SELECT Fecha, Tmax FROM DatoDiarioSMN
                WHERE Estacion = {}
                AND (((DatoDiarioSMN.Fecha)>=#1/1/1999#))
                AND (((DatoDiarioSMN.Fecha)<=#12/31/2010#))
                '''.format(idestacion)
    elif tvari == 'wnd10m':
        if tipo == 'SMN':
            SQL_q1 = '''
                SELECT Fecha, Viento FROM DatoDiarioSMN
                WHERE Estacion = {}
                AND (((DatoDiarioSMN.Fecha)>=#1/1/1999#))
                AND (((DatoDiarioSMN.Fecha)<=#12/31/2007#))
                '''.format(idestacion)
            SQL_q2 = '''
                SELECT Fecha, Hora, Viento FROM MedicionHorariaSMN
                WHERE Estacion = {}
                AND (((MedicionHorariaSMN.Fecha)>=#1/1/2008#))
                AND (((MedicionHorariaSMN.Fecha)<=#12/31/2010#))
                '''.format(idestacion)

    # ## End of SQL string to select data
    return SQL_q1, SQL_q2

def get_DF_wind(inp_dic):
    """
    Since wind in ora database has difference since 2007
    a function is programmed to calculate historical
    daily values
    """
    drv = '{Microsoft Access Driver (*.mdb, *.accdb)}'
    pwd = 'pw'
    cnxn = pyodbc.connect(
    'DRIVER={};DBQ={};PWD={}'.format(drv, inp_dic['dbf'], pwd))
    SQL_s1, SQL_s2 = get_sql_string(inp_dic['var'], inp_dic['t_estac'],
                                    str(inp_dic['iest']))
    df1 = pd.read_sql_query(SQL_s1, cnxn)
    df2 = pd.read_sql_query(SQL_s2, cnxn)
    df2['H'] = df2['Hora'].apply(lambda x: '{0:0>2}'.format(x))
    df2['D'] = pd.to_datetime(df2['Fecha'].dt.date.astype(str) +\
                              ' ' + df2['H'].astype(str),
                              format='%Y-%m-%d %H')
    df2['D_UTC'] = df2['D'].dt.tz_localize('UTC')
    df2['D_LOCAL'] = df2['D_UTC'].dt.tz_convert('America/Argentina/Buenos_Aires')
    df3 = df2.groupby([df2['D_LOCAL'].dt.date])['Viento'].mean()
    df3 = df3.iloc[1::]
    aux = {'Fecha': df3.index, 'Viento':df3.values}
    df4 = pd.DataFrame(index=np.arange(0, len(df3)), columns=['Fecha','Viento'],
                       data=aux)
    df1['Fecha'] = df1['Fecha'].dt.strftime('%Y-%m-%d')
    frame = pd.concat([df1, df4], axis=0, ignore_index=True)
    # #######################################
    # REVISAR FORMATO de FECHAS df4!!!!!
    # #######################################
    return frame


def calc_percentil(muestra):
    """
    Calculate from 1 to 99 percentiles using the data
    in muestra. muestra must be an numpy array
    """
    percentiles = []
    for p in range(1, 100):
        percentiles.append(np.nanpercentile(muestra, p))

    return percentiles


def save_tabla_percentil(in_di, matdata):
    """
    Use matdata as the data with percetiles for each month,
    colected from three months around the one studied.
    This function generates a Pandas DataFrame and save it
    as a CSV.

    """
    columnas = ['Prct', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul',
                'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    tabla_percentil = pd.DataFrame(data=matdata, columns=columnas)
    f_name = in_di['outfo'] + in_di['estacion'] + '/percentiles_' +\
             in_di['type'] + '_' + in_di['var'] + '.txt'
    tabla_percentil.apply(pd.to_numeric, errors='ignore')
    tabla_percentil.to_csv(f_name, sep=';', decimal=',', float_format='%.2f')


def calc_pdf_CFS(in_di):
    """
    This function reads CSV generated by grib_func.py functions, that extracts
    the value of the variable for an ensemble of 4 members. The dictionary must
    contain at least the folder where the general output is, the name of the
    station and the variable to work.
    """
    # Check if keys are in input dictionary
    if all(llaves in in_di for llaves in ['outfo', 'estacion', 'var']):
        nfile = in_di['outfo'] + in_di['estacion'] +\
                '/data_final_' + in_di['var'] + '.txt'
        df = pd.read_csv(nfile, sep=';', decimal=',', index_col=0, header=0)
        ncol = in_di['var'] + '_00'
        col = df.loc[:, ncol::]
        if in_di['var'] == 'tmax' or in_di['var'] == 'tmin':
            df['ens_mean'] = col.mean(axis=1) - 273.
        else:
            df['ens_mean'] = col.mean(axis=1)
        # ---------------------------
        df['fecha'] = pd.to_datetime(df['fecha'], format='%Y-%m-%d')
        df['month'] = pd.DatetimeIndex(df['fecha']).month
        fmat = np.empty((99, 13))
        fmat.fill(np.nan)
        fmat[:, 0] = np.arange(1, 100)
        for mes in range(1, 13):
            if mes - 1 <= 0:
                cnd = [12, 1, 2]
            elif mes + 1 >= 13:
                cnd = [11, 12, 1]
            else:
                cnd = [mes - 1, mes, mes + 1]
            datos = df[df['month'].isin(cnd)]
            # ecdf = ECDF(datos.ens_mean.values)
            prc = calc_percentil(datos.ens_mean.values)
            fmat[:, mes] = prc
        save_tabla_percentil(in_di, fmat)

    else:
        print('No estan todos los input en el diccionario de entrada')
        exit()


def calc_pdf_OBS(in_di):
    """
    This function reads database of ORA (ora.mdb), that extracts
    the value of the variable for specified station and variable.
    The dictionary must contain at least the folder where the db is,
    the idestacion (that is in ora.mdb) and the variable to work.
    """
    drv = '{Microsoft Access Driver (*.mdb, *.accdb)}'
    pwd = 'pw'
    if in_di['var'] == 'wnd10m':
        print('Programando')
        df = get_DF_wind(in_di)
        df['Viento'] = df['Viento'] * (1./3.6)
    else:
        cnxn = pyodbc.connect('DRIVER={};DBQ={};PWD={}'.format(drv,
                                                           in_di['dbf'], pwd))
        SQL_q, SQL_extra = get_sql_string(in_di['var'], in_di['t_estac'], str(in_di['iest']))
        df = pd.read_sql_query(SQL_q, cnxn)
        cnxn.close()
    df.columns = ['fecha', 'variable']
    df['fecha'] = pd.to_datetime(df['fecha'], format='%Y-%m-%d')
    df['month'] = pd.DatetimeIndex(df['fecha']).month
    fmat = np.empty((99, 13))
    fmat.fill(np.nan)
    fmat[:, 0] = np.arange(1, 100)
    for mes in range(1, 13):
        if mes - 1 <= 0:
            cnd = [12, 1, 2]
        elif mes + 1 >= 13:
            cnd = [11, 12, 1]
        else:
            cnd = [mes - 1, mes, mes + 1]
        datos = df[df['month'].isin(cnd)]
        prc = calc_percentil(datos.variable.values)
        fmat[:, mes] = prc
    save_tabla_percentil(in_di, fmat)
    # Devolvemos el total de datos historicos
    return df[['fecha', 'variable']]


if __name__ == '__main__':
    of = '../pde_salidas/'
    estac = 'resistencia'
    vari = 'wnd10m'
    typo = 'CFS'
    dic0 = {'outfo': of, 'estacion': estac, 'var':vari, 'type': typo}
    calc_pdf_CFS(dic0)

    db = 'c:/Felix/ORA/base_datos/BaseNueva/ora.mdb'
    idest = 107  # Resistencia
    vari = 'wnd10m'
    typo = 'OBS'
    dic1 = {'outfo': of, 'estacion': estac, 'dbf': db,
            'iest': idest, 't_estac': 'SMN', 'var': vari, 'type':typo}
    calc_pdf_OBS(dic1)
