import streamlit as st
import requests
import json
import time
import random
import uuid
import database
import os 
import ast

def get_secret(key):
    """안전한 시크릿 로드 (Render 호환)"""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except:
        pass
    return os.environ.get(key)

# --- 1. 페이지 설정 & 초기화 ---
st.set_page_config(
    page_title="PT Pro: 물리치료 국가고시 AI 마스터",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# [UI 트윅] Streamlit 기본 요소 숨기기 (헤더, 푸터, 햄버거 메뉴)
hide_st_style = """
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .viewerBadge_container__1QSob {display: none;}
</style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# 사용자 ID & 상태 초기화
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

# 앱 상태 관리: 'home', 'exam', 'review_notes'
if "app_mode" not in st.session_state:
    st.session_state.app_mode = "home"

# 시험 상태 관리
if "exam_session" not in st.session_state:
    st.session_state.exam_session = {
        "questions_solved": 0,    # 현재 세션에서 푼 문제 수
        "correct_count": 0,       # 맞은 개수
        "current_q": None,        # 현재 문제 데이터
        "is_submitted": False,    # 정답 제출 여부
        "user_choice": None       # 사용자가 고른 답
    }

# [선물용 기능] 비밀번호 보호 (ACCESS_PASSWORD가 설정된 경우만)
access_password = get_secret("ACCESS_PASSWORD")

if access_password:
    if "auth_status" not in st.session_state:
        st.session_state.auth_status = False
        
    if not st.session_state.auth_status:
        st.markdown("""
        <style>
        .auth-container {
            max-width: 400px;
            margin: 100px auto;
            padding: 40px;
            background: rgba(255, 255, 255, 0.9);
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            text-align: center;
        }
        </style>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.markdown('<div class="auth-container">', unsafe_allow_html=True)
            st.title("🔒 Private Access")
            st.write("초대된 사용자만 접속할 수 있습니다.")
            pwd = st.text_input("접속 비밀번호를 입력하세요", type="password")
            
            if st.button("접속하기", type="primary"):
                if pwd == access_password:
                    st.session_state.auth_status = True
                    st.toast("환영합니다! 접속 성공 🎉")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("비밀번호가 틀렸습니다.")
            st.markdown('</div>', unsafe_allow_html=True)
        st.stop() # 비밀번호 맞을 때까지 아래 코드 실행 중단

# 데이터베이스 초기화
if "db_initialized" not in st.session_state:
    database.init_db()
    st.session_state.db_initialized = True

# --- 2. Ultra Premium CSS 스타일 (Glassmorphism + Gradient) ---
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    /* 기본 배경 및 폰트 */
    .stApp {
        background: linear-gradient(120deg, #fdfbfb 0%, #ebedee 100%);
        font-family: 'Pretendard', sans-serif;
    }
    
    /* 헤더 스타일 */
    .header-container {
        padding: 40px 20px;
        text-align: center;
        background: linear-gradient(90deg, #6a11cb 0%, #2575fc 100%);
        color: white;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(37, 117, 252, 0.3);
        margin-bottom: 40px;
    }
    .header-title {
        font-size: 2.8rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -1px;
    }
    .header-subtitle {
        font-size: 1.1rem;
        opacity: 0.9;
        margin-top: 10px;
        font-weight: 400;
    }

    /* 카드 공통 스타일 (Glassmorphism) */
    .card {
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 30px;
        box-shadow: 0 8px 32px rgba(31, 38, 135, 0.07);
        border: 1px solid rgba(255, 255, 255, 0.18);
        margin-bottom: 25px;
        transition: transform 0.3s ease;
    }
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px rgba(31, 38, 135, 0.12);
    }
    
    /* 문제 텍스트 */
    .question-box {
        font-size: 1.4rem;
        font-weight: 700;
        color: #2d3436;
        line-height: 1.6;
        margin-bottom: 20px;
    }
    
    /* 뱃지 스타일 */
    .category-badge {
        background: linear-gradient(45deg, #00b09b, #96c93d);
        color: white;
        padding: 5px 15px;
        border-radius: 50px;
        font-size: 0.85rem;
        font-weight: 700;
        display: inline-block;
        margin-bottom: 15px;
        box-shadow: 0 4px 10px rgba(150, 201, 61, 0.3);
    }

    /* 점수판 */
    .score-board {
        text-align: center;
        font-size: 1.2rem;
        font-weight: 700;
        color: #6c5ce7;
        margin-bottom: 20px;
        padding: 10px;
        background: #f1f2f6;
        border-radius: 15px;
    }

    /* 정답/오답 박스 */
    .result-box {
        padding: 20px;
        border-radius: 15px;
        margin-top: 20px;
        animation: fadeIn 0.5s ease-out;
    }
    .correct { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    .wrong { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* 버튼 커스터마이징 */
    .stButton button {
        border-radius: 12px;
        font-weight: 600;
        padding: 0.5rem 1rem;
        transition: all 0.2s;
    }
    /* Primary 버튼 (그라데이션) */
    .stButton button[kind="primary"] {
        background: linear-gradient(90deg, #6a11cb 0%, #2575fc 100%);
        border: none;
        box-shadow: 0 4px 15px rgba(37, 117, 252, 0.4);
    }
    .stButton button[kind="primary"]:hover {
        opacity: 0.9;
        transform: scale(1.02);
    }
</style>
""", unsafe_allow_html=True)

import random

# --- 3. 로직 함수 (API & Helper) ---
SUBJECTS = [
    "물리치료 기초",
    "물리치료 진단평가",
    "물리치료 중재",
    "의료관계법규",
    "물리치료 실기"
]

def generate_exam_batch(api_keys_list, count=20):
    """
    한 번의 요청으로 20문제를 생성하여 리스트로 반환합니다.
    (단순/고속 모드: 키 순환 후 실패 시 즉시 종료)
    """
    if not api_keys_list: return None
        
    shuffled_keys = list(api_keys_list)
    random.shuffle(shuffled_keys)
    
    last_error = "Unknown Error"
    
    # 키 하나씩 시도
    for i, api_key in enumerate(shuffled_keys):
        try:
            # 1. 모델 찾기
            list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            resp = requests.get(list_url, timeout=5)
            
            if resp.status_code == 200:
                models = resp.json().get('models', [])
            else:
                last_error = f"Key #{i+1} List Error {resp.status_code}"
                continue
            
            valid_model_name = None
            # Flash 모델 우선
            for m in models:
                 if 'flash' in m.get('name', '').lower() and 'generateContent' in m.get('supportedGenerationMethods', []):
                     valid_model_name = m.get('name'); break
            
            # 없으면 아무거나
            if not valid_model_name:
                for m in models:
                    if 'generateContent' in m.get('supportedGenerationMethods', []):
                        valid_model_name = m.get('name'); break
            
            if not valid_model_name: 
                last_error = f"Key #{i+1} No Model Found"
                continue
            
            # 2. 배치 생성 요청
            generate_url = f"https://generativelanguage.googleapis.com/v1beta/{valid_model_name}:generateContent?key={api_key}"
            
            prompt = f"""
            당신은 대한민국 물리치료사 국가고시 출제 위원입니다.
            [물리치료 기초, 진단평가, 중재, 의료관계법규, 실기] 전 범위에서
            총 {count}개의 객관식 문제를 출제하여 JSON 리스트로 반환하세요.
            
            [조건]
            1. 난이도: 실제 국시 합격률 40% 수준의 변별력 있는 문제
            2. 각 과목을 골고루 분배하세요.
            3. 5지 선다형
            
            [응답 형식]
            반드시 아래와 같은 JSON 배열 포맷만 출력하세요. (Markdown codeblock 금지)
            [
              {{
                "category": "과목명",
                "question": "1. 문제 내용...",
                "options": ["보기1", "보기2", "보기3", "보기4", "보기5"],
                "answer": 0,
                "explanation": "해설..."
              }},
              ... 
            ]
            """
            
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            if "1.5" in valid_model_name:
                payload["generationConfig"] = {"response_mime_type": "application/json"}
                
            headers = {'Content-Type': 'application/json'}
            
            # 타임아웃 180초 (3분) - 대량 생성이라 시간 필요
            r = requests.post(generate_url, headers=headers, json=payload, timeout=180)
            
            if r.status_code == 200:
                text = r.json()['candidates'][0]['content']['parts'][0]['text']
                text = text.replace("```json", "").replace("```", "").strip()
                
                # 리스트 파싱
                start = text.find("["); end = text.rfind("]")
                if start != -1 and end != -1:
                    data_list = json.loads(text[start:end+1])
                    
                    clean_list = []
                    for item in data_list:
                        if not all(k in item for k in ('question', 'options', 'answer')): continue
                        ans = item.get('answer')
                        if isinstance(ans, int):
                            if ans > 4: item['answer'] = ans % 5
                            elif ans >= 1: item['answer'] = ans - 1
                        clean_list.append(item)
                        
                    if len(clean_list) > 0:
                        return clean_list
                
                last_error = f"Key #{i+1} JSON Parse Error"
                continue
            
            elif r.status_code == 429:
                last_error = f"Key #{i+1} Quota Exceeded (429)"
                continue # 다음 키로 바로 넘어감
            else:
                last_error = f"Key #{i+1} Error {r.status_code}"
                continue
                
        except Exception as e:
            last_error = str(e)
            continue
            
    st.error(f"⚠️ 문제 생성 실패: {last_error} (잠시 후 다시 시도해주세요)")
    return None

# --- 4. 사이드바 (Secrets 연동 - 다중 키 지원) ---
with st.sidebar:
    st.header("⚙️ 설정")
    
    api_keys = []
    
    # 1. 시크릿/환경변수 로드 통합 (Helper 함수 사용)
    # 다중 키 ("GEMINI_API_KEYS")
    val_list = get_secret("GEMINI_API_KEYS")
    val_single = get_secret("GEMINI_API_KEY")
    
    if val_list:
        if isinstance(val_list, list): api_keys = val_list
        elif isinstance(val_list, str):
            try:
                # ["key1", "key2"] 꼴의 문자열 파싱 (Render 환경변수)
                import ast
                parsed = ast.literal_eval(val_list)
                if isinstance(parsed, list): api_keys = parsed
                elif isinstance(parsed, str): api_keys = [parsed]
            except:
                # 콤마로 분리
                api_keys = [k.strip() for k in val_list.split(",") if k.strip()]
                
    elif val_single:
        # 단일 키 호환
        api_keys = [val_single]

    if api_keys:
        st.success(f"✅ 클라우드 키 {len(api_keys)}개 대기중")
    else:
        user_input_key = st.text_input("Gemini API Key", type="password")
        if user_input_key: api_keys = [user_input_key]
    
    daily_limit = 20
    is_allowed, current_count = database.check_usage(st.session_state.user_id, daily_limit)
    
    st.markdown("---")
    st.markdown(f"📊 **일일 사용량: {current_count} / {daily_limit}**")
    st.progress(min(current_count / daily_limit, 1.0))
    
    st.markdown("---")
    if st.button("🏠 홈으로"):
        st.session_state.app_mode = "home"
        st.rerun()
        
    if st.button("📓 오답노트"):
        st.session_state.app_mode = "review"
        st.rerun()

# --- 5. UI 구성 ---

# 헤더
st.markdown("""
<div class="header-container">
    <div class="header-title">PT PRO MASTER</div>
    <div class="header-subtitle">물리치료사 국가고시 합격을 위한 완벽한 AI 파트너</div>
</div>
""", unsafe_allow_html=True)

if not api_keys:
    st.warning("🔒 API 키가 필요합니다. (Secrets를 설정하거나 키를 입력하세요)")
    st.stop()

# [모드: 홈]
if st.session_state.app_mode == "home":
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="card" style="text-align:center;">', unsafe_allow_html=True)
        st.markdown("### 👋 오늘의 모의고사 (20문제)")
        st.write("한 번 클릭으로 국시 전 과목 모의고사를 생성합니다.")
        st.markdown(f"**현재 점수: {st.session_state.exam_session.get('correct_count', 0)}점**")
        
        # 시작 버튼
        if st.button("🚀 20문제 전체 생성 및 시작", type="primary"):
            if not is_allowed:
                st.error("🚫 오늘의 학습량을 모두 사용했습니다.")
            else:
                with st.spinner("🔄 AI가 20문제를 정성껏 출제하고 있습니다... (약 10~20초 소요)"):
                    # 배치 생성 호출
                    questions = generate_exam_batch(api_keys, count=20)
                    
                    if questions:
                        st.session_state.exam_session = {
                            "questions_list": questions, # 전체 문제 리스트
                            "current_idx": 0,           # 현재 문제 인덱스
                            "correct_count": 0,
                            "is_submitted": False,
                            "user_choice": None
                        }
                        # 사용량 한 번에 증가
                        database.increment_usage(st.session_state.user_id, amount=len(questions))
                        st.session_state.app_mode = "exam"
                        st.rerun()
                    else:
                        st.error("생성 실패! 잠시 후 다시 시도해주세요.")
            
        st.markdown('</div>', unsafe_allow_html=True)

# [모드: 시험]
elif st.session_state.app_mode == "exam":
    session = st.session_state.exam_session
    q_list = session.get("questions_list", [])
    idx = session.get("current_idx", 0)
    
    # 예외 처리: 문제가 없을 때
    if not q_list or idx >= len(q_list):
        st.balloons()
        st.success(f"🎉 모든 문제를 풀었습니다! 최종 점수: {session['correct_count']} / {len(q_list)}")
        if st.button("메인으로 돌아가기"):
            st.session_state.app_mode = "home"
            st.rerun()
        st.stop()

    # 현재 문제 가져오기 (API 호출 X, 메모리에서 가져옴)
    q = q_list[idx]
    
    # 레이아웃: 점수판 & 진행률
    st.markdown(f'<div class="score-board">🏆 문제 {idx + 1} / {len(q_list)} (현재 득점: {session["correct_count"]})</div>', unsafe_allow_html=True)
    
    # 문제 카드
    st.markdown(f"""
    <div class="card">
        <span class="category-badge">{q.get('category')}</span>
        <div class="question-box">Q. {q.get('question')}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # 보기 영역
    options = q.get('options', [])
    
    with st.container():
        # 상태에 따라 key를 다르게 주어 리셋 방지 or 리셋 유도
        choice_idx = st.radio(
            "정답을 선택하세요:", 
            range(len(options)), 
            format_func=lambda i: options[i],
            key=f"q_{idx}", # 문제마다 키가 달라야 함
            index=None,
            disabled=session['is_submitted']
        )
        
        st.write("") 
        
        if not session['is_submitted']:
            if st.button("✅ 정답 제출", type="primary"):
                if choice_idx is None:
                    st.toast("답을 골라주세요!", icon="⚠️")
                else:
                    session['is_submitted'] = True
                    session['user_choice'] = choice_idx
                    
                    correct_idx = q.get('answer', 0)
                    if choice_idx == correct_idx:
                        session['correct_count'] += 1
                        st.balloons()
                    else:
                        database.add_review_note(st.session_state.user_id, q.get('category'), q.get('question'), options, correct_idx, q.get('explanation'))
                    st.rerun()
        else:
            # 결과 표시
            user_pick = session['user_choice']
            correct_pick = q.get('answer', 0)
            
            if user_pick == correct_pick:
                st.markdown(f'<div class="result-box correct">🎉 <b>정답입니다!</b></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="result-box wrong">❌ <b>오답입니다.</b> (선택: {options[user_pick]})<br>👉 정답: <b>{options[correct_pick]}</b></div>', unsafe_allow_html=True)
            
            with st.expander("📚 해설 보기", expanded=True):
                st.info(q.get('explanation'))
                
            col_nxt1, col_nxt2 = st.columns([4, 1])
            with col_nxt2:
                if st.button("다음 문제 ➡️", type="primary"):
                    session['current_idx'] += 1
                    session['is_submitted'] = False
                    session['user_choice'] = None
                    st.rerun()

# [모드: 오답노트]
elif st.session_state.app_mode == "review":
    st.markdown('<div class="header-container" style="padding:20px; font-size:1.5rem;">📓 오답노트 복습</div>', unsafe_allow_html=True)
    
    notes = database.get_review_notes(st.session_state.user_id)
    if not notes:
        st.success("🎉 저장된 오답이 없습니다. 훌륭해요!")
    else:
        for i, note in enumerate(notes):
            with st.expander(f"[{note['category']}] {note['question'][:40]}..."):
                st.markdown(f"**Q. {note['question']}**")
                st.markdown(f"**정답:** {note['options'][note['answer']]}")
                st.markdown(f"**해설:** {note['explanation']}")
                if st.button("완벽히 이해했음 (삭제)", key=f"del_{i}"):
                    database.delete_review_note(st.session_state.user_id, note['question'])
                    st.rerun()
