import copy
import folium
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from bokeh.plotting import figure, show, output_notebook
from bokeh.models import DatetimeTickFormatter
from bokeh.palettes import Category20

plt.rcParams['font.family'] = 'Malgun Gothic'  # 한글 폰트 설정
plt.rcParams['axes.unicode_minus'] = False  # 마이너스 부호 출력 설정


''' --------------------------------------------------------------------------------------------------- '''



# 여러 선 그래프 를 동시에, 기본 그래프
def line_hue(**kwargs):
    """
    df: 데이터프레임
    title: 그래프 제목
    x_label: x축 이름
    y_label: y축 이름
    x: x축 컬럼명
    y: y축 컬럼명
    hue: hue 컬럼명
    """
    df = kwargs['df']
    title = kwargs['title']
    x, y = kwargs['x'], kwargs['y']
    x_label, y_label = kwargs['x_label'], kwargs['y_label']
    hue = kwargs['hue']

    plt.figure(figsize=(10, 5))
    sns.lineplot(data=df, x=x, y=y, hue=hue)
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.grid(True)
    plt.legend(title=title)
    plt.show()

# 여러 그래프
def selectable_lines(**kwargs):
    """
    df: 데이터프레임
    title: 그래프 제목
    x_label: x축 이름
    y_label: y축 이름
    x: x축 컬럼명
    y: y축 컬럼명
    hue: hue 컬럼명
    """
    title = kwargs['title']
    x, y = kwargs['x'], kwargs['y']
    x_label, y_label = kwargs['x_label'], kwargs['y_label']
    hue = kwargs['hue']
    df = copy.deepcopy(kwargs['df'])[[x, y, hue]]

    df = df.groupby([x, hue]).mean().reset_index()

    output_notebook()
    hues = list(df[hue].unique())
    palette = Category20[20] if len(hues) > 10 else Category20[len(hues) * 2]

    # 그래프 생성
    p = figure(title=title, width=1100, height=600, tools="pan,wheel_zoom,box_zoom,reset")
    p.xaxis.axis_label = x_label
    p.yaxis.axis_label = y_label

    # 날짜 형식 설정
    if x == 'date':
        p.xaxis.formatter = DatetimeTickFormatter(
            days="%Y-%m-%d",
            months="%Y-%m-%d",
            years="%Y-%m-%d"
        )

    # hue 색상 설정
    for i, hue_value in enumerate(hues):
        hue_df = df[df[hue] == hue_value]

        p.line(x=x, y=y, source=hue_df, legend_label=hue_value, color=palette[i], line_width=2)

    # 범례 클릭 정책 설정: 항목 클릭 시 해당 선 토글
    p.legend.click_policy = "hide"
    p.legend.location = "top_left"
    p.legend.background_fill_color = "white"
    p.legend.background_fill_alpha = 1

    show(p)


