import root
import json
import pandas as pd
import mysql.connector
from original_data import weather, last_fm
from sqlalchemy import create_engine

with open(root.get_path('config'), 'r') as config_file:
    config = json.load(config_file)

mysql_config = {
            'host': config['mysql_host'],
            'user': config['mysql_user'],
            'port': config['mysql_port'],
            'password': config['mysql_password'],
            'database': config['mysql_database']
        }

# mysql 연결 with 문 사용
class connect:
    def __init__(self):
        self.conn = None
        self.cursor = None

    def __enter__(self):
        self.conn = mysql.connector.connect(**mysql_config)
        self.cursor = self.conn.cursor()
        return self.cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        self.cursor.close()
        self.conn.close()

''' --------------------------------------------------------------------------------------------------- '''

class insert:
    def __init__(self):
        self.db_url = f'mysql+mysqlconnector://{mysql_config["user"]}:{mysql_config["password"]}@{mysql_config["host"]}/{mysql_config["database"]}'
        self.engine = create_engine(self.db_url)
        self.weather_change_columns = {
            'lat': 'LAT',
            'lng': 'LNG',
            'date': 'DATE',
            'Rainf': 'RAINFALL',
            'Snowf': 'SNOWFALL',
            'air_pressure': 'AIR_PRESSURE',
            'air_temperature': 'AIR_TEMPERATURE',
            'humidity': 'HUMIDITY',
            'wind_from_direction': 'WIND_FROM_DIRECTION',
            'wind_speed': 'WIND_SPEED'
        }
        self.genre_streams_change_columns = {
            'region': 'COUNTRY_CODE',
            'date': 'DATE',
            'streams': 'STREAMS',
            'playlist_genre': 'GENRE'
        }

    def country(self, cursor):
        euro_code = pd.read_csv(root.get_path('cleaned_country')).set_index('KAGGLE_CODE').to_dict()['COUNTRY_NAME']
        sql = '''
        INSERT INTO COUNTRY (COUNTRY_CODE, COUNTRY_NAME) VALUES (%s, %s)
        '''
        for kaggle_code, country_name in euro_code.items():
            cursor.execute(sql, (kaggle_code, country_name))

    def genre_streams_by_country(self, genre_dataframe):
        genre_dataframe = genre_dataframe[['region', 'date', 'streams', 'playlist_genre']].rename(columns=self.genre_streams_change_columns)
        genre_dataframe.to_sql('GENRE_STREAMS_BY_COUNTRY', con=self.engine, if_exists='append', index=False, method='multi')


    def geo_info(self, cursor):
        geo_euro_cities = geonames().get_cities()

        sql = '''
        INSERT INTO GEO_INFO (COUNTRY_CODE, LAT, LNG, POPULATION) VALUES (%s, %s, %s, %s)
        '''
        for kaggle_code, cities in geo_euro_cities.items():
            for city in cities:
                cursor.execute(sql, (kaggle_code, city['lat'], city['lng'], city['population']))

    def last_fm(self, cursor):
        data = last_fm().get_data()
        for code, tags in data.items():
            for tag in tags:
                sql = '''
                INSERT INTO LAST_FM (COUNTRY_CODE, TAG) VALUES (%s, %s)
                '''
                cursor.execute(sql, (code, tag))

    def weather(self):
        weather_dataframe = weather().get().rename(columns=self.weather_change_columns)
        weather_dataframe.to_sql('WEATHER', con=self.engine, if_exists='append', index=False, method='multi')

