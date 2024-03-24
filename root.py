import os
import sys

root =  os.path.dirname(os.path.abspath(__file__).replace('\\', '/'))

# 모듈 경로 추가
package_path = ['/weather', '/weather/module', '/weather/module/data', '/weather/zest', '/weather/zest/data']
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

    # 가공된 파일 저장 경로
    "cleaned_country": "/data/cleaned/country.csv",
    "cleaned_state": "/data/cleaned/state.csv",
    "cleaned_city": "/data/cleaned/city.csv",
    "cleaned_weather": "/data/cleaned/weather.csv",
    "cleaned_last_fm": "/data/cleaned/last_fm.csv",
    "cleaned_genre_streams_by_country": "/data/cleaned/genre_streams_by_country.csv",

    # 지리 Natural Earth 데이터 파일
    "natural_country": "/data/original/geo_natural_earth/country/country.shp",
    "natural_city": "/data/original/geo_natural_earth/city/city.shp",
    "natural_state": "/data/original/geo_natural_earth/state/state.shp",

    # h5py 파일 저장 패턴
    "h5py_rainf_pattern": "/data/h5py/rainf/Rainf",
    "h5py_snowf_pattern": "/data/h5py/snowf/Snowf",

}

def get_path(key):
    """
    "kaggle_weather": 캐글 유럽 날씨 데이터
    "kaggle_genre": 캐글 3만 장르 데이터
    "kaggle_weather_euro_code": kaggle weather 국가 코드
    "csv_weather_pattern": csv 날씨 데이터 *.csv 패턴    
    "nc_rainfall_pattern": nc 파일 강수량 패턴
    "nc_snowfall_pattern": nc 파일 강설량 패턴
    "geo_euro_code": geonames api 국가 코드
    "geo_euro_cities": geonames api 국가별 도시 목록
    """
    if key == '':
        return root

    return root + path[key]