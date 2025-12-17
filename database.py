import sqlite3
from datetime import datetime

DB_FILE = "usage_data.db"

def init_db():
    """데이터베이스 및 테이블 초기화"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # 사용량 추적 테이블: 사용자ID(여기선 간단히 날짜별 통합 카운트 사용), 날짜, 횟수
    # 실제 배포 환경(Streamlit Cloud)에서는 IP 추적이 어렵거나 공유되므로,
    # 여기서는 '로컬 사용자' 기준으로 브라우저 세션 키나 단순 일일 전체 제한으로 구현합니다.
    # 사용자별 구분을 위해선 uuid를 session_state에 저장해서 key로 씁니다.
    c.execute('''
        CREATE TABLE IF NOT EXISTS usage_logs (
            user_id TEXT,
            date_str TEXT,
            count INTEGER,
            PRIMARY KEY (user_id, date_str)
        )
    ''')
    
    # [추가] 오답노트 테이블
    c.execute('''
        CREATE TABLE IF NOT EXISTS review_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            category TEXT,
            question TEXT,
            options TEXT,
            answer INTEGER,
            explanation TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_today_str():
    return datetime.now().strftime("%Y-%m-%d")

# [수정] 일일 제한 20회로 증가
def check_usage(user_id, daily_limit=20):
    """오늘 사용량이 한도를 초과했는지 확인"""
    today = get_today_str()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute('SELECT count FROM usage_logs WHERE user_id = ? AND date_str = ?', (user_id, today))
    row = c.fetchone()
    conn.close()
    
    if row:
        current_count = row[0]
        return current_count < daily_limit, current_count
    else:
        return True, 0

def increment_usage(user_id, amount=1):
    """사용량 증가 (기본 1, 배치 생성 시 amount 만큼)"""
    today = get_today_str()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute('SELECT count FROM usage_logs WHERE user_id = ? AND date_str = ?', (user_id, today))
    row = c.fetchone()
    
    if row:
        c.execute('UPDATE usage_logs SET count = count + ? WHERE user_id = ? AND date_str = ?', (amount, user_id, today))
    else:
        c.execute('INSERT INTO usage_logs (user_id, date_str, count) VALUES (?, ?, ?)', (user_id, today, amount))
        
    conn.commit()
    conn.close()

# [추가] 오답노트 관련 함수
def add_review_note(user_id, category, question, options_list, answer_idx, explanation):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # options 리스트는 문자열로 변환해서 저장 (,로 구분하되 간단히 repr 사용)
    import json
    options_str = json.dumps(options_list, ensure_ascii=False)
    
    c.execute('''
        INSERT INTO review_notes (user_id, category, question, options, answer, explanation)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, category, question, options_str, answer_idx, explanation))
    conn.commit()
    conn.close()

def get_review_notes(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT category, question, options, answer, explanation, timestamp FROM review_notes WHERE user_id = ? ORDER BY timestamp DESC', (user_id,))
    rows = c.fetchall()
    conn.close()
    
    notes = []
    import json
    for r in rows:
        notes.append({
            "category": r[0],
            "question": r[1],
            "options": json.loads(r[2]),
            "answer": r[3],
            "explanation": r[4],
            "timestamp": r[5]
        })
    return notes

def delete_review_note(user_id, question):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM review_notes WHERE user_id = ? AND question = ?', (user_id, question))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
