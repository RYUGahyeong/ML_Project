import root
import json
import h5py
import glob
import time
import numpy as np
import pandas as pd
import netCDF4 as nc
import geopandas as gpd
from shapely import wkt
from netCDF4 import num2date
from original_data_cleaning import weather, last_fm


with open(root.get_path('config'), 'r') as config_file:
    config = json.load(config_file)


class files:
    def __init__(self):
        # 데이터 저장 위치
        self.country_path = root.get_path('country') # 국가
        self.genre_streams_path = root.get_path('genre_streams_by_country') # 국가, 장르 별 청취수
        self.weather_path = root.get_path('weather') # 수집된 날짜, 도시별 날씨 데이터
        self.last_fm_path = root.get_path('last_fm') # 국가별 음악 취향 찾기
        self.state_path = root.get_path('state') # 지리 데이터
        self.city_path = root.get_path('city')  # 지리 데이터

        # nc 파일 컬럼
        self.nc_cols = ['Rainf', 'Snowf', 'PSurf', 'Qair', 'Tair', 'Wind']
        
        # original 파일 저장 경로
        self.nc_path = {  # nc 파일 위치 패턴
            'Rainf': root.get_path('nc_rainfall_pattern'),
            'Snowf': root.get_path('nc_snowfall_pattern'),
            'PSurf': root.get_path('nc_air_pressure_pattern'),
            'Qair': root.get_path('nc_humidity_pattern'),
            'Tair': root.get_path('nc_temperature_pattern'),
            'Wind': root.get_path('nc_wind_pattern')
        }
        self.h5py_path = { # h5py 파일 저장 패턴
            'Rainf': root.get_path('h5py_rainf_pattern'),
            'Snowf': root.get_path('h5py_snowf_pattern'),
            'PSurf': root.get_path('h5py_air_pressure_pattern'),
            'Qair': root.get_path('h5py_humidity_pattern'),
            'Tair': root.get_path('h5py_temperature_pattern'),
            'Wind': root.get_path('h5py_wind_pattern')
        }        
        self.shp_path = { # 지리 정보 shp 파일 경로
            'country': root.get_path('natural_country'),  # 국가 코드, 도시명
            'city': root.get_path('natural_city'),  # 도시명, 행정 경계, 인구수
            'state': root.get_path('natural_state')
        }

    ''' ----------------------------------------- 국가별 음악 취향 LAST_FM 데이터 저장 ----------------------------------------- '''

    def last_fm(self):
        data = last_fm().get_data()
        rows = []
        for name, tags in data.items():
            for tag in tags:
                rows.append([name, tag])
        df_last_fm = pd.DataFrame(rows, columns=['COUNTRY_NAME', 'TAG'])
        df_last_fm.to_csv(self.last_fm_path, index=False)

    ''' ----------------------------------------- shp -> csv 지리 데이터 저장 ----------------------------------------- '''

    def geo_info(self):
        country = pd.read_csv(self.country_path)
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
        city = city[['CITY', 'DISTRICT', 'POPULATION', 'POINT']].drop_duplicates().dropna()

        state['GEOMETRY'] = state['GEOMETRY'].apply(lambda x: wkt.dumps(x))
        state.to_csv(self.state_path, index=False)
        city.to_csv(self.city_path, index=False)

    ''' ----------------------------------------- nc -> h5 파일로 2019년도 날씨 데이터 저장 ----------------------------------------- '''

    def nc_to_h5py(self):
        city = pd.read_csv(root.get_path('city'))
        points = city['POINT'].apply(lambda x: wkt.loads(x))  # WKT 문자열을 공간 데이터 객체로 변환

        # 경도와 위도의 최소값과 최대값
        min_lon, max_lon = points.apply(lambda x: x.x).min(), points.apply(lambda x: x.x).max()
        min_lat, max_lat = points.apply(lambda x: x.y).min(), points.apply(lambda x: x.y).max()

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
                indices_2019  = [idx for idx, date in enumerate(dates) if date.year == 2019]
                if not indices_2019 :
                    continue  # 2019년 데이터가 없으면 다음 파일로

                # 위도와 경도 범위에 맞는 인덱스 필터링
                lat_indices = np.nonzero((latitudes >= min_lat) & (latitudes <= max_lat))[0]
                lon_indices = np.nonzero((longitudes >= min_lon) & (longitudes <= max_lon))[0]

                latitudes_2019 = latitudes[lat_indices]
                longitudes_2019 = longitudes[lon_indices]
                times_2019 = np.array([int(time.mktime(dates[idx].timetuple())) for idx in indices_2019])  # 유닉스 타임스탬프로 변환
                data_column_2019 = data_column[np.ix_(indices_2019, lat_indices, lon_indices)]

                dataset.close()

                # HDF5 파일 생성
                with h5py.File(f'{self.h5py_path[col]}{i + 1}.h5', 'w') as hdf:
                    # 데이터셋 생성
                    hdf.create_dataset('lat', data=latitudes_2019)
                    hdf.create_dataset('lon', data=longitudes_2019)
                    hdf.create_dataset('time', data=times_2019)
                    hdf.create_dataset(col, data=data_column_2019)

    ''' ----------------------------------------- 날씨 데이터 저장 ----------------------------------------- '''

    def weather(self):
        weather_dataframe = weather().get()
        weather_dataframe.to_csv(self.weather_path, index=False)