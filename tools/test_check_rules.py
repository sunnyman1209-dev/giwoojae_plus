r"""데이터 검사 규칙(plus_rules)의 작은 시험: python -I quiz_plus\tools\test_check_rules.py
가짜 문항으로 규칙이 걸려야 할 때 걸리고, 걸리지 않아야 할 때 걸리지 않는지 본다. check_plus.py도 먼저 이 시험을 돌린다.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plus_rules as R  # noqa: E402


def tb(**kw):
    """교재에서 넣은 4지선다 가짜 문항(정상)."""
    q = {"id": "tb|3-12", "origin": "교재", "src": "new", "t": "4지선다", "stem": "측정 오차의 종류가 아닌 것은?",
         "choices": ["개인 오차", "기기 오차", "환경 오차", "가공 오차"], "ans": 3,
         "ex": {"근거": "NCS 자료집", "오답": ["① 개인 오차: 측정하는 사람에 따라 생긴다."]}}
    q.update(kw)
    return q


def run():
    fails = []

    def expect(name, got, want):
        if bool(got) != want:
            fails.append(f"{name}: {'걸려야' if want else '걸리지 않아야'} 하는데 결과 {got}")

    # 1. 교재·실전모의 문항: 정답, 근거, 단답형 인정 답안
    expect("정상 교재 4지", R.textbook_errors(tb()), False)
    expect("교재 4지 정답 없음", R.textbook_errors(tb(ans=None)), True)
    expect("교재 근거 없음", R.textbook_errors(tb(ex={"근거": " "})), True)
    expect("실전모의 근거 없음", R.textbook_errors(tb(origin="실전모의", ex={})), True)
    short = tb(t="단답형", choices=None, ans=None, ansText="개인 오차", accept=["개인 오차", "개인오차"])
    expect("정상 교재 단답", R.textbook_errors(short), False)
    expect("교재 단답 인정 답안 없음", R.textbook_errors(dict(short, accept=[])), True)
    expect("교재 단답 정답 글 없음", R.textbook_errors(dict(short, ansText="")), True)
    expect("교재 계산 단위 없음", R.textbook_errors(tb(t="계산형", choices=None, ans=None, value=0.02, unit="")), True)
    expect("교재 연결 정답 없음", R.textbook_errors(tb(t="연결형", choices=None, ans=None, left=["a"], right=["b"])), True)
    expect("교재 아닌 문항은 이 규칙 밖", R.textbook_errors(tb(origin=None, ans=None)), False)

    # 2. 화면에 보이는 글의 출처 노출
    expect("정상 문항 출처 없음", R.leaks(tb()), False)
    expect("근거 칸 NCS 자료집 허용", R.leaks(tb(ex={"근거": "NCS 자료집"})), False)
    expect("지문에 교재", R.leaks(tb(stem="교재에 나온 측정 오차가 아닌 것은?")), True)
    expect("보기에 예상문제", R.leaks(tb(choices=["예상문제 3회", "b", "c", "d"])), True)
    expect("해설에 쪽수", R.leaks(tb(ex={"근거": "NCS 자료집 12쪽"})), True)
    expect("개념 상자에 회차-번호", R.leaks(tb(ex={"근거": "NCS 자료집", "개념": {"title": "오차", "body": ["3회 12번과 같다."]}})), True)
    expect("해설에 회차 번호(하이픈)", R.leaks(tb(ex={"근거": "7회-15번 참고"})), True)
    expect("인정 답안에 실전 모의고사", R.leaks(tb(t="단답형", accept=["실전 모의고사"])), True)
    expect("내부 id·origin은 화면 밖", R.leaks(tb(id="tb|3-12", origin="교재")), False)
    expect("숫자 단위는 출처 아님", R.leaks(tb(stem="회전수 1200 rpm, 이송 0.2 mm/rev일 때 3번 공구의 절삭 속도는?")), False)

    # 3. 해설의 원본 지칭(경고)
    expect("정상 해설 지칭 없음", R.refs(tb()), False)
    expect("해설에 '이 문제'", R.refs(tb(ex={"근거": "이 문제는 개인 오차를 묻는다."})), True)
    expect("해설에 '보기 ③'", R.refs(tb(ex={"근거": "보기 ③이 답이다."})), True)
    expect("해설에 '③번'", R.refs(tb(ex={"근거": "③번이 답이다."})), True)
    expect("해설에 '2번'", R.refs(tb(ex={"근거": "2번이 답이다."})), True)
    expect("해설에 '문항'", R.refs(tb(ex={"근거": "같은 문항이다."})), True)
    expect("오답 줄 앞 번호는 지칭 아님", R.refs(tb(ex={"근거": "NCS 자료집", "오답": ["③ 환경 오차: 온도에서 생긴다."]})), False)
    expect("지문의 문제는 해설 밖", R.refs(tb(stem="다음 문제에서 옳은 것은?")), False)
    return fails


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    f = run()
    print("\n".join(f) if f else "규칙 시험 통과")
    sys.exit(1 if f else 0)
