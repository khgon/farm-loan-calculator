import streamlit as st
import pandas as pd
import io
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from datetime import datetime

@st.cache_data(show_spinner=False)
def generate_loan_schedule(principal: int, annual_rate: float, total_years: int, grace_years: int) -> pd.DataFrame:
    """
    대출 상환 일정을 생성하는 모델.
    첫 번째 행(대출 실행 연도)은 원금만 남아 있고 이자 및 원금상환 없음.
    이후 거치기간 동안 이자만 납부, 그 다음부터 원금균등분할 상환을 적용합니다.
    """
    from decimal import Decimal, localcontext, ROUND_HALF_EVEN

    if principal <= 0:
        raise ValueError("대출 원금은 0보다 커야 합니다.")
    if annual_rate < 0:
        raise ValueError("연 이자율은 0 이상이어야 합니다.")
    if total_years <= 0:
        raise ValueError("전체 기간은 0보다 커야 합니다.")
    if grace_years < 0 or grace_years >= total_years:
        raise ValueError("거치 기간은 0 이상이고 전체 기간 미만이어야 합니다.")

    with localcontext() as ctx:
        ctx.prec = 28
        ctx.rounding = ROUND_HALF_EVEN

        remaining = Decimal(principal)
        rate = Decimal(str(annual_rate)) / Decimal('100')
        repay_years = total_years - grace_years

        principal_dec = Decimal(principal)
        temp_payment = principal_dec / Decimal(repay_years)
        base_principal_payment = temp_payment.quantize(Decimal('1'), rounding=ROUND_HALF_EVEN)
        extra = principal_dec - base_principal_payment * repay_years

        rows = []
        # 최초 연도: 원금만 유지, 이자/원금 없음
        rows.append({
            '년차': 0,
            '잔액(원)': int(remaining),
            '이자(원)': 0,
            '원금상환액(원)': 0,
            '연납부액(원)': 0
        })
        # 이후 연차 스케줄
        for year in range(1, total_years + 1):
            if year <= grace_years:
                # 거치기간: 이자만
                interest_dec = (remaining * rate).quantize(Decimal('1'), rounding=ROUND_HALF_EVEN)
                paid_principal_dec = Decimal('0')
            else:
                # 상환기간: 이자 + 원금균등분할
                interest_dec = (remaining * rate).quantize(Decimal('1'), rounding=ROUND_HALF_EVEN)
                if year == total_years:
                    paid_principal_dec = remaining
                else:
                    paid_principal_dec = base_principal_payment + (Decimal('1') if extra > 0 else Decimal('0'))
                    if extra > 0:
                        extra -= Decimal('1')
            payment_dec = interest_dec + paid_principal_dec
            remaining -= paid_principal_dec

            rows.append({
                '년차': year,
                '잔액(원)': int(remaining),
                '이자(원)': int(interest_dec),
                '원금상환액(원)': int(paid_principal_dec),
                '연납부액(원)': int(payment_dec)
            })

    return pd.DataFrame(rows)


def format_korean_won(amount: int) -> str:
    units = [(10**12, '조'), (10**8, '억'), (10**4, '만')]
    res = []
    for val, name in units:
        cnt = amount // val
        if cnt:
            res.append(f"{cnt}{name}")
            amount %= val
    if not res:
        return f"{amount}원"
    return ''.join(res)

# 페이지 설정
st.set_page_config(page_title="후계농업경영인 육성자금 상환 계획", layout="wide", initial_sidebar_state="expanded")

st.title("후계농업경영인 육성자금 상환 계획")

# 세션 초기화
if 'principal' not in st.session_state:
    st.session_state.principal = 0

# 사이드바: 대출 실행 연도 입력
current_year = datetime.now().year
st.sidebar.header("입력 설정")
start_year = st.sidebar.number_input("대출 실행 연도", min_value=1900, max_value=2100, value=current_year, step=1)

# 대출 원금 설정 버튼
st.sidebar.subheader("대출 원금 설정")
col1, col2, col3 = st.sidebar.columns(3)
if col1.button("+1억원"): st.session_state.principal += 100_000_000
if col2.button("+1천만원"): st.session_state.principal += 10_000_000
if col3.button("+1백만원"): st.session_state.principal += 1_000_000
if st.sidebar.button("원금 초기화"): st.session_state.principal = 0

# 현재 원금 표시
st.sidebar.write(f"현재 원금: {st.session_state.principal:,}원 ({format_korean_won(st.session_state.principal)})")

# 대출 조건 입력 폼
with st.sidebar.form(key='loan_form'):
    annual_rate = st.slider("금리 (%)", 0.0, 10.0, 1.5, 0.1)
    total_years = st.slider("전체 기간 (년)", 1, 50, 25)
    grace_years = st.slider("거치 기간 (년)", 0, total_years - 1, 5)
    submit = st.form_submit_button("계산하기")

# 계산 및 결과 표시
if submit:
    principal = st.session_state.principal
    if principal <= 0:
        st.error("원금을 먼저 설정하세요.")
    else:
        df = generate_loan_schedule(principal, annual_rate, total_years, grace_years)
        df['연도'] = df['년차'].apply(lambda y: start_year + y)

        st.subheader("대출 조건")
        st.write(f"- 대출 실행 연도: {start_year}년")
        st.write(f"- 금리: {annual_rate}%")
        st.write(f"- 대출(상환)기간 : {grace_years}년 거치 {total_years - grace_years}년 원금균등분할")

        total_interest = df['이자(원)'].sum()
        st.write(f"**총 이자 총액:** {total_interest:,}원")

        st.subheader("상환 일정 (단위: 천원)")
        df_k = df.pipe(
            lambda d: d.assign(
                **{c: (d[c] // 1000).astype(int) for c in ['잔액(원)', '이자(원)', '원금상환액(원)', '연납부액(원)']}
            )
        ).pipe(
            lambda d: d.rename(columns={
                '연도': '연도',
                '잔액(원)': '잔액(천원)',
                '이자(원)': '이자(천원)',
                '원금상환액(원)': '원금상환(천원)',
                '연납부액(원)': '연납부액(천원)'
            })
        )[['연도', '잔액(천원)', '이자(천원)', '원금상환(천원)', '연납부액(천원)']]
        st.dataframe(df_k)

        # 엑셀 다운로드
        towrite = io.BytesIO()
        try:
            with pd.ExcelWriter(towrite, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
        except ImportError:
            with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
        towrite.seek(0)
        st.download_button(
            label="원본 Excel 다운로드",
            data=towrite,
            file_name='loan_schedule.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
