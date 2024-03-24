import root
import json
import h5py
import glob
import time
import pandas as pd
import netCDF4 as nc
import geopandas as gpd
from shapely import wkt
from netCDF4 import num2date
from original_data import weather, last_fm


with open(root.get_path('config'), 'r') as config_file:
    config = json.load(config_file)


class files:
    def __init__(self):
        # 데이터 저장 위치
        self.country_path = root.get_path('cleaned_country') # 국가
        self.genre_streams_path = root.get_path('cleaned_genre_streams_by_country') # 국가, 장르 별 청취수
        self.weather_path = root.get_path('cleaned_weather') # 수집된 날짜, 도시별 날씨 데이터
        self.last_fm_path = root.get_path('cleaned_last_fm') # 국가별 음악 취향 찾기
        self.state_path = root.get_path('cleaned_state') # 지리 데이터
        self.city_path = root.get_path('cleaned_city')  # 지리 데이터

        # nc 파일 컬럼
        self.nc_cols = ['Rainf', 'Snowf']
        
        # original 파일 저장 경로
        self.nc_path = {  # nc 파일 위치 패턴
            'Rainf': root.get_path('nc_rainfall_pattern'),
            'Snowf': root.get_path('nc_snowfall_pattern')
        }
        self.h5py_path = { # h5py 파일 저장 패턴
            'Rainf': root.get_path('h5py_rainf_pattern'),
            'Snowf': root.get_path('h5py_snowf_pattern')
        }        
        self.shp_path = { # 지리 정보 shp 파일 경로
            'country': root.get_path('natural_country'),  # 국가 코드, 도시명
            'city': root.get_path('natural_city'),  # 도시명, 행정 경계, 인구수
            'state': root.get_path('natural_state')
        }

        # dataframe 컬럼 이름 변경
        self.weather_change_columns = {
            'date': 'DATE',
            'city': 'CITY',
            'Rainf': 'RAINFALL',
            'Snowf': 'SNOWFALL',
            'air_pressure': 'AIR_PRESSURE',
            'air_temperature': 'AIR_TEMPERATURE',
            'relative_humidity': 'HUMIDITY',
            'wind_from_direction': 'WIND_FROM_DIRECTION',
            'wind_speed': 'WIND_SPEED'
        }
        self.genre_streams_change_columns = {
            'region': 'COUNTRY_CODE',
            'date': 'DATE',
            'streams': 'STREAMS',
            'playlist_genre': 'GENRE'
        }



    ''' ----------------------------------------- 캐글 STREAMS, GENRE 저장 ----------------------------------------- '''

    def genre_streams_by_country(self, genre_dataframe):
        genre_dataframe = genre_dataframe[['region', 'date', 'streams', 'playlist_genre']].rename(
            columns=self.genre_streams_change_columns)
        genre_dataframe.to_csv(self.genre_streams_path, index=False)

    ''' ----------------------------------------- 국가별 음악 취향 LAST_FM 데이터 저장 ----------------------------------------- '''

    def last_fm(self):
        data = last_fm().get_data()
        rows = []
        for name, tags in data.items():
            for tag in tags:
                rows.append([name, tag])
        df_last_fm = pd.DataFrame(rows, columns=['COUNTRY_NAME', 'TAG'])
        df_last_fm.to_csv(self.last_fm_path, index=False)

    ''' ----------------------------------------- 날씨 데이터 저장 ----------------------------------------- '''

    def weather(self):
        weather_dataframe = weather().get().rename(columns=self.weather_change_columns)
        weather_dataframe.to_csv(self.weather_path, index=False)

    ''' ----------------------------------------- nc -> h5 파일로 2019년도 날씨 데이터 저장 ----------------------------------------- '''

    def nc_to_h5py(self):
        for col in self.nc_cols:
            files = glob.glob(self.nc_path[col])

            for i, file in enumerate(files):

                # nc 파일 불러오기
                dataset = nc.Dataset(file, 'r')
                latitudes = dataset.variables['lat'][:]
                longitudes = dataset.variables['lon'][:]
                times = dataset.variables['time'][:]

                data_column = dataset.variables[col][:]
                time_units = dataset.variables['time'].units
                dates = num2date(times, units=time_units)

                # 2019년 데이터만 필터링
                indices = [idx for idx, date in enumerate(dates) if date.year == 2019]
                if not indices:
                    continue  # 2019년 데이터가 없으면 다음 파일로 넘어감

                latitudes_2019 = latitudes
                longitudes_2019 = longitudes
                times_2019 = [int(time.mktime(date.timetuple())) for date in dates[indices]]  # 유닉스 타임스탬프로 변환
                data_column_2019 = data_column[indices]

                dataset.close()

                # HDF5 파일 생성
                with h5py.File(f'{self.h5py_path[col]}{i + 1}.h5', 'w') as hdf:
                    # 데이터셋 생성
                    hdf.create_dataset('lat', data=latitudes_2019)
                    hdf.create_dataset('lon', data=longitudes_2019)
                    hdf.create_dataset('time', data=times_2019)
                    hdf.create_dataset(col, data=data_column_2019)

    ''' ----------------------------------------- shp -> csv 지리 데이터 저장 ----------------------------------------- '''

    def geo_info(self):
        country = pd.read_csv(self.country_path).rename(columns={'KAGGLE_CODE': 'COUNTRY_CODE'})
        state = gpd.read_file(self.shp_path['state']).rename(columns={
            'iso_a2': 'GEO_CODE', 'iso_3166_2': 'DISTRICT', 'geometry': 'GEOMETRY'
        })
        state = pd.merge(state, country, on='GEO_CODE', how="inner", validate="many_to_one")

        state = state[['COUNTRY_CODE', 'DISTRICT', 'GEOMETRY']].drop_duplicates()

        city = gpd.read_file(self.shp_path['city']).rename(columns={
            'ISO_A2': 'GEO_CODE', 'NAME': 'CITY', 'POP_MAX': 'POPULATION', 'geometry': 'POINT'
        })

        # GeoDataFrame 생성
        state_gdf = gpd.GeoDataFrame(state, geometry='GEOMETRY')
        city_gdf = gpd.GeoDataFrame(city, geometry='POINT')

        city = gpd.sjoin(city_gdf, state_gdf, how="left", predicate="within")
        city = city[['CITY', 'DISTRICT', 'POPULATION', 'POINT']].drop_duplicates()

        state['GEOMETRY'] = state['GEOMETRY'].apply(lambda x: wkt.dumps(x))
        state.to_csv(self.state_path, index=False)
        city.to_csv(self.city_path, index=False)

files().nc_to_h5py()