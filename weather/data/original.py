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
from concurrent.futures import ProcessPoolExecutor


with open(root.get_path('config'), 'r') as config_file:
    config = json.load(config_file)

''' =========================================== 날씨 =========================================== '''


class weather:
    def __init__(self):
        self.h5_cols = ['Rainf', 'Snowf']
        self.h5_pattern = {
            'Rainf': f"{root.get_path('h5py_rainf_pattern')}*.h5",
            'Snowf': f"{root.get_path('h5py_snowf_pattern')}*.h5",
        }
        self.csv_files_pattern = root.get_path('csv_weather_pattern')

        # 국가 코드, 경계면 포함
        self.state = pd.read_csv(root.get_path('state'))
        self.state['GEOMETRY'] = self.state['GEOMETRY'].apply(lambda x: wkt.loads(x)) # WKT 문자열을 공간 데이터 객체로 변환
        self.state = gpd.GeoDataFrame(self.state, geometry='GEOMETRY')

    ''' ----------------------------------------- 날씨 전체 데이터 return ----------------------------------------- '''

    def get(self):
        csv_df = self.csv_data().groupby(['DATE', 'TIME_GROUP', 'CITY'], as_index=False).mean().reset_index(drop=True)
        h5_df = self.h5_data().groupby(['DATE', 'TIME_GROUP', 'CITY'], as_index=False).mean().reset_index(drop=True)

        merged = pd.merge(csv_df, h5_df, on=['DATE', 'TIME_GROUP', 'CITY'], how='outer', validate="one_to_one")

        cols = ['DATE', 'TIME_GROUP', 'CITY', 'AIR_PRESSURE', 'AIR_TEMPERATURE', 'HUMIDITY', 'RAINFALL', 'SNOWFALL']
        merged = merged[cols]

        return merged[merged['DATE'].apply(lambda x: x.year) == 2019].sort_values(by=['DATE', 'TIME_GROUP', 'CITY'])

    ''' **----------------------------------------- 시간별로 합치기 -----------------------------------------** '''
    def time_group(self, df):
        bins = [-1, 6, 12, 18, 24]
        labels = ['0-6', '6-12', '12-18', '18-24']
        df['DATE'] = df['TIME'].dt.date
        df['TIME_GROUP'] = pd.cut(df['TIME'].dt.hour, bins=bins, labels=labels, right=True)
        df.drop(columns=['TIME'], inplace=True)
        return df.groupby(['DATE', 'TIME_GROUP', 'LAT', 'LNG'], as_index=False).mean().reset_index(drop=True)

    ''' **----------------------------------------- 가까운 도시 찾기 -----------------------------------------** '''
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

    ''' ----------------------------------------- 기압, 온도, 습도, 풍속, 바람 방향(북쪽 기준 각도) ----------------------------------------- '''

    def csv_data(self):
        use_cols = ['actual_time', 'air_pressure', 'air_temperature', 'relative_humidity', 'latitude', 'longitude']
        change_columns = {
            'actual_time': 'TIME', 'latitude': 'LAT', 'longitude': 'LNG',
            'air_pressure': 'AIR_PRESSURE', 'air_temperature': 'AIR_TEMPERATURE',
            'relative_humidity': 'HUMIDITY'
        }

        files = glob.glob(self.csv_files_pattern)
        concat_data = pd.DataFrame()
        for file in files:
            data = pd.read_csv(file, comment='#', usecols=use_cols).rename(columns=change_columns)
            data = data.groupby(['TIME', 'LAT', 'LNG'], as_index=False).mean().reset_index(drop=True)
            data['TIME'] = pd.to_datetime(data['TIME'])
            data = data.astype({'LAT': 'float32', 'LNG': 'float32'})
            data = self.time_group(data)
            data = self.near_city(data)

            if not concat_data.empty:
                concat_data = pd.concat([concat_data, data])
            else:
                concat_data = data

        return concat_data[['DATE', 'TIME_GROUP', 'CITY', 'AIR_PRESSURE', 'AIR_TEMPERATURE', 'HUMIDITY']]

    ''' ----------------------------------------- 강수량, 강설량 ----------------------------------------- '''

    def h5_data(self):
        dataframes = []

        for col in self.h5_cols:
            dataframe = pd.DataFrame()
            files = glob.glob(self.h5_pattern[col])

            for file in files:
                print(file)
                df = self.__partial_h5_data(path=file, col=col).rename(columns={'time': 'TIME', 'lat': 'LAT', 'lng': 'LNG'})
                df = self.time_group(df).dropna()
                dataframe = pd.concat([dataframe, df], ignore_index=True)
            dataframes.append(dataframe)

        merged_df = None

        for df in dataframes:
            df = df.groupby(['DATE', 'TIME_GROUP', 'LAT', 'LNG'], as_index=False).mean().reset_index(drop=True)
            if merged_df is None:
                merged_df = df
            else:
                merged_df = pd.merge(merged_df, df, on=['DATE', 'TIME_GROUP', 'LAT', 'LNG'], how='outer', validate="one_to_one")

        merged_df = self.near_city(merged_df).groupby(['DATE', 'TIME_GROUP', 'CITY'], as_index=False).mean().reset_index(drop=True)

        merged_df.rename(columns={'Rainf': 'RAINFALL', 'Snowf': 'SNOWFALL'}, inplace=True)

        return merged_df[['DATE', 'TIME_GROUP', 'CITY', 'RAINFALL', 'SNOWFALL']]

    ''' **----------------------------------------- 파일 별 (강수량, 강설량) -----------------------------------------** '''

    def __partial_h5_data(self, **kwargs):
        """
        path: h5 파일 경로
        col: 선택 파일 컬럼
        :return: dataframe
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

    ''' **--------------------------------------- 특정 국가 장르 태그 ---------------------------------------** '''

    def __get_country_tags(self, country):
        top_tracks = self.__get_top_tracks_by_country(country)
        genre_tags = []

        for track in top_tracks:
            track_name = track['name']
            artist_name = track['artist']['name']
            genre_tags.extend(self.__get_track_genre_tags(track_name, artist_name))

        return genre_tags

    ''' **--------------------------------------- 특정 국가 인기 트랙 ---------------------------------------** '''

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

    ''' **--------------------------------------- 트랙의 장르 태그들 ---------------------------------------** '''

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


''' =============================================== 삭제 예정 ============================================= '''


# 장르 데이터와 날씨 데이터 병합
def merged_weather_genre():
    weather_data = pd.read_csv(root.get_path('kaggle_weather'))
    genre_data = pd.read_csv(root.get_path('kaggle_genre'))

    genre_data = genre_data[['track_name', 'track_artist', 'playlist_genre']]
    genre_data.drop_duplicates(subset=['track_name', 'track_artist'], keep='first', inplace=True)
    genre_data.rename(columns={'track_artist': 'artist'}, inplace=True)

    merged_data = pd.merge(weather_data, genre_data, on=['track_name', 'artist'], how='left', validate="many_to_one")

    return merged_data.drop(['const', 'spotify_id', 'month'], axis=1).dropna().reset_index(drop=True)