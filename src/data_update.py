'''Module for updating the dashboard data, this script is to be run once a day'''
import io
import requests
import numpy as np
import pandas
import geopandas as gpd

def get_data(name):
    '''Get the data from github website and creates a pandas.DataFrame out of it.
    Parameters:
    ----------
            name (str): a name in csv_list
    Returns:
    -------
            pandas.DataFrame'''

    base_url = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/\
csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_'
    print(base_url)
    url = base_url + name + '.csv'
    content = requests.get(url).content
    dframe = pandas.read_csv(io.StringIO(content.decode('utf-8')),
                             skipinitialspace=True)
    return dframe

def create_raw():
    '''Create dataframe for all raw data.
    Parameters:
    -----------
                None
    Returns:
    --------
           a 3-uple of pandas.Dataframe consiting
           of confirmed cases, recovered cases and deaths cases.
    '''
    df_raw_confirm = get_data('confirmed_global')
    df_raw_reco = get_data('recovered_global')
    df_raw_deaths = get_data('deaths_global')

    return df_raw_confirm, df_raw_reco, df_raw_deaths

##############################################################################

def create_time(df_raw):
    '''create a pandas dataframe with a "date" column.
    The rows consist of all the dates since starts of the pandemic.
    Parameters:
    ----------
              dframe (pandas.DataFrame): a raw dataframe from github
    Returns:
    -------
              pandas.DataFrame
    '''
    time_index = df_raw.columns[4:]
    df_time = pandas.DataFrame({'date': time_index})
    time_series = pandas.to_datetime(df_time['date'], format='%m/%d/%y')
    df_time_formated = pandas.DataFrame({'date': time_series})

    return df_time_formated



#creating a dataframe for our specified countries only
def create_countries_df(df_raw_confirm, df_raw_reco, df_raw_deaths):
    '''Create 3 DataFrame for our contries of interest.
    The DataFrame are DataFrame for confirmed cases,
    recovered cases, and death cases. Columns are date and
    countries
    '''
    country_df = pandas.read_csv('../data/raw/countries.csv',
                                 sep=';',
                                 skipinitialspace=True)

    country_list = list(country_df['country'])

    df_time_formated = create_time(df_raw_confirm)
    df_confirm = df_time_formated.copy()
    df_reco = df_time_formated.copy()
    df_deaths = df_time_formated.copy()
    df_active = df_time_formated.copy()

    #creating DataFrame for confirmed, recovered, deaths, and active cases
    for country in country_list:
        df_confirm[country] = np.array(df_raw_confirm[df_raw_confirm['Country/Region'] == country].iloc[:, 4::].sum(axis=0))
        df_reco[country] = np.array(df_raw_reco[df_raw_reco['Country/Region'] == country].iloc[:, 4::].sum(axis=0))
        df_deaths[country] = np.array(df_raw_deaths[df_raw_deaths['Country/Region'] == country].iloc[:, 4::].sum(axis=0))
        df_active[country] = df_confirm[country] - df_reco[country] - df_deaths[country]

    # removing 'Comoros', 'Lesotho', 'Taiwan'
    for dframe in [df_confirm, df_reco, df_deaths, df_active]:
        dframe = dframe.drop(['Comoros', 'Lesotho', 'Taiwan'], axis=1)

    # saving the dataframe to csv
    df_confirm.to_csv('../data/raw/time_series_confirmed.csv', index=False)
    df_reco.to_csv('../data/raw/time_series_recovered.csv', index=False)
    df_deaths.to_csv('../data/raw/time_series_deaths.csv', index=False)
    df_active.to_csv('../data/raw/time_series_active.csv', index=False)

    return df_confirm, df_reco, df_deaths, df_active

#####################################################################################################
# New case per day
#####################################################################################################

def daily_rate(dframe):
    '''function computing the daily rate of increase from a DataFrame with accumulated daily cases
    Parameter:
    ----------
           df (pandas.DataFrame): data frame with first columns being "date" and the remaining columns being cases by countries.

    Returns:
    --------
        df_reco (pandas.DataFrame): data frame similar to the input but with daily new cases instead
    '''

    df_output = pandas.DataFrame()
    df_output['date'] = dframe['date']

    for country in list(dframe.columns.values[1:]):
        rate_list = [dframe[country][0]]
        for i in range(1, dframe.shape[0]):
            rate_list.append(dframe[country][i] - dframe[country][i-1])

        df_output[country] = rate_list

    return df_output

def create_rate_df(df_confirm, df_reco, df_deaths, df_active):
    ''''''

    df_daily_reco = daily_rate(df_reco)
    df_daily_deaths = daily_rate(df_deaths)
    df_daily_active = daily_rate(df_active)
    df_daily_new = daily_rate(df_confirm)

    #saving the dataframe
    df_daily_reco.to_csv('../data/raw/time_series_daily_recovered.csv', index=False)
    df_daily_deaths.to_csv('../data/raw/time_series_daily_deaths.csv', index=False)
    df_daily_active.to_csv('../data/raw/time_series_daily_active.csv', index=False)
    df_daily_new.to_csv('../data/raw/time_series_daily_new.csv', index=False)

    #return df_daily_reco, df_daily_deaths, df_daily_active, df_daily_new

############################################################################################
# Data for interactive map
############################################################################################