def koppen_map(**kwargs):
    """
    :param koppen_df: koppen 기후 분류된 dict
    :param city: 도시 DataFrame
    """
    koppen_dfs = kwargs.get('koppen_df')
    city = kwargs.get('city')
    koppen_desc = {
        'A': '''<b>열대 기후</b> <br />
                    모든달 평균 온도가 18도 이상이며, 연중 강수량이 풍부한 기후입니다.''',
        'B': '''<b>건조 기후</b><br />
                    증발량이 강수량보다 많아 건조한 기후입니다.''',
        'Cfa': '''<b>습윤 아열대 기후(온난 습윤 기후)</b><br />
                    온화한 겨울과 더운 여름을 가지며, 연중 강수량이 풍부합니다.''',
        'Cfb': '''<b>해양성 기후(온난 습윤 기후)</b></br>            
                    온화한 겨울, 시원한 여름을 가지며, 연중 강수량이 균일합니다.''',
        'Cwa': '''<b>건조한 겨울을 가진 아열대 기후</b><br/>
                    더운 여름과 건조한 겨울을 가집니다.''',
        'Cwb': '''<b>건조한 겨울을 가진 온난한 온대 기후</b><br/>
                    시원한 여름과 건조한 겨울을 가집니다.''',
        'Dfa': '''<b>습윤 대륙성 기후(더운 여름)</b></br>
                    추운 겨울과 더운 여름을 가지며, 연중 강수량이 풍부합니다.''',
        'Dfb': '''<b>습윤 대륙성 기후(온화한 여름)</b></br>
                    추운 겨울과 온화한 여름을 가지며, 연중 강수량이 풍부합니다.''',
        'Dwc': '''<b>건조한 겨울을 가진 대륙성 기후(냉각된 여름)</b><br/>
                    매우 추운 겨울과 시원한 여름을 가지며, 겨울에 건조합니다.''',
        'Dwd': '''<b>건조한 겨울을 가진 대륙성 기후(매우 추운 겨울)</b><br />
                    매우 추운 겨울과 시원한 여름을 가지며, 겨울에 건조합니다.''',
        'E': '''<b>극지 기후</b><br/>
                    매우 추운 환경으로, 가장 따뜻한 달의 평균 온도가 10도를 넘지 않는 기후입니다.'''  # 남색
    }

    # 쾨펜 기후 분류별 색상 지정
    koppen_colors = {
        'A': 'red',
        'B': 'black',  # 지도상 높은 곳에 위치해 안보임
        'Cfa': '#FFB347',  # 오렌지 계열
        'Cfb': '#FFCC99',
        'Cwa': '#FFA500',
        'Cwb': '#FFC04C',
        'Dfa': '#87CEFA',  # 파란색 계열
        'Dfb': '#7B68EE',
        'Dwc': '#1E90FF',
        'Dwd': '#0000CD',
        'E': 'gray'
    }

    coords = city['POINT'].apply(lambda x: (x.x, x.y)).tolist()
    lng_center, lat_center = map(np.mean, zip(*coords))

    # 지도 생성
    europe_map = folium.Map(location=[lat_center, lng_center], zoom_start=3, scrollWheelZoom=False)

    # 도시 포인트
    for code, df in koppen_dfs.items():
        coords = df['POINT'].apply(lambda x: (x.x, x.y)).tolist()
        color = koppen_colors.get(code, 'black')
        for coord in coords:
            lng, lat = coord
            popup = folium.Popup(f'<b>{code}</b><br/>{koppen_desc[code]}', max_width=300)
            folium.CircleMarker(
                location=[lat, lng],  # 원의 중심 좌표 (위도, 경도)
                radius=2,  # 원의 반지름
                color=color,  # 원의 테두리 색
                fill=True,  # 원 내부를 채울지 여부
                fill_color=color,  # 원 내부의 채우기 색
                fill_opacity=1,  # 원 내부 채우기의 투명도
                popup=popup
            ).add_to(europe_map)

    return europe_map

def cluster_count_donut(**kwargs):
    """
    :param cluster_counts: 클러스터 개수
    :return: 
    """
    cluster_counts = kwargs['cluster_counts']
    
    # Seaborn 스타일 및 색상 팔레트 설정
    sns.set_palette("pastel")

    # 2% 미만 항목 필터링
    total = cluster_counts.sum()
    small_counts = cluster_counts[cluster_counts / total < 0.02]
    others_sum = small_counts.sum()
    filtered_counts = cluster_counts[cluster_counts / total >= 0.02]

    # "기타" 항목 추가
    if others_sum > 0:  # "기타" 항목이 있을 경우에만 추가
        filtered_counts['기타 (' + str(len(small_counts)) + '개)'] = others_sum

    # 새로운 라벨과 색상 팔레트 생성
    labels = filtered_counts.index
    colors = sns.color_palette("pastel", len(labels))

    # 파이 차트 그리기
    plt.figure(figsize=(10, 8))
    plt.pie(
        filtered_counts, startangle=90, labels=labels, autopct=lambda p: '{:.0f}%'.format(p) if p >= 2 else '',
        colors=colors, wedgeprops={'edgecolor': 'none'}
    )

    # 중앙의 하얀 원 추가
    centre_circle = plt.Circle((0, 0), 0.20, fc='white')
    fig = plt.gcf()
    fig.gca().add_artist(centre_circle)

    # 동일한 비율로 설정하여 파이차트가 원형으로 보이도록 함
    plt.axis('equal')

    # 제목 및 범례 추가
    plt.title('날씨 패턴 비율', pad=30)
    plt.legend(labels, title="날씨 패턴", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))

    # 차트 표시
    plt.show()