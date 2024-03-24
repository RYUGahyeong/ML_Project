from collections import Counter

class weather_data_preprocessing:

    # # 온도에 따른 쾌적 습도 범위
    # def comfort_humidity_ranges_by_temp(self, humidity, temp):
    #     if temp < 0:
    #         min_h, max_h = 30, 50
    #     elif temp < 10:
    #         min_h, max_h = 50, 60
    #     elif temp < 20:
    #         min_h, max_h = 40, 60
    #     else:
    #         min_h, max_h = 40, 50
    #
    #     result = {
    #         humidity < min_h : 'low',
    #         min_h <= humidity : 'normal',
    #         humidity > max_h : 'high',
    #     }
    #
    #     return result[True]

    # 한국과 유럽 국가들 간 음악 취향 비교
    def compare_european_tracks_preference(self, kor_genre_tags, eur_countries_genre_tags):
        eur_countries_weight = {}
        for eur_genre in eur_countries_genre_tags.items():
            eur_countries_weight[eur_genre.key()] = sum((Counter(kor_genre_tags) & Counter(eur_genre.value())).values())