import os
import sys

root =  os.path.dirname(os.path.abspath(__file__).replace('\\', '/'))

# 모듈 경로 추가
package_path = ['/weather', '/weather/ml_model', '/weather/visual_insight', '/weather/preprocess']
for p in package_path:
    full_path = root + p
    if full_path not in sys.path:
        sys.path.append(full_path)

path = {
    # 설정 파일
    "config": "/config.json",

    # 캐글 파일
    "kaggle_weather": "/data/weather_spotify_songs.csv",
    "kaggle_genre": "/data/thirty_thousand_spotify_songs.csv",

    # 날씨 관련 데이터 파일
    "csv_weather_pattern": "/data/original/weather_csv/IGRA_2019_*.csv",
    "nc_rainfall_pattern": "/data/original/weather_nc/rainfall/Rainf_*.nc",
    "nc_snowfall_pattern": "/data/original/weather_nc/snowfall/Snowf_*.nc",
    "nc_air_pressure_pattern": "/data/original/weather_nc/air_pressure/PSurf_*.nc",
    "nc_humidity_pattern": "/data/original/weather_nc/specific_humidity/Qair_*.nc",
    "nc_temperature_pattern": "/data/original/weather_nc/temperature/Tair_*.nc",
    "nc_wind_pattern": "/data/original/weather_nc/wind/Wind_*.nc",

    # 가공된 파일 저장 경로
    "country": "/data/cleaned/COUNTRY.csv",
    "state": "/data/cleaned/STATE.csv",
    "city": "/data/cleaned/CITY.csv",
    "weather": "/data/cleaned/WEATHER.csv",
    "last_fm": "/data/cleaned/LAST_FM.csv",
    "genre_streams_by_country": "/data/cleaned/GENRE_STREAMS_BY_COUNTRY.csv",

    # 지리 Natural Earth 데이터 파일
    "natural_country": "/data/original/geo_natural_earth/country/country.shp",
    "natural_city": "/data/original/geo_natural_earth/city/city.shp",
    "natural_state": "/data/original/geo_natural_earth/state/state.shp",

    # h5py 파일 저장 패턴
    "h5py_rainf_pattern": "/data/h5py/rainf/Rainf",
    "h5py_snowf_pattern": "/data/h5py/snowf/Snowf",
    "h5py_air_pressure_pattern": "/data/h5py/air_pressure/PSurf",
    "h5py_humidity_pattern": "/data/h5py/specific_humidity/Qair",
    "h5py_temperature_pattern": "/data/h5py/temperature/Tair",
    "h5py_wind_pattern": "/data/h5py/wind/Wind",

    # 모델 실행파일 저장경로
    "time_model": "/weather/model/time_model.joblib",
    "scaler": "/weather/model/scale.joblib",

    "recommend": "/weather/model/recommend.csv"

}

def get_path(key):
    if key == '':
        return root

    return root + path[key]