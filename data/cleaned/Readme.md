### COUNTRY
| 필드명       | 설명           |
|-----------|--------------|
| COUNTRY_CODE  | 캐글 국가 코드 |
| GEO_CODE | 지리 데이터 국가 코드 |
| COUNTRY_NAME     | 국가 이름        |

### STATE
| 필드명          | 설명              |
|--------------|-----------------|
| DISTRICT     | 행정 구역 코드        |
| COUNTRY_CODE | 국가 코드           |
| GEOMETRY     | 행정 경계 (POLYGON) |

### CITY
| 필드명          | 설명                         |
|-------------|------------------------|
| CITY    | 도시명               |
| DISTRICT         | 행정 구역 코드                   |
| POPULATION         | 인구수             |
| POINT | 도시 중심 위도, 경도 Point 자료형 |

### GENRE_STREAMS_BY_COUNTRY
| 필드명          | 설명                         |
|-------|-----------|
| COUNTRY_CODE | 국가 코드     |
| DATE | 데이터 수집된 날 |
|STREAMS| 청취수   |
|GENRE| 장르     |

### LAST_FM
| 필드명          | 설명                         |
|--------------|----------------------------|
| COUNTRY_NAME | 국가 이름                      |
| TAG          | 음악 분류 (장르가 포함되어 있는 경우도 있음) |

### WEATHER
| 필드명          | 설명                                      | 
|--------------|-----------------------------------------|
| DATE         | 수집된 날                                   |
| TIME_GROUP   | 시간 그룹 ('0-6', '6-12', '12-18', '18-24') |
| CITY         | 도시 이름                                   |
| RAINFALL     | 강수량 (kg/(m^2/s)                         |
| SNOWFALL     | 강설량 (kg/(m^2/s)                         |
| AIR_PRESSURE | 대기압 (Pa)                                |
| HUMIDITY     | 상대 습도 (%)                               |
| TEMPERATURE  | 공기 온도 (K)                               |
| WIND_SPEED   | 풍속 (m s-1)                              |
