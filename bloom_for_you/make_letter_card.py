import os
import numpy as np
import openai
import qrcode
from io import BytesIO
import base64
from collections import Counter, defaultdict
from datetime import datetime

import rclpy
from rclpy.node import Node
from bloom_for_you_interfaces.srv import CardSrv

# === 경로 설정 ===
BASE = os.path.dirname(os.path.abspath(__file__))
WS_ROOT = os.path.abspath(os.path.join(BASE, "..", ".."))
PERSONAL_ROOT = os.path.join(WS_ROOT, "personal_folder")

# === (수정된 부분) NAMESPACE_ROOT: npy 파일 위치 ===
NAMESPACE_ROOT = os.path.abspath(os.path.join(BASE, ".."))  # src/bloom_for_you

# === GPT API로 "명사/동사"만 추출 ===
def extract_keywords_gpt(text, openai_api_key=None):
    prompt = (
        f'"{text}" 이 문장에서 **존재하는** 명사 또는 동사만 뽑아줘. '
        "실제 한국어 사전에 등재된 단어만. 3~4개로 콤마(,)로 구분해서 주고, 반드시 실제 단어만 줘."
    )
    resp = openai.ChatCompletion.create(
        model="gpt-4o",
        api_key=openai_api_key,
        messages=[{"role": "user", "content": prompt}]
    )
    kw_line = resp.choices[0].message.content.strip()
    keywords = [k.strip() for k in kw_line.split(',') if k.strip()]
    return keywords

# === QR코드 base64 변환: 사이트 메인으로 이동 ===
def qr_img_base64():
    url = "http://192.168.10.77:5000/"
    qr = qrcode.make(url)
    buf = BytesIO()
    qr.save(buf, format="PNG")
    img_b64 = base64.b64encode(buf.getvalue()).decode()
    return f'<img src="data:image/png;base64,{img_b64}" width="130"/>'

