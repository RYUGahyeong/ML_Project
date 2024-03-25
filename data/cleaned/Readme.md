## 데이터 설명
- COUNTRY_CODE 는 캐글 국가 코드입니다.
- weather 데이터는 가공을 편하게 하기 위해 inner join 으로 변경했으며 nan값은 제외했습니다.  
- 수집 데이터는 행정 구역 경계면을 기준으로 나누었습니다.
- last_fm 데이터는 해당 국가의 음악 취향과 한국의 음악 취향의 차이를 알아보기 위해 상위 100개 음악의 태그를 수집한 데이터입니다. COUNTRY_CODE="KOR" 은 한국을 의미합니다.

<hr />

### country
| 설명        | 필드명          |
|-----------|--------------|
| 캐글 국가 코드  | COUNTRY_CODE |
| 지리 데이터 코드 | GEO_CODE     |
| 국가 이름     | COUNTRY_NAME |

### state
| 설명              | 필드명          |
|-----------------|--------------|
| 국가 코드           | COUNTRY_CODE |
| 행정 구역 코드        | DISTRICT     |
| 행정 경계 (POLYGON) | GEOMETRY     |

### city
| 설명          | 필드명          |
|-------------|--------------|
| 행정 구역 코드    | DISTRICT     |
| 도시명         | CITY         |
| 인구수         | POPULATION   |
| 도시 중심 POINT | POINT        |

### genre_streams_by_country
| 설명    | 필드명    |
|-------|--------|
| 국가 코드 |COUNTRY_CODE|
| 수집된 날 |DATE|
|청취수|STREAMS|
|장르|GENRE|

### last_fm
| 설명                      | 필드명          |
|-------------------------|--------------|
| 국가 이름                   | COUNTRY_NAME |
| 태그 (장르가 포함되어 있는 경우도 있음) | TAG          |

### weather
| 설명                             | 필드명             | 
|--------------------------------|-----------------|
| 수집된 날                          | DATE            |
| 시간 그룹 ('0-8', '8-16', '16-24') | TIME_GROUP      |
| 도시 이름                          | CITY            |
| 대기압 (Pa)                       | AIR_PRESSURE    |
| 공기 온도 (K)                      | AIR_TEMPERATURE |
| 상대 습도 (%)                      | HUMIDITY        |
| 강수량 (kg/(m^2/s)                | RAINFALL        |
| 강설량 (kg/(m^2/s) )              | SNOWFALL        |