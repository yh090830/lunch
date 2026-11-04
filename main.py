import streamlit as st
import pandas as pd
import plotly.express as px
import re
from itertools import combinations
from collections import Counter

# ==========================================
# 1. 기본 설정
# ==========================================

st.set_page_config(
    page_title="급식 규칙 찾기",
    page_icon="🍱",
    layout="wide"
)

st.title("🍱 급식 규칙 찾기")
st.write("송탄고등학교 중식 데이터를 이용한 메뉴 장바구니 분석")

DATA_URL = "https://raw.githubusercontent.com/it-teacher-go/data-share-/main/songtan_meals_184.csv"


# ==========================================
# 2. 데이터 불러오기
# ==========================================

@st.cache_data
def load_data():
    df = pd.read_csv(
        DATA_URL,
        encoding="utf-8-sig",
        dtype=str,
        keep_default_na=False
    )

    df.columns = df.columns.str.strip()

    required_columns = ["날짜", "식사", "메뉴"]

    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"CSV에 '{col}' 열이 없습니다.")

    return df


# ==========================================
# 3. 메뉴 이름 정리
# ==========================================

def clean_menu(menu):
    """메뉴 이름에서 괄호와 괄호 안의 내용을 제거한다."""

    menu = str(menu).strip()

    while True:
        cleaned = re.sub(
            r"\([^()]*\)|（[^（）]*）",
            "",
            menu
        )

        if cleaned == menu:
            break

        menu = cleaned

    return re.sub(r"\s+", " ", menu).strip()


# ==========================================
# 4. 장바구니 데이터 만들기
# ==========================================

def make_baskets(df):

    baskets = []

    for menu_text in df["메뉴"]:

        if not menu_text.strip():
            continue

        menus = [
            clean_menu(menu)
            for menu in menu_text.split("|")
        ]

        # 빈 메뉴 제거 및 중복 메뉴 제거
        menus = sorted(set(
            menu for menu in menus if menu
        ))

        if menus:
            baskets.append(menus)

    return baskets


# ==========================================
# 5. 연관 규칙 분석
# ==========================================

def analyze_rules(baskets):

    total_days = len(baskets)

    menu_counts = Counter()
    pair_counts = Counter()

    for basket in baskets:

        menu_counts.update(basket)

        for pair in combinations(sorted(basket), 2):
            pair_counts[pair] += 1

    rules = []

    for (menu_a, menu_b), together_count in pair_counts.items():

        support = together_count / total_days

        # A → B
        confidence_ab = together_count / menu_counts[menu_a]
        lift_ab = confidence_ab / (
            menu_counts[menu_b] / total_days
        )

        rules.append({
            "조건": menu_a,
            "결과": menu_b,
            "동시": together_count,
            "지지도": support,
            "신뢰도": confidence_ab,
            "향상도": lift_ab
        })

        # B → A
        confidence_ba = together_count / menu_counts[menu_b]
        lift_ba = confidence_ba / (
            menu_counts[menu_a] / total_days
        )

        rules.append({
            "조건": menu_b,
            "결과": menu_a,
            "동시": together_count,
            "지지도": support,
            "신뢰도": confidence_ba,
            "향상도": lift_ba
        })

    return rules, menu_counts, pair_counts


# ==========================================
# 6. 데이터 분석 실행
# ==========================================

try:

    df = load_data()

    baskets = make_baskets(df)

    if not baskets:
        st.error("분석할 급식 데이터가 없습니다.")
        st.stop()

    rules, menu_counts, pair_counts = analyze_rules(baskets)

    rules_df = pd.DataFrame(rules)

    if rules_df.empty:
        st.warning("함께 나온 메뉴 쌍이 없습니다.")
        st.stop()

except Exception as e:

    st.error(
        f"데이터를 불러오거나 분석하는 중 오류가 발생했습니다: {e}"
    )
    st.stop()


# ==========================================
# 7. 기본 통계
# ==========================================

total_days = len(baskets)
total_menus = len(menu_counts)
total_pairs = len(pair_counts)

st.subheader("📊 분석 데이터 요약")

