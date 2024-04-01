import copy
import root
import itertools
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely import wkt
from sklearn.cluster import DBSCAN


class weather_cleaner:
    def __init__(self):
        """
        :param country: 국가 데이터
        :param state: 행정 경계 데이터
        :param city: 도시 데이터
        :param weather: 날씨 데이터
        :param quarter: TIME_GROUP 순서 배열
        :param time_group_order: TIME_GROUP 순서 정렬
        :param weather_cols: 날씨 관련 특성 컬럼명 목록
        :param genre_streams_by_country: 장르 데이터
        """
        # 국가 COUNTRY_CODE,GEO_CODE,COUNTRY_NAME
        self.country = pd.read_csv(root.get_path('country'))

        # 행정 경계 COUNTRY_CODE,DISTRICT,GEOMETRY
        state = pd.read_csv(root.get_path('state'))
        state['GEOMETRY'] = state['GEOMETRY'].apply(wkt.loads)
        self.state = gpd.GeoDataFrame(state, geometry='GEOMETRY')

        # 도시 CITY,DISTRICT,POPULATION,POINT
        city = pd.read_csv(root.get_path('city'))
        city['POINT'] = city['POINT'].apply(wkt.loads)
        self.city = gpd.GeoDataFrame(city, geometry='POINT')

        # 날씨 DATE,TIME_GROUP,CITY,RAINFALL,SNOWFALL,AIR_PRESSURE,HUMIDITY,TEMPERATURE,WIND_SPEED
        time_group_mapping = { '0-6': 0, '6-12': 1, '12-18': 2, '18-24': 3 }
        self.weather = pd.read_csv(root.get_path('weather'))
        self.weather['DATE'] = pd.to_datetime(self.weather['DATE'])
        self.weather['TEMPERATURE'] = self.weather['TEMPERATURE'] - 273.15  # 온도(K) => 온도(C)
        self.weather['TIME_GROUP'] = self.weather['TIME_GROUP'].map(time_group_mapping)
        self.weather = self.weather.sort_values(by=['DATE', 'CITY', 'TIME_GROUP'])

        self.weather_cols = ['RAINFALL', 'SNOWFALL', 'AIR_PRESSURE', 'HUMIDITY', 'TEMPERATURE', 'WIND_SPEED']

        # 스트리밍 COUNTRY_CODE,DATE,STREAMS,GENRE
        self.genre_streams_by_country = pd.read_csv(root.get_path('genre_streams_by_country'))
        self.genre_streams_by_country['DATE'] = pd.to_datetime(self.genre_streams_by_country['DATE'])

    ''' ----------------------------------------- return 쾨펜 분류 dict ----------------------------------------- '''
    def koppen_dfs(self, weather):
        """
        :param weather: 날씨 데이터 DataFrame
        :return: {'기후 분류코드': df[COUNTRY_CODE, DISTRICT, CITY, KOPPEN_CLASS, GEOMETRY, POINT, POPULATION]}
        """
        weather = copy.deepcopy(weather)

        # row 한줄당 kg/(m^2) 6시간 평균  | 단위 1kg/m^2 = 1mm
        weather['RAINFALL'] = weather['RAINFALL'] * 6 * 60 * 60
        weather = weather.groupby(['CITY', 'DATE'], as_index=False).agg({
            'TEMPERATURE': 'mean', 'RAINFALL': 'sum', 'WIND_SPEED': 'mean', 'AIR_PRESSURE': 'mean', 'HUMIDITY': 'mean'
        })

        result = weather.groupby('CITY', as_index=False).apply(self.__classify_by_koppen).reset_index(drop=True)
        result = pd.merge(result, self.city, on='CITY', how='inner', validate="many_to_many")
        result = pd.merge(self.state, result, on='DISTRICT', how='inner', validate="many_to_many")
        return {k: v for k, v in result.groupby('KOPPEN_CLASS')}

    ''' **----------------- 쾨펜 분류 -----------------** '''
    def __classify_by_koppen(self, df):
        """
        :param df: DataFrame with 'TEMPERATURE', 'RAINFALL', 'DATE', 'CITY'
        :return: DataFrame with 'CITY' and 'KOPPEN_CLASS'
        """
        df['MONTH'] = pd.to_datetime(df['DATE']).dt.month

        annual_rainfall = df['RAINFALL'].sum() # 1년 강수량
        monthly_rainfall = df.groupby('MONTH', as_index=False)['RAINFALL'].sum()
        dryest_rainfall = monthly_rainfall['RAINFALL'].min()
        humid_rainfall = monthly_rainfall['RAINFALL'].max()

        monthly_temp = df.groupby('MONTH', as_index=False)['TEMPERATURE'].mean()
        coldest_temp = monthly_temp['TEMPERATURE'].min()
        warmest_temp = monthly_temp['TEMPERATURE'].max()
        warm_season_length = max(
            (len(list(g)) for k, g in itertools.groupby(monthly_temp['TEMPERATURE'].tolist(), key=lambda x: x > 10) if k), default=0
        )

        # Thornthwaite 방정식을 사용한 잠재 증발산량(PET) 추정
        temp = np.maximum(df['TEMPERATURE'].values, 0)
        heat_index = np.sum((temp / 5) ** 1.514)  # 연간 열 지수
        a = (6.75e-7) * heat_index ** 3 - (7.71e-5) * heat_index ** 2 + (1.792e-2) * heat_index + 0.49239  # 계수
        pet = (16 * ((10 * temp / heat_index) ** a)).sum()  # 연간 PET 계산

        # A(열대) 기후
        if (monthly_temp['TEMPERATURE'] >= 18).all():
            koppen_class = 'A'
        # B(건조) 기후
        elif annual_rainfall < pet:
            koppen_class = 'B'
        # C(온대) 기후
        elif 0 <= coldest_temp <= 18:
            if warmest_temp <= 22 and coldest_temp >= 0:
                koppen_class = 'Cfb' if dryest_rainfall/humid_rainfall > 0.1 else 'Cwb'
            else:
                koppen_class = 'Cfa' if dryest_rainfall/humid_rainfall > 0.1 else 'Cwa'
        # D(냉대) 기후
        elif coldest_temp <= -3 and warmest_temp >= 10:
            if monthly_rainfall['RAINFALL'].mean() > 0:
                koppen_class = 'Dfa' if warm_season_length >= 4 else 'Dfb'
            else:
                koppen_class = 'Dfc' if dryest_rainfall >= 30 else 'Dfd'
        elif warm_season_length >= 1 and dryest_rainfall < 30:
            koppen_class = 'Dwc' if warm_season_length >= 4 else 'Dwd'
        # E(한대) 기후
        else:
            koppen_class = 'E'

        df['KOPPEN_CLASS'] = koppen_class

        return df[['CITY', 'KOPPEN_CLASS']].drop_duplicates()

    ''' ----------------------------------------- 해외자치구 및 기후 퍼센트에 따라 날씨 데이터 선택 ----------------------------------------- '''
    def select_weather(self, **kwargs):
        """
        :param original_koppen_dfs: 쾨펜 기본 분류 데이터
        :return: 해외 자치구 및 기후 퍼센트가 낮은 국가 날씨 데이터 DataFrame
        """
        original_koppen_dfs = kwargs.get('original_koppen_dfs')

        include_keys = ['Cwa', 'Cfa', 'Dwd', 'Dfa']

        # 기후 퍼센트
        selected_df = pd.concat(original_koppen_dfs.values())

        koppen_percent = (
            selected_df.groupby('COUNTRY_CODE')['KOPPEN_CLASS']
            .value_counts(normalize=True)
            .rename('PERCENT').reset_index()
        )

        koppen_summary = koppen_percent[koppen_percent['KOPPEN_CLASS'].isin(include_keys)]
        grouped_summary = koppen_summary.groupby('COUNTRY_CODE')['PERCENT'].sum()

        # 50% 이상인 국가만
        select_countries = grouped_summary[grouped_summary > 0.5].index.tolist()

        # 해외 자치구 있는 국가 제거
        geo_all = (
            self.country[self.country['COUNTRY_CODE'].isin(select_countries)]
            .merge(self.state, on='COUNTRY_CODE')
            .merge(self.city, on='DISTRICT')
        )
        country_dict = {k: v for k, v in geo_all.groupby('COUNTRY_CODE')}

        exclude_countries = []

        for country, geo_country in country_dict.items():
            coords = np.array([[point.x, point.y] for point in geo_country['POINT']])
            db = DBSCAN(eps=15, min_samples=1).fit(coords)
            if len(np.unique(db.labels_)) > 1:  # 2개 이상 라벨은 해외 자치구가 있다고 판단
                exclude_countries.append(country)

        geo_all = geo_all[~geo_all['COUNTRY_CODE'].isin(exclude_countries)]

        return self.weather[self.weather['CITY'].isin(geo_all['CITY'])]

