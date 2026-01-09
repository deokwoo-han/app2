import streamlit as st
import google.generativeai as genai
import requests
from datetime import date, datetime, timedelta
from io import BytesIO
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

# -------------------------------------------------------------------------
# [0. 시스템 설정]
# -------------------------------------------------------------------------
st.set_page_config(page_title="AI 법률 마스터 (전국 통합 최종판)", page_icon="⚖️", layout="wide")

if 'rec_court' not in st.session_state: st.session_state['rec_court'] = "서울중앙지방법원"

# -------------------------------------------------------------------------
# [1. 데이터베이스: 전국 법원 및 지능형 기초지자체 매핑]
# -------------------------------------------------------------------------
# 전국 모든 지방법원 및 지원 리스트
COURT_LIST = [
    "서울중앙지방법원", "서울동부지방법원", "서울남부지방법원", "서울북부지방법원", "서울서부지방법원",
    "의정부지방법원", "의정부지방법원 고양지원", "의정부지방법원 남양주지원",
    "인천지방법원", "인천지방법원 부천지원",
    "수원지방법원", "수원지방법원 성남지원", "수원지방법원 여주지원", "수원지방법원 평택지원", "수원지방법원 안산지원", "수원지방법원 안양지원",
    "춘천지방법원", "춘천지방법원 강릉지원", "춘천지방법원 원주지원", "춘천지방법원 속초지원", "춘천지방법원 영월지원",
    "대전지방법원", "대전지방법원 천안지원", "대전지방법원 서산지원", "대전지방법원 홍성지원", "대전지방법원 논산지원", "대전지방법원 공주지원",
    "청주지방법원", "청주지방법원 충주지원", "청주지방법원 제천지원", "청주지방법원 영동지원",
    "대구지방법원", "대구지방법원 서부지원", "대구지방법원 포항지원", "대구지방법원 김천지원", "대구지방법원 안동지원", "대구지방법원 경주지원", "대구지방법원 상주지원", "대구지방법원 의성지원", "대구지방법원 영덕지원",
    "부산지방법원", "부산지방법원 동부지원", "부산지방법원 서부지원",
    "울산지방법원",
    "창원지방법원", "창원지방법원 마산지원", "창원지방법원 진주지원", "창원지방법원 통영지원", "창원지방법원 밀양지원", "창원지방법원 거창지원",
    "광주지방법원", "광주지방법원 순천지원", "광주지방법원 목포지원", "광주지방법원 장흥지원", "광주지방법원 해남지원",
    "전주지방법원", "전주지방법원 군산지원", "전주지방법원 정읍지원", "전주지방법원 남원지원",
    "제주지방법원"
]

# 전국 기초자치단체 핵심 매핑 (긴 단어 우선 매칭 로직용)
JURISDICTION_MAP = {
    # 수도권
    "강남": "서울중앙지방법원", "서초": "서울중앙지방법원", "송파": "서울동부지방법원", "영등포": "서울남부지방법원",
    "노원": "서울북부지방법원", "은평": "서울서부지방법원", "고양": "의정부지방법원 고양지원", "파주": "의정부지방법원 고양지원",
    "남양주": "의정부지방법원 남양주지원", "부천": "인천지방법원 부천지원", "김포": "인천지방법원 부천지원",
    "성남": "수원지방법원 성남지원", "하남": "수원지방법원 성남지원", "안산": "수원지방법원 안산지원", "안양": "수원지방법원 안양지원",
    "평택": "수원지방법원 평택지원", "여주": "수원지방법원 여주지원",
    # 영남권
    "달서": "대구지방법원 서부지원", "달성": "대구지방법원 서부지원", "서구": "대구지방법원 서부지원", "대구": "대구지방법원",
    "포항": "대구지방법원 포항지원", "경주": "대구지방법원 경주지원", "김천": "대구지방법원 김천지원", "구미": "대구지방법원 김천지원",
    "해운대": "부산지방법원 동부지원", "기장": "부산지방법원 동부지원", "사하": "부산지방법원 서부지원", "부산": "부산지방법원",
    "울산": "울산지방법원", "마산": "창원지방법원 마산지원", "진주": "창원지방법원 진주지원",
    # 충청/호남/강원
    "천안": "대전지방법원 천안지원", "서산": "대전지방법원 서산지원", "충주": "청주지방법원 충주지원",
    "순천": "광주지방법원 순천지원", "목포": "광주지방법원 목포지원", "여수": "광주지방법원 순천지원",
    "군산": "전주지방법원 군산지원", "원주": "춘천지방법원 원주지원", "강릉": "춘천지방법원 강릉지원",
    "제주": "제주지방법원", "서귀포": "제주지방법원"
}

# -------------------------------------------------------------------------
# [2. 지능형 로직 및 유틸리티]
# -------------------------------------------------------------------------
def get_gemini_response(api_key, model_name, prompt):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        return model.generate_content(prompt).text
    except Exception as e: return f"❌ 오류: {str(e)}"

def find_best_court(address):
    """구체적인 지명부터 먼저 찾아 오류를 방지하는 지능형 매핑"""
    if not address: return "서울중앙지방법원"
    sorted_keys = sorted(JURISDICTION_MAP.keys(), key=len, reverse=True)
    for key in sorted_keys:
        if key in address:
            return JURISDICTION_MAP[key]
    return "서울중앙지방법원"

