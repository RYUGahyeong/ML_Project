import copy
import seaborn as sns
import matplotlib.pyplot as plt
from bokeh.plotting import figure, show, output_notebook
from bokeh.models import DatetimeTickFormatter
from bokeh.palettes import Category20

plt.rcParams['font.family'] = 'Malgun Gothic'  # 한글 폰트 설정
plt.rcParams['axes.unicode_minus'] = False  # 마이너스 부호 출력 설정


''' --------------------------------------------------------------------------------------------------- '''

class graph:

    # 여러 선 그래프 를 동시에, 기본 그래프
    def line_hue(self, **kwargs):
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
    def selectable_lines(self, **kwargs):
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


    # def multi_scatter(self, **kwargs):
    #     """
    #     df: 데이터프레임
    #     title: 그래프 제목
    #     x: x축 컬럼명
    #     y: y축 컬럼명
    #     hue: hue 컬럼명
    #     """
    #     df = kwargs['df']
    #     title = kwargs['title']
    #     x, y = kwargs['x'], kwargs['y']
    #     hue = kwargs['hue']
    #
    #     scatters = [go.Scatter(x=df[df[hue]==label][x], y=df[df[hue]==label][y], mode='markers', name=label) for label in df[hue].unique()]
    #
    #     layout = go.Layout(
    #         title=title,
    #         updatemenus=[dict(
    #             type="buttons",
    #             direction="left",
    #             buttons=list([
    #                 dict(
    #                     args=["type", "scatter"],
    #                     label="토글",
    #                     method="restyle"
    #                 )
    #             ]),
    #         )]
    #     )
    #
    #     fig = go.Figure(data=scatters, layout=layout)
    #     fig.show()