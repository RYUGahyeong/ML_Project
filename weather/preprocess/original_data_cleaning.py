import root
import json
import glob
import requests
import numpy as np
import xarray as xr
import pandas as pd
import geopandas as gpd
from shapely import wkt
from sklearn.neighbors import KNeighborsClassifier


with open(root.get_path('config'), 'r') as config_file:
    config = json.load(config_file)


''' =========================================== 날씨 =========================================== '''
class weather:
    def __init__(self):
        self.h5_cols = ['Rainf', 'Snowf', 'PSurf', 'Qair', 'Tair', 'Wind']
        self.h5_pattern = {
            'Rainf': f"{root.get_path('h5py_rainf_pattern')}*.h5",
            'Snowf': f"{root.get_path('h5py_snowf_pattern')}*.h5",
            'PSurf': f"{root.get_path('h5py_air_pressure_pattern')}*.h5",
            'Qair': f"{root.get_path('h5py_humidity_pattern')}*.h5",
            'Tair': f"{root.get_path('h5py_temperature_pattern')}*.h5",
            'Wind': f"{root.get_path('h5py_wind_pattern')}*.h5"
        }
        self.change_columns = {
            'Rainf': 'RAINFALL',
            'Snowf': 'SNOWFALL',
            'PSurf': 'AIR_PRESSURE',
            'Qair': 'HUMIDITY',
            'Tair': 'TEMPERATURE',
            'Wind': 'WIND_SPEED'
        }

        # 국가 코드, 경계면 포함
        self.state = pd.read_csv(root.get_path('state'))
        self.state['GEOMETRY'] = self.state['GEOMETRY'].apply(lambda x: wkt.loads(x)) # WKT 문자열을 공간 데이터 객체로 변환
        self.state = gpd.GeoDataFrame(self.state, geometry='GEOMETRY')

    ''' ----------------------------------------- 날씨 전체 데이터 return ----------------------------------------- '''
    def get(self):
        dataframes = []

        for col in self.h5_cols:
            dataframe = pd.DataFrame()
            files = glob.glob(self.h5_pattern[col])

            for file in files:
                print(file)
                df = self.__partial_weather(path=file, col=col).rename(columns={'time': 'TIME', 'lat': 'LAT', 'lng': 'LNG'})
                df = self.time_group(df).dropna()
                dataframe = pd.concat([dataframe, df], ignore_index=True)
            dataframes.append(dataframe)

        merged_df = None

        for df in dataframes:
            df = df.groupby(['DATE', 'TIME_GROUP', 'LAT', 'LNG'], as_index=False).mean().reset_index(drop=True)
            if merged_df is None:
                merged_df = df
            else:
                merged_df = pd.merge(merged_df, df, on=['DATE', 'TIME_GROUP', 'LAT', 'LNG'], how='inner', validate="one_to_one")

        merged_df = (
            self.near_city(merged_df).groupby(['DATE', 'TIME_GROUP', 'CITY'], as_index=False).mean()
            .reset_index(drop=True)
        )
        merged_df.rename(columns=self.change_columns, inplace=True)

        selected_columns = ['DATE', 'TIME_GROUP', 'CITY'] + [col.upper() for col in self.change_columns.values()]
        merged_df = merged_df[selected_columns]

        # 상대습도 계산
        def calculate_relative_humidity(row):
            kelvin = row['TEMPERATURE'] # 온도(K)
            q = row['HUMIDITY'] # 비습(kg/kg)
            P = row['AIR_PRESSURE'] # 기압(Pa)
            celsius = kelvin - 273.15 # 섭씨 온도로 변환
            e_s = 6.112 * np.exp((17.67 * celsius) / (celsius + 243.5)) * 100 # 포화 수증기압 계산 (Pa)
            q_s = 0.622 * e_s / (P - e_s) # 포화 비습 계산 (kg/kg)            
            RH = (q / q_s) * 100 # 상대습도 계산 (%)

            if RH > 100: # 이상치 제거
                return None
            return RH # 상대습도(%)

        merged_df['HUMIDITY'] = merged_df.apply(lambda row:calculate_relative_humidity(row), axis=1)
        return merged_df.dropna()

    ''' **----------------- 파일 별 (강수량, 강설량 등) -----------------** '''
    def __partial_weather(self, **kwargs):
        """
        path: h5 파일 경로
        col: 선택 파일 컬럼
        :return: ['time', 'lat', 'lng', col] DataFrame
        """
        path = kwargs.get('path')
        col = kwargs.get('col')

        ds = xr.open_dataset(path, engine='netcdf4')
        select = ds[['time', 'lat', 'lon', col]]
        df = select.to_dataframe().reset_index(drop=True).rename(columns={'lon': 'lng'})
        df = df.astype({'lat': 'float32', 'lng': 'float32'})
        df['time'] = pd.to_datetime(df['time'], unit='s').dt.tz_localize('UTC')
        df = df[df['time'].dt.year == 2019]

        return df.groupby(['time', 'lat', 'lng'], as_index=False).mean().reset_index(drop=True)

    ''' **----------------- 시간별로 합치기 -----------------** '''
    def time_group(self, df):
        bins = [-1, 6, 12, 18, 24]
        labels = ['0-6', '6-12', '12-18', '18-24']
        df['DATE'] = df['TIME'].dt.date
        df['TIME_GROUP'] = pd.cut(df['TIME'].dt.hour, bins=bins, labels=labels, right=True)
        df.drop(columns=['TIME'], inplace=True)
        return df.groupby(['DATE', 'TIME_GROUP', 'LAT', 'LNG'], as_index=False).mean().reset_index(drop=True)

    ''' **----------------- 가까운 도시 찾기 -----------------** '''
    def near_city(self, df):
        """
        weather: 날씨 데이터 dataframe
        return: 날씨 데이터 dataframe 필터링 + 도시
        """
        df = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df['LNG'], df['LAT']))
        df = gpd.sjoin(df, self.state, how="left", predicate="within")

        city = pd.read_csv(root.get_path('city'))
        city['POINT'] = city['POINT'].apply(lambda x: wkt.loads(x))

        temp = []  # 결과를 저장할 리스트 초기화

        for district, group in df.groupby('DISTRICT'):
            selected = city[city['DISTRICT'] == district]
            if selected.empty or district is None:
                continue
            X = np.array([[point.x, point.y] for point in selected['POINT']])
            y = selected['CITY'].values

            knn = KNeighborsClassifier(n_neighbors=1)
            knn.fit(X, y)
            new_point = np.array([[point.x, point.y] for point in group['geometry']])
            group['CITY'] = knn.predict(new_point)
            group.drop(columns=['geometry', 'DISTRICT', 'COUNTRY_CODE'], inplace=True)
            group = group.groupby(['DATE', 'TIME_GROUP', 'CITY'], as_index=False).mean().reset_index(drop=True)
            temp.append(group)

        return pd.concat(temp).dropna()


