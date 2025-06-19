import numpy as np
import requests
import re
from datetime import datetime

from bloom_for_you.function_modules.tts import tts
from bloom_for_you.function_modules.stt import stt_with_save
import bloom_for_you.function_modules.config as config
print("[DEBUG] VEL:", config.VEL, "ACC:", config.ACC)

from bloom_for_you.function_modules import robot

# ──────── [좌표 정의] ────────
POS_TABLE = [280.28, 63.48, 250.00, 20.24, -179.96, 19.97]
POS_TABLE2 = [324.59, 8.09, 319.90, 73.11, 180.00, -13.77]
POS_ZONE1 = [108.99, -461.86, 197.16, 104.45, -178.30, -168.57]
POS_ZONE2 = [-114.80, -460.45, 197.16, 69.36, 180.00, 163.36]
POS_PLANT = [POS_TABLE, POS_ZONE1, POS_ZONE2]

# ───────── 로그 함수 ─────────
def log_voice_msg(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")

# ───────── 인증 ─────────
def authenticate() -> str | None:
    attempts = 0
    while attempts < 2:
        tts("예약번호를 말씀해주세요")
        raw = stt_with_save(duration=5)
        log_voice_msg(f"인증 시도 - 원문 인식: {raw}")

        res_num = "".join(re.findall(r"\d", raw))
        log_voice_msg(f"정제된 예약번호: {res_num}")

        if res_num in config.VALID_RESERVATIONS:
            tts("예약번호 확인 완료했습니다")
            return res_num
        else:
            attempts += 1
            if attempts < 2:
                tts("예약번호가 틀렸습니다. 다시 시도해주세요")
            else:
                tts("두 번 틀리셨습니다. 고객센터로 문의해주세요")
                return None

# ───────── 천천히 하강하며 힘 감지 후 그리퍼 여는 함수 (check_force_condition 방식) ─────────
import time
def move_flower(robot_instance, zone_number):
    log_voice_msg("화분 가져오는 중...")

    robot_instance.move(POS_PLANT[0])               # 출발점으로 이동
    robot_instance.move(POS_PLANT[zone_number])     # zone으로 이동
    time.sleep(1.0)
    robot_instance.open_grip()                      # 그리퍼 열기
    time.sleep(1.0)
    robot_instance.move_relative([0,0,-300,0,0,0])  # 아래로 30cm 내리기 (화분 잡기용)
    time.sleep(1.0)
    robot_instance.close_grip()                     # 그리퍼 닫기(집기)
    time.sleep(1.0)
    robot_instance.move(POS_PLANT[zone_number])     # 원위치 복귀(혹은 들기)
    
    # ↓ 테이블2로 이동해서, 18cm 내리기 & 그리퍼 열기
    descend_and_release(robot_instance, POS_TABLE2)

    robot_instance.move(POS_TABLE2)                 # 혹시 필요하다면 위치 고정
    robot_instance.close_grip()                     # (이 부분은 필요에 따라!)

    log_voice_msg("화분 픽업 완료")


def descend_and_release(robot_instance, start_pos):
    robot_instance.move(start_pos)                  # 테이블 위치로 이동
    robot_instance.move_relative([0, 0, -180, 0, 0, 0])  # 18cm 하강
    time.sleep(0.3)
    robot_instance.open_grip()                      # 그리퍼 열기(내려놓기)
    robot_instance.force_off()                      # force control 해제

def reverse_move_flower(robot_instance, zone_number):
    log_voice_msg("화분을 원위치로 옮기는 중...")

    robot_instance.move(POS_TABLE2)                 # 테이블 위치로 이동
    robot_instance.open_grip()                      # 혹시 열려있지 않으면 확실히 열기
    time.sleep(1.0)
    robot_instance.move_relative([0, 0, -180, 0, 0, 0])   # 18cm 아래로 내리기
    time.sleep(0.5)
    robot_instance.close_grip()                     # 집기
    time.sleep(1.0)
    robot_instance.move(POS_TABLE2)                 # 테이블로 복귀(확실히)
    robot_instance.move(POS_PLANT[zone_number])     # 원래 zone으로 이동
    robot_instance.move_relative([0, 0, -300, 0, 0, 0])   # 30cm 내려놓기
    time.sleep(0.5)
    robot_instance.open_grip()                      # 그리퍼 열기(놓기)
    robot_instance.force_off()
    log_voice_msg("화분 원위치 완료")

# ───────── 핵심 로직 (음성 메시지 받고 서버에 전송 + 화분 제어 통합) ─────────
def voice_memory_with_robot(res_num, zone_number=1):  # zone_number도 받게 변경!
    tts("화분을 지정 위치로 가져옵니다")
    robot_instance = robot.Robot()
    move_flower(robot_instance, zone_number)

    tts("문장을 남겨주세요")
    log_voice_msg("문장을 저장중..")
    log_voice_msg("마이크를 정면으로 바라보고 5초간 말씀해주세요")
    message = stt_with_save(duration=5)
    log_voice_msg(f"인식된 문장: {message}")

    audio_path = "/home/kim/ros2_ws/src/bloom_for_you/install/bloom_for_you/lib/python3.10/site-packages/message.wav"
    np.save("message.npy", np.array([message], dtype=object))
    log_voice_msg("message.npy로 저장 완료")

    try:
        with open(audio_path, 'rb') as audio_file:
            files = {'audio': audio_file}
            data = {'res_num': str(res_num), 'message': message}
            resp = requests.post(config.LOCAL_SIGNAL_URL, files=files, data=data)
            resp.raise_for_status()
            log_voice_msg("로컬 신호 전송 완료")
    except Exception as e:
        log_voice_msg(f"로컬 신호 전송 실패: {e}")

    tts("메시지가 저장되었습니다. 화분을 다시 제자리에 놓겠습니다.")
    log_voice_msg("화분 이동중..")
    tts("모든 작업이 끝났습니다.")
    time.sleep(3)   # 3초 대기

    reverse_move_flower(robot_instance, zone_number)  # 역동작 수행
    log_voice_msg("화분 원위치 완료")
    return True

# ───────── ROS2: /flower_info 토픽 리스너 & 응답 퍼블리셔 ─────────
import rclpy
from rclpy.node import Node
from bloom_for_you_interfaces.msg import FlowerInfo

class VoiceMemoryTopicNode(Node):
    def __init__(self):
        super().__init__('voice_memory_topic_node')
        self.sub = self.create_subscription(
            FlowerInfo, 'flower_info', self.callback, 10
        )
        self.pub = self.create_publisher(
            FlowerInfo, 'flower_info', 10
        )
        self.get_logger().info("음성 memory 토픽 노드 준비 완료!")

    def callback(self, msg):
        if msg.command == 10:
            self.get_logger().info(f"[음성 녹음] 요청 감지! (id={msg.id})")
            # ----- [중복 이동 제거: 아래 2줄 삭제] -----
            # robot_instance = robot.Robot()
            # move_flower(robot_instance, msg.zone_number)
            # --------------------------------------
            # 메시지 저장, 응답 publish 로직은 그대로 (zone_number도 전달)
            success = voice_memory_with_robot(res_num=msg.id, zone_number=msg.zone_number)
            response = FlowerInfo()
            response.id = msg.id
            response.command = 11
            response.zone_number = msg.zone_number
            response.flower_name = msg.flower_name
            response.flower_meaning = msg.flower_meaning
            response.growth_duration_days = msg.growth_duration_days
            response.watering_cycle = msg.watering_cycle
            response.growth_state = msg.growth_state
            self.pub.publish(response)
            self.get_logger().info(f"응답: command=11 퍼블리시 완료!")

# ───────── 메인 진입점 ─────────
def main():
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'ros':
        if not rclpy.ok():
            rclpy.init()
        node = VoiceMemoryTopicNode()
        try:
            rclpy.spin(node)
        finally:
            node.destroy_node()
            rclpy.shutdown()
    else:
        voice_memory_with_robot()

if __name__ == "__main__":
    main()