st.markdown(
    f"""
    **급식 일수:** {total_days:,}일　|　
    **메뉴 종류 수:** {total_menus:,}종　|　
    **함께 나온 메뉴 쌍:** {total_pairs:,}쌍
    """
)

st.divider()


# ==========================================
# 8. 연관 규칙 검색 설정
# ==========================================

st.subheader("🔍 연관 규칙 검색")

col1, col2 = st.columns(2)

with col1:

    selected_menu = st.selectbox(
        "메뉴로 좁혀 보기",
        options=["전체 메뉴"] + sorted(menu_counts.keys()),
        index=0
    )

with col2:

    sort_option = st.selectbox(
        "정렬 기준",
        options=[
            "향상도 순",
            "신뢰도 순",
            "동시 순"
        ],
        index=0
    )


# ==========================================
# 9. 최소 동시 일수 슬라이더
# ==========================================

min_together = st.slider(
    "최소 동시 일수",
    min_value=1,
    max_value=10,
    value=1,
    step=1,
    help="선택한 일수보다 적게 함께 나온 메뉴 규칙은 제외합니다."
)


# ==========================================
# 10. 규칙 필터링
# ==========================================

filtered_df = rules_df.copy()

# 최소 동시 일수 적용
filtered_df = filtered_df[
    filtered_df["동시"] >= min_together
]

# 메뉴 선택 적용
if selected_menu != "전체 메뉴":

    filtered_df = filtered_df[
        (filtered_df["조건"] == selected_menu) |
        (filtered_df["결과"] == selected_menu)
    ]


# ==========================================
# 11. 정렬
# ==========================================

sort_columns = {
    "향상도 순": ["향상도", "신뢰도", "동시"],
    "신뢰도 순": ["신뢰도", "향상도", "동시"],
    "동시 순": ["동시", "향상도", "신뢰도"]
}

filtered_df = filtered_df.sort_values(
    by=sort_columns[sort_option],
    ascending=[False, False, False]
).reset_index(drop=True)


# ==========================================
# 12. 남은 규칙 수 표시
# ==========================================

st.write(
    f"**현재 조건에 맞는 규칙: {len(filtered_df):,}개**"
)

st.caption(
    f"최소 동시 일수 {min_together}일 이상인 규칙만 표시합니다."
)


# ==========================================
# 13. 연관 규칙 표
# ==========================================

st.subheader("📋 메뉴 연관 규칙")

st.caption(
    "지지도: 전체 급식 중 두 메뉴가 함께 나온 비율 | "
    "신뢰도: 조건 메뉴가 나왔을 때 결과 메뉴도 나온 비율 | "
    "향상도: 두 메뉴의 연관 정도"
)

display_df = filtered_df[
    ["조건", "결과", "동시", "지지도", "신뢰도", "향상도"]
]

st.dataframe(
    display_df.style.format({
        "지지도": "{:.2%}",
        "신뢰도": "{:.2%}",
        "향상도": "{:.3f}"
    }),
    use_container_width=True,
    hide_index=True,
    height=500
)


# ==========================================
# 14. 향상도 상위 10개 그래프
# ==========================================

st.divider()

st.subheader("📈 향상도 상위 10개 메뉴 규칙")

