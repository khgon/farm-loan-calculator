# 버그 분석 보고서

## 프로젝트 개요
후계농업경영인 육성자금 상환 계획 계산기 (Streamlit 애플리케이션)

## 발견된 버그 및 문제점

### 1. 🔴 **중복 Import 문제**
**위치**: `app.py` 라인 4, 14
**문제**: `Decimal`과 `localcontext` 모듈이 두 번 import됨
```python
# 라인 4: 전역 import
from decimal import Decimal, localcontext, ROUND_HALF_EVEN

# 라인 14: 함수 내부 import (중복)
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
```
**해결책**: 함수 내부의 중복 import 제거

### 2. 🔴 **requirements.txt 포맷 오류**
**위치**: `requirements.txt`
**문제**: 패키지 이름 앞에 불필요한 공백 존재
```
     streamlit
     pandas
     openpyxl
     xlsxwriter
```
**해결책**: 앞의 공백 제거

### 3. 🟡 **정밀도 손실 가능성**
**위치**: `app.py` 라인 58-64
**문제**: `Decimal`로 정밀한 계산 후 `int()`로 변환하여 정밀도 손실 가능
```python
rows.append({
    '년차': year,
    '잔액(원)': int(remaining),  # 정밀도 손실
    '이자(원)': int(interest_dec),  # 정밀도 손실
    '원금상환액(원)': int(paid_principal_dec),  # 정밀도 손실
    '연납부액(원)': int(payment_dec)  # 정밀도 손실
})
```

### 4. 🟡 **원금 분배 로직 잠재적 오류**
**위치**: `app.py` 라인 28-30, 48-52
**문제**: 원금 균등분할 시 나머지 분배 로직에서 정확성 문제 가능
```python
# 나머지 원금 분배 로직
extra = principal_dec - base_principal_payment * repay_years
# ...
paid_principal_dec = base_principal_payment + (Decimal('1') if extra > 0 else Decimal('0'))
```
**위험**: `extra`가 `repay_years`보다 클 경우 일부 연도에 1원씩만 추가 분배

### 5. 🟡 **세션 상태 관리 문제**
**위치**: `app.py` 라인 84-96
**문제**: 세션 상태 버튼 클릭 시 페이지 새로고침으로 인한 예상치 못한 동작
- 원금 설정 버튼들이 개별적으로 작동하여 의도치 않은 다중 클릭 가능

### 6. 🟡 **에러 처리 부족**
**위치**: `app.py` 라인 133-141
**문제**: Excel 다운로드 시 `ImportError` 외 다른 예외 상황 처리 없음
```python
try:
    with pd.ExcelWriter(towrite, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
except ImportError:  # 다른 예외는 처리하지 않음
    with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
```

### 7. 🟡 **유효성 검사 누락**
**위치**: `app.py` 라인 97-99
**문제**: 슬라이더 값 변경 시 실시간 검증 부족
- 거치기간이 전체기간보다 큰 경우 처리 미흡
- 음수 이자율 등 edge case 처리 부족

### 8. 🔵 **성능 개선 가능**
**위치**: `app.py` 라인 7
**문제**: `@st.cache_data` 적용되어 있으나 세션 상태 변경 시 캐시 무효화 고려 필요

## 권장 수정사항

### 우선순위 높음 (🔴)
1. 중복 import 제거
2. requirements.txt 포맷 수정

### 우선순위 중간 (🟡)  
1. 정밀도 손실 방지를 위한 반올림 정책 명확화
2. 원금 분배 로직 개선
3. 포괄적인 예외 처리 추가
4. 세션 상태 관리 개선

### 우선순위 낮음 (🔵)
1. 성능 최적화
2. 사용자 경험 개선

## 테스트 권장사항
1. 다양한 금리 조건에서 계산 결과 검증
2. 극단적인 값(매우 큰 원금, 긴 기간) 테스트
3. 거치기간 = 전체기간 - 1인 경우 테스트
4. 브라우저 새로고침 시 세션 상태 유지 테스트

## 결론
전체적으로 기능은 정상 작동하나, 몇 가지 개선사항이 필요함. 특히 정밀도 관련 이슈와 에러 처리 부분의 보완이 권장됨.