''' =========================================== 음악 취향 =========================================== '''
class last_fm:  # Last.fm API
    def __init__(self, **kwargs):
        self.api_key = config['lastfm_key']

    ''' ----------------------------------------- 유럽 국가 TAG + 한국(KOR) 태그 ----------------------------------------- '''
    def get_data(self):
        data = {}
        euros = pd.read_csv(root.get_path('country'))['COUNTRY_NAME']
        euros = pd.concat([euros, pd.Series(['Korea, Republic of'])], ignore_index=True)
        for name in euros:
            data[name] = self.__get_country_tags(name)
        return data

    ''' **----------------- 특정 국가 장르 태그 -----------------** '''
    def __get_country_tags(self, country):
        top_tracks = self.__get_top_tracks_by_country(country)
        genre_tags = []

        for track in top_tracks:
            track_name = track['name']
            artist_name = track['artist']['name']
            genre_tags.extend(self.__get_track_genre_tags(track_name, artist_name))

        return genre_tags

    ''' **----------------- 특정 국가 인기 트랙 -----------------** '''
    def __get_top_tracks_by_country(self, country):
        url = "http://ws.audioscrobbler.com/2.0/"
        params = {
            'method': 'geo.gettoptracks',
            'country': country,
            'api_key': self.api_key,
            'format': 'json',
            'limit': 1
        }
        response = requests.get(url, params=params)
        return response.json()['tracks']['track']

    ''' **----------------- 트랙의 장르 태그들 -----------------** '''
    def __get_track_genre_tags(self, track, artist):
        url = "http://ws.audioscrobbler.com/2.0/"
        params = {
            'method': 'track.gettoptags',
            'track': track,
            'artist': artist,
            'api_key': self.api_key,
            'format': 'json'
        }
        response = requests.get(url, params=params)
        tags = response.json().get('toptags', {}).get('tag', [])
        return [tag['name'] for tag in tags]