if not filtered_df.empty:

    top10_df = filtered_df.sort_values(
        by=["향상도", "신뢰도", "동시"],
        ascending=[False, False, False]
    ).head(10).copy()

    top10_df["규칙"] = (
        top10_df["조건"] + " → " + top10_df["결과"]
    )

    top10_df["규칙"] = [
        f"{i + 1}. {rule}"
        for i, rule in enumerate(top10_df["규칙"])
    ]

    fig = px.bar(
        top10_df.sort_values(
            "향상도",
            ascending=True
        ),
        x="향상도",
        y="규칙",
        orientation="h",
        text="향상도",
        hover_data={
            "조건": True,
            "결과": True,
            "동시": True,
            "지지도": ":.2%",
            "신뢰도": ":.2%",
            "향상도": ":.3f",
            "규칙": False
        },
        labels={
            "향상도": "향상도 (Lift)",
            "규칙": "연관 규칙"
        },
        title="향상도 기준 상위 10개 연관 규칙"
    )

    fig.update_traces(
        texttemplate="%{text:.3f}",
        textposition="outside"
    )

    fig.update_layout(
        height=500,
        xaxis_title="향상도",
        yaxis_title="메뉴 규칙",
        yaxis=dict(
            automargin=True
        ),
        showlegend=False
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

else:

    st.info("선택한 조건에 해당하는 연관 규칙이 없습니다.")


# ==========================================
# 15. 함께 나온 적 없는 짝
# ==========================================

st.divider()

st.subheader("🚫 함께 나온 적 없는 짝")

st.write(
    "메뉴 하나를 선택하면 그 메뉴와 한 번도 같은 날 나오지 않았지만, "
    "개별적으로 10일 이상 등장한 메뉴를 찾아줍니다."
)

# 연관 규칙 검색과 별개의 메뉴 선택
never_menu = st.selectbox(
    "함께 나온 적 없는 짝을 찾을 기준 메뉴",
    options=sorted(menu_counts.keys()),
    index=0,
    key="never_menu_select"
)

# 선택한 메뉴의 등장 횟수
selected_menu_days = menu_counts[never_menu]

# 기준 메뉴와 한 번도 함께 나오지 않은 메뉴 찾기
never_together = []

for candidate_menu, days in menu_counts.items():

    if candidate_menu == never_menu:
        continue

    pair = tuple(sorted((never_menu, candidate_menu)))

    # 함께 나온 횟수가 0이고, 개별 등장 횟수가 10일 이상인 메뉴
    if pair_counts.get(pair, 0) == 0 and days >= 10:

        never_together.append({
            "메뉴": candidate_menu,
            "나온 날 수": days
        })

# 등장 횟수가 많은 순으로 정렬
never_df = pd.DataFrame(never_together)

if not never_df.empty:

    never_df = never_df.sort_values(
        by="나온 날 수",
        ascending=False
    ).reset_index(drop=True)

# 기준 메뉴의 등장 횟수와 검색 결과 수 표시
st.markdown(
    f"""
    **선택한 메뉴:** {never_menu}　|　
    **선택한 메뉴가 나온 날:** {selected_menu_days}일　|　
    **함께 나온 적 없는 메뉴:** {len(never_df):,}종
    """
)

if not never_df.empty:

    st.dataframe(
        never_df,
        use_container_width=True,
        hide_index=True,
        height=400
    )

else:

    st.info(
        "조건에 맞는 메뉴가 없습니다. "
        "다른 메뉴를 선택해 보세요."
    )


# ==========================================
# 16. 분석 결과 해석 안내
# ==========================================

with st.expander("📖 연관 규칙 지표 알아보기"):

    st.markdown(
        """
        **1. 지지도 (Support)**

        두 메뉴가 전체 급식 일수 중 얼마나 자주 함께 나왔는지 나타냅니다.

        지지도 = 두 메뉴가 함께 나온 일수 / 전체 급식 일수

        **2. 신뢰도 (Confidence)**

        조건 메뉴가 나왔을 때 결과 메뉴도 함께 나올 확률입니다.

        신뢰도 = 두 메뉴가 함께 나온 일수 / 조건 메뉴가 나온 일수

        **3. 향상도 (Lift)**

        두 메뉴가 독립적으로 등장한다고 가정했을 때보다
        실제로 얼마나 더 자주 함께 나오는지를 나타냅니다.

        - 향상도 > 1 : 양의 연관성
        - 향상도 = 1 : 독립적인 관계
        - 향상도 < 1 : 음의 연관성

        **4. 함께 나온 적 없는 짝**

        선택한 메뉴와 같은 날 한 번도 등장하지 않은 메뉴 중
        개별적으로 10일 이상 등장한 메뉴만 표시합니다.

        ※ 향상도가 높다고 해서 반드시 인과관계가 있다는 뜻은 아닙니다.
        """
    )

st.caption(
    "송탄고등학교 중식 데이터 기반 메뉴 장바구니 분석"
)
