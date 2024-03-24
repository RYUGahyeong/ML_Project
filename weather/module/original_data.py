import root
import json
import glob
import requests
import xarray as xr
import pandas as pd
import geopandas as gpd
from shapely import wkt


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
        self.state = pd.read_csv(root.get_path('cleaned_state'))
        self.state['GEOMETRY'] = self.state['GEOMETRY'].apply(lambda x: wkt.loads(x)) # WKT 문자열을 공간 데이터 객체로 변환
        self.state = gpd.GeoDataFrame(self.state, geometry='GEOMETRY')

    ''' ----------------------------------------- 날씨 전체 데이터 return ----------------------------------------- '''

    def get(self):
        csv_df = self.csv_data()
        h5_df = self.h5_data()

        csv_df.drop(columns=['geometry'], inplace=True)
        csv_df = csv_df.groupby(['COUNTRY_CODE', 'DISTRICT', 'TIME'], as_index=False).mean().reset_index(drop=True)
        csv_df.sort_values(by=['TIME', 'COUNTRY_CODE', 'DISTRICT'], inplace=True)

        h5_df.drop(columns=['geometry'], inplace=True)
        h5_df = h5_df.groupby(['COUNTRY_CODE', 'DISTRICT', 'TIME'], as_index=False).mean().reset_index(drop=True)
        h5_df.sort_values(by=['TIME', 'COUNTRY_CODE', 'DISTRICT'], inplace=True)

        merged = pd.merge(h5_df, csv_df, on=['TIME', 'COUNTRY_CODE', 'DISTRICT'], how='outer', validate="many_to_many")

        cols = ['COUNTRY_CODE', 'DISTRICT', 'TIME', 'AIR_PRESSURE', 'AIR_TEMPERATURE', 'HUMIDITY', 'WIND_FROM_DIRECTION', 'WIND_SPEED', 'RAINFALL', 'SNOWFALL']
        dataframe = merged[cols]
        return dataframe

    ''' ----------------------------------------- 기압, 온도, 습도, 풍속, 바람 방향(북쪽 기준 각도) ----------------------------------------- '''

    def csv_data(self):
        use_cols = ['actual_time', 'air_pressure', 'air_temperature', 'relative_humidity',
                    'wind_from_direction', 'wind_speed', 'latitude', 'longitude']
        change_columns = {
            'actual_time': 'TIME', 'latitude': 'lat', 'longitude': 'lng', 'air_pressure': 'AIR_PRESSURE',
            'air_temperature': 'AIR_TEMPERATURE', 'relative_humidity': 'HUMIDITY',
            'wind_from_direction': 'WIND_FROM_DIRECTION', 'wind_speed': 'WIND_SPEED'
        }

        files = glob.glob(self.csv_files_pattern)
        concat_data = pd.DataFrame()
        for file in files:
            data = pd.read_csv(file, comment='#', usecols=use_cols).drop_duplicates(
                subset=['actual_time', 'latitude', 'longitude'], keep='first'
            ).rename(columns=change_columns)
            data['TIME'] = pd.to_datetime(data['TIME'])

            if not concat_data.empty:
                concat_data = pd.concat([concat_data, data])
            else:
                concat_data = data

        concat_data['TIME'] = concat_data['TIME'].dt.round('H') # 가까운 시간 반올림 0분 0초

        concat_data = gpd.GeoDataFrame(concat_data, geometry=gpd.points_from_xy(concat_data['lng'], concat_data['lat']))
        concat_data = gpd.sjoin(concat_data, self.state, how="inner", predicate="within")
        concat_data = concat_data.groupby(['TIME', 'COUNTRY_CODE', 'DISTRICT', 'geometry'], as_index=False).median().reset_index(drop=True)
        return concat_data[['TIME', 'COUNTRY_CODE', 'DISTRICT', 'geometry', 'AIR_PRESSURE', 'AIR_TEMPERATURE', 'HUMIDITY', 'WIND_FROM_DIRECTION', 'WIND_SPEED']]

    ''' ----------------------------------------- 강수량, 강설량 ----------------------------------------- '''

    def h5_data(self):
        dataframe_list = []

        for col in self.h5_cols:
            dataframe = pd.DataFrame()
            files = glob.glob(self.h5_pattern[col])

            for file in files:
                print(file)
                df = self.__partial_h5_data(path=file, col=col)
                dataframe = pd.concat([dataframe, df], ignore_index=True)
            dataframe_list.append(dataframe)

        merged_df = None

        for df in dataframe_list:
            df = df.groupby(['time', 'lat', 'lng'], as_index=False).mean().reset_index(drop=True)
            if merged_df is None:
                merged_df = df
            else:
                merged_df = pd.merge(merged_df, df, on=['time', 'lat', 'lng'], how='inner', validate="one_to_one")

        merged_df['time'] = merged_df['time'].dt.round('H')  # 가까운 시간 반올림 0분 0초

        merged_df.rename(columns={'time': 'TIME', 'Rainf': 'RAINFALL', 'Snowf': 'SNOWFALL'}, inplace=True)
        merged_df = gpd.GeoDataFrame(merged_df, geometry=gpd.points_from_xy(merged_df['lng'], merged_df['lat']))
        merged_df = gpd.sjoin(merged_df, self.state, how="inner", predicate="within")
        merged_df = merged_df.groupby(['TIME', 'COUNTRY_CODE', 'DISTRICT', 'geometry'], as_index=False).median().reset_index(drop=True)

        return merged_df.reset_index(drop=True)[['TIME', 'COUNTRY_CODE', 'DISTRICT', 'geometry', 'RAINFALL', 'SNOWFALL']]

    ''' **----------------------------------------- 파일 별 (강수량, 강설량) -----------------------------------------** '''

    def __partial_h5_data(self, **kwargs):
        """
        path: h5 파일 경로
        cities_gcs: (위도, 경도)
        col: 선택 파일 컬럼
        :return: dataframe
        """
        path = kwargs.get('path')
        col = kwargs.get('col')

        lat_min, lat_max = 34, 71
        lng_min, lng_max = -10, 30

        ds = xr.open_dataset(path, engine='netcdf4')
        select = ds[['time', 'lat', 'lon', col]]
        df = select.where((select['lat'] >= lat_min) & (select['lat'] <= lat_max) & (select['lon'] >= lng_min) & (select['lon'] <= lng_max), drop=True)
        df = df.to_dataframe().reset_index(drop=True).rename(columns={'lon': 'lng'})

        df['time'] = pd.to_datetime(df['time'], unit='s').dt.tz_localize('UTC')

        return df

''' =========================================== 음악 취향 =========================================== '''

class last_fm:  # Last.fm API
    def __init__(self, **kwargs):
        self.api_key = config['lastfm_key']

    ''' ----------------------------------------- 유럽 국가 TAG + 한국(KOR) 태그 ----------------------------------------- '''

    def get_data(self):
        data = {}
        euros = pd.read_csv(root.get_path('cleaned_country'))['COUNTRY_NAME']
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