def spheri_merca(dframe, lon='longitude', lat='latitude'):
    '''Convert spherical coordinate in a DataFrame into mercator coordinates.
    Creates new columns: "x" and "y" coresponding to mercator coordinates.
    This function modify the input DataFrame.
    Parameters:
    -----------
            df (pandas.DataFrame): DataFrame containing "longitude" and "latitude"
                                   columns
            lon (str): name of longitude column.
            lat (str): name of latitude column.
    Returns:
    -------
            None.
    '''
    k = 6378137
    dframe['x'] = dframe[lon] * (k * np.pi/180.0)
    dframe['y'] = np.log(np.tan((90 + dframe[lat]) * np.pi/360.0))*k


def check_interval(number):
    '''Check if a number n fall in a certain interval.
    Parameters:
    ----------
                number (int): number of active cases
    Returns:
    --------
                int: integer representing the severity of the situation.
                     Will be used as radius for bokeh circle glyph in
                     the interactive map
    '''
    bounds = [0, 20, 100, 200, 300, 500, 1000, 2000, 3000, 5000, 10000, 400000]
    interval = [range(bounds[i], bounds[i+1]) for i in range(len(bounds)-1)]

    for item in interval:
        if number in item:
            return 3*(interval.index(item) + 1)
        elif number > 400000:
            return 36

#country_africa
def create_africa_df(df_confirm, df_reco, df_deaths, df_active):
    '''Creates, save (to csv) and return dataframe of our countries of interest.
    Parameters:
    ----------
            None
    Returns:
    --------
            pandas.DataFrame: dataframe containing columns: 'country', 'confirmed'
                              'active', 'recovered', 'deaths', 'severity'.
    '''
    country_africa = pandas.read_csv('../data/raw/countries_pertinent_africa.csv',
                                     skipinitialspace=True,
                                     keep_default_na=False) # prevent NA from becoming NaN

    spheri_merca(country_africa, lon='longitude', lat='latitude')

    def take_last_value(dframe):
        '''take the last value of a dataframe'''
        return [int(dframe[item][-1:]) for item in country_africa['country']]

    country_africa['confirmed'] = take_last_value(df_confirm)
    country_africa['active'] = take_last_value(df_active)
    country_africa['recovered'] = take_last_value(df_reco)
    country_africa['deaths'] = take_last_value(df_deaths)
    country_africa['severity'] = country_africa['active'].apply(check_interval)

    # save dataframe to csv
    country_africa.to_csv('../data/raw/countries_africa_data.csv', index=False)

    return country_africa

###########################################################################################################################
# Geopandas
##########################################################################################################################

# function loading the shapefile
def load_geoshape():
    ''''''
    shapefile = '../data/raw/TM_WORLD_BORDERS-0.3.shp'
    gdf = gpd.read_file(shapefile)[['NAME', 'ISO2', 'geometry']]
    gdf.columns = ['country', 'country_code', 'geometry']
    return gdf

def create_geodf(df_confirm, df_reco, df_deaths, df_active):
    ''''''
    country_africa = create_africa_df(df_confirm, df_reco, df_deaths, df_active)
    africa_iso = list(country_africa['country_code'])
    gdf = load_geoshape()

    row_to_remove = [item for item in list(gdf['country_code']) if item not in africa_iso]

    for item in row_to_remove:
        gdf = gdf[gdf.country_code != item]

    gdf.reset_index(drop=True, inplace=True)

    # Changing Congo Democratic, Tanzania and Swaziland name in gdf
    #to match the name in country_africa
    gdf_country_copy = list(gdf['country'])
    gdf_country_copy[1] = 'Congo (Kinshasa)'
    gdf_country_copy[15] = 'Tanzania'
    gdf_country_copy[18] = 'Eswatini'
    gdf['country'] = gdf_country_copy

    #sorting gdf row to match country of africa
    gdf = gdf.sort_values(by=['country'])

    # function checking if country rows in gdf and country_africa
    #are in the same order
    def check_order():
        result = []
        for a, b in zip(list(gdf['country_code']), list(country_africa['country_code'])):
            result.append(a == b)
        return result

    if all(check_order()):
        # adding country_africa  'latitude', 'longitude',
        #'confirmed', 'active', 'recovered', 'deaths',
        #'severity' columns to gdf
        pertinent_col = ['country',
                         'latitude',
                         'longitude',
                         'confirmed',
                         'active',
                         'recovered',
                         'deaths',
                         'severity']

        final_gdf = gdf.merge(country_africa[pertinent_col])
        # saving to a shapefile
        final_gdf.to_file(driver='ESRI Shapefile', filename='../data/raw/final_covid_geodata.shp')
    else:
        print('Countries ISO2 do not match when trying to merge country_africa')

############################################################################################################

if __name__ == '__main__':

    RAW_CONF, RAW_RECO, RAW_DEATHS = create_raw()

    DF_CONFIRM, DF_RECO, DF_DEATHS, DF_ACTIVE = create_countries_df(RAW_CONF,
                                                                    RAW_RECO,
                                                                    RAW_DEATHS)
    create_geodf(DF_CONFIRM, DF_RECO, DF_DEATHS, DF_ACTIVE)
    create_rate_df(DF_CONFIRM, DF_RECO, DF_DEATHS, DF_ACTIVE)