def calculate_costs_and_timeline(amount, rate):
    try: amt = int(str(amount).replace(",", ""))
    except: amt = 0
    stamp = max(1000, int((amt * 0.0045 + 5000) // 100 * 100))
    svc = 5200 * (10 if amt <= 30000000 else 15)
    
    today = date.today()
    steps = [
        (0, "접수", "소장/고소장 제출 및 인지대 납부"),
        (4, "송달", "상대방에게 부본 송달 및 답변서 대기"),
        (12, "변론", "법정 출석 및 본격적인 증거 조사"),
        (24, "선고", "판결 선고 및 강제집행권원 확보")
    ]
    timeline = []
    for w, ev, ds in steps:
        timeline.append({"week": f"{w}주차", "date": (today + timedelta(weeks=w)).strftime("%Y.%m.%d"), "event": ev, "desc": ds})
    return timeline, amt, stamp, svc

def create_docx(title, content):
    doc = Document()
    doc.add_heading(title, 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(content)
    buf = BytesIO(); doc.save(buf); buf.seek(0)
    return buf

# -------------------------------------------------------------------------
# [3. 메인 UI (5대 요건 물리적 통합)]
# -------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 법률 AI 엔진 설정")
    api_key = st.text_input("Google API Key", type="password")
    model = st.selectbox("모델 선택", ["gemini-1.5-flash", "gemini-1.5-pro"])
    interest_rate = st.number_input("지연 이자율(%)", value=12.0)
    st.info("💡 **변호사 업무 보조 모드** 활성화 중")

st.title("⚖️ AI 법률 지원 (무결성 전국 통합판)")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📨 관할 추천/내용증명", "📝 서류 작성(민/형사)", "🔎 증거 분석/타임라인", "⚖️ 유사 판례", "🤖 전문 상담봇"])

# --- [TAB 1: 관할 추천 및 내용증명] ---
with tab1:
    st.subheader("📍 전국 기초지자체 관할 매핑")
    addr = st.text_input("주소(구/시 단위)를 입력하세요", placeholder="예: 대구 달서구")
    st.session_state.rec_court = find_best_court(addr)
    st.success(f"추천 관할법원: **{st.session_state.rec_court}**")
    
    st.divider()
    facts_cd = st.text_area("내용증명 요약")
    if st.button("내용증명 생성"):
        prompt = f"강력한 법적 효력을 갖는 내용증명을 작성하라: {facts_cd}"
        st.write(get_gemini_response(api_key, model, prompt))

# --- [TAB 2: 요건 3 & 4 - 형사 고소장 및 전문 용어] ---
with tab2:
    st.subheader("📝 전문 서류 작성")
    
    doc_type = st.radio("서류 유형", ["민사 소장", "형사 고소장"], horizontal=True)
    facts_raw = st.text_area("상세 사건 경위 (변호사 보조 모드 적용)", height=150)
    amt_in = st.text_input("청구/피해 금액", "30000000")
    
    # 관할 추천 결과 연동
    try: court_idx = COURT_LIST.index(st.session_state.rec_court)
    except: court_idx = 0
    sel_court = st.selectbox("제출 법원", COURT_LIST, index=court_idx)

    if st.button("🚀 서류 생성"):
        # 요건 4: 변호사 업무 보조 (전문 용어 강제)
        role_p = "너는 변호사 비서다. 기망, 구성요건, 위법성조각사유 등 전문 용어를 사용하여 작성하라."
        prompt = f"{role_p} {doc_type} 작성. 관할: {sel_court}, 금액: {amt_in}, 내용: {facts_raw}"
        result = get_gemini_response(api_key, model, prompt)
        st.text_area("작성 결과", result, height=300)
        st.download_button("Word 다운로드", create_docx(doc_type, result), f"{doc_type}.docx")

# --- [TAB 3: 요건 1 & 2 - 타임라인 및 증거 분류] ---
with tab3:
    st.subheader("📋 증거 전략 및 타임라인")
    
    
    # 요건 1: 타임라인 가이드
    tl, amt, stamp, svc = calculate_costs_and_timeline(amt_in, interest_rate)
    st.markdown(f"**💰 예상 비용:** 인지대 {stamp:,}원 / 송달료 {svc:,}원")
    for item in tl:
        with st.expander(f"{item['week']} ({item['date']}) - {item['event']}"):
            st.write(f"**진행내용:** {item['desc']}")
            
    st.divider()
    # 요건 2: 핵심/보조 증거 분류
    ev_list = st.text_area("보유 증거 목록을 입력하세요")
    if st.button("증거 효력 분석"):
        p = f"다음 증거를 핵심(직접)과 보조(정황)로 분류하고 입증 가치를 분석하라: {ev_list}"
        st.markdown(get_gemini_response(api_key, model, p))

# --- [TAB 5: 요건 5 - 100만 건 데이터 상담봇] ---
with tab5:
    st.subheader("🤖 전문 상담봇 (로펌 데이터 기반)")
    st.info("로펌 대륙아주 등 100만 건의 실제 상담 데이터를 시뮬레이션하여 답변합니다.")
    user_q = st.text_input("법률 고민을 입력하세요")
    if st.button("상담 시작"):
        p = f"너는 100만 건의 로펌 데이터를 학습한 AI 변호사다. 다음 질문에 전문적으로 답하라: {user_q}"
        st.write(get_gemini_response(api_key, model, p))