# === 카드 생성 메인 함수 ===
def make_letter_card(res_num, openai_api_key=None):
    npy_path = os.path.join(NAMESPACE_ROOT, f"messages_{res_num}.npy")  # <--- 수정!
    if not os.path.exists(npy_path):
        print(f"[ERROR] 파일 없음: {npy_path}")
        return False

    entries = list(np.load(npy_path, allow_pickle=True))

    # === 날짜별 키워드 분류 ===
    by_date = defaultdict(list)
    all_keywords = []

    for ts, msg in entries:
        # 날짜 뽑기 (타임스탬프 앞 8자리)
        date_str = str(ts)[:8]
        try:
            kws = extract_keywords_gpt(msg, openai_api_key=openai_api_key)
            by_date[date_str].extend(kws)
            all_keywords.extend(kws)
        except Exception as e:
            continue

    if not all_keywords:
        print("키워드 추출 실패 (메시지 없음 또는 API 에러)")
        return False

    # === 전체 키워드(빈도순) → QR용 (여기선 실제로 쓰이지 않지만 남겨둠) ===
    counter = Counter(all_keywords)
    sorted_keywords = [kw for kw, cnt in counter.most_common()]

    # === 카드에 예쁘게 뿌릴 HTML ===
    html_lines = [
        "<!DOCTYPE html>",
        "<html lang='ko'>",
        "<head>",
        "<meta charset='utf-8'>",
        "<title>꽃 편지 키워드 카드</title>",
        "<style>",
        "body { font-family:sans-serif; background:#faf9f6; margin:0; }",
        ".card { background:#fff; border-radius:22px; box-shadow:0 2px 14px #eee; max-width:600px; margin:60px auto; padding:50px 40px; }",
        "h1 { text-align:center; font-size:2.1rem; color:#3b5998; margin-bottom:36px; }",
        ".subtitle { color:#555; font-size:1.12rem; text-align:center; margin-bottom:22px; }",
        ".date-label { font-size:1.08rem; color:#888; margin:18px 0 8px 2px; font-weight:600; letter-spacing:2px; }",
        ".keywords-cloud { display:flex; flex-wrap:wrap; gap:18px; justify-content:center; margin:8px 0 28px 0; }",
        ".keyword-item {",
        "  background:linear-gradient(90deg, #fdeff9 0%, #e1bee7 100%);",
        "  color:#333; font-weight:600; font-size:1.18rem;",
        "  border-radius:16px; padding:12px 22px; box-shadow:0 2px 8px #ecd6e2;",
        "  transition:0.18s; letter-spacing:1.1px;",
        "  display:inline-block;",
        "}",
        ".keyword-item:hover { background:#ffe0f7; transform:scale(1.07); }",
        ".qr { text-align:center; margin:35px 0 0 0; }",
        "</style>",
        "</head>",
        "<body>",
        "<div class='card'>",
        "<h1>꽃 편지 카드</h1>",
        "<div class='subtitle'>날짜별 <b>핵심 키워드!</b> 서로 무슨 말을 했을지 맞혀보세요 🌷</div>",
    ]

    # === 날짜별로 그룹 ===
    for date_str in sorted(by_date.keys()):
        keywords_today = by_date[date_str]
        day_counter = Counter(keywords_today)
        html_lines.append(f"<div class='date-label'>{datetime.strptime(date_str,'%Y%m%d').strftime('%Y.%m.%d')}</div>")
        html_lines.append("<div class='keywords-cloud'>")
        max_cnt = max(day_counter.values())
        for kw, cnt in day_counter.most_common():
            size = 1.1 + 0.5 * (cnt / max_cnt)
            html_lines.append(f"<span class='keyword-item' style='font-size:{size}em'>{kw}</span>")
        html_lines.append("</div>")

    # === QR코드 전체 ===
    html_lines += [
        "<div class='qr'>",
        qr_img_base64(),
        "<div style='font-size:0.96rem; margin-top:6px; color:#888;'>이 카드를 사이트에서 다시 볼 수 있어요</div>",
        "</div>",
        "</div>",
        "</body>",
        "</html>"
    ]

    out_html = os.path.join(NAMESPACE_ROOT, f"letter_card_{res_num}.html")
    with open(out_html, "w", encoding="utf-8") as f:
        f.write("\n".join(html_lines))
    print(f"[letter_card] HTML 카드 저장 완료: {out_html}")
    return True

# === 서비스 서버 Node ===
class CardServiceServer(Node):
    def __init__(self):
        super().__init__('card_service_server')
        self.card_sv = self.create_service(CardSrv, 'cardsrv', self.callback)
        self.get_logger().info("카드 생성 서비스(cardsrv) 준비 완료")

    def callback(self, request, response):
        res_num = request.flowerinfo.id   # ← 여기만 수정!
        self.get_logger().info(f"카드 생성 요청: 예약번호={res_num}")
        try:
            success = make_letter_card(
                res_num, openai_api_key=os.getenv("OPENAI_API_KEY")
            )
            response.success = success
            if success:
                self.get_logger().info(f"카드 생성 완료: 예약번호={res_num}")
            else:
                self.get_logger().error(f"카드 생성 실패: 파일 없음/키워드 없음")
        except Exception as e:
            self.get_logger().error(f"카드 생성 중 에러: {e}")
            response.success = False
        return response

def main():
    rclpy.init()
    node = CardServiceServer()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

# --- 터미널에서 python3 xxxx.py [예약번호] ([API_KEY])로 직접 호출도 가능하게!
if __name__ == "__main__":
    import sys
    openai_api_key = os.environ.get("OPENAI_API_KEY") or "sk-xxx"
    # 서비스 노드 실행
    if len(sys.argv) == 1:
        main()
    # 그냥 python으로 바로 카드 생성도 지원
    else:
        res_num = sys.argv[1]
        if len(sys.argv) > 2:
            openai_api_key = sys.argv[2]
        make_letter_card(res_num, openai_api_key=openai_api_key)
