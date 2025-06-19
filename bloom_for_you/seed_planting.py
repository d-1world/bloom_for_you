import rclpy
from rclpy.node import Node
from bloom_for_you_interfaces.msg import FlowerInfo
from bloom_for_you.function_modules import robot
from bloom_for_you.function_modules import yolo
from bloom_for_you.function_modules.tts import tts
import DR_init
import time
from bloom_for_you.function_modules.onrobot_ import RG

CMD_SEED = 2    # 씨앗 심기 노드 실행
FINISH_SEED = 3 # 씨앗 심기 완료

POS_SEED1 = [642.63,96.38,134.88,8.01,-180.00,7.71]         # 씨앗1 위치
POS_SEED2 = [642.64,-68.62,134.90,17.35,180.00,17.05]       # 씨앗2 위치(튤립)
POS_SEED3 = [642.62,-228.98,134.89,160.31,180.00,160.02]    # 씨앗3 위치(해바라기)

POS_TABLE = [280.28, 63.48, 187.74, 20.24, -179.96, 19.97]      # 화분 위치
POS_ZONE1 = [108.99, -461.86, 197.16, 104.45, -178.30, -168.57] # 플랜트 존 위치1(왼쪽)
POS_ZONE2 = [-114.80, -460.45, 197.16, 69.36, 180.00, 163.36]   # 플랜트 존 위치2(오른쪽)
POS_TABLE2 = [324.59, 8.09, 330.00, 73.11, 180.00, -13.77]

POS_PLANT = [POS_TABLE, POS_ZONE1, POS_ZONE2, POS_SEED1, POS_SEED2, POS_SEED3]

GRIPPER_NAME = "rg2"
TOOLCHARGER_IP = "192.168.1.1"
TOOLCHARGER_PORT = "502"
MAX_ATTEMPTS = 3 # 최대 재시도 횟수

class SeedPlanting(Node):
    def __init__(self):
        super().__init__('seed_planting')
        self.cmd_sub = self.create_subscription(FlowerInfo, 'flower_info', self.cmd_callback, 10)
        self.cmd_pub = self.create_publisher(FlowerInfo, 'flower_info', 10)
        self.robot_instance = robot.Robot()
        self.yolo_instance = yolo.Yolo()
        self.gripper_instance = RG(GRIPPER_NAME, TOOLCHARGER_IP, TOOLCHARGER_PORT)

    def cmd_callback(self, msg):     
        self.command = msg.command
        if self.command != CMD_SEED:
            return
        self.id = msg.id
        self.zone_number = msg.zone_number
        self.flower_name = msg.flower_name
        self.flower_meaning = msg.flower_meaning
        self.growth_duration_days = msg.growth_duration_days
        self.watering_cycle = msg.watering_cycle
        self.growth_state = msg.growth_state
        
        self.robot_instance.move_home()
        self.robot_instance.close_grip()
        tts("씨앗 심기를 시작합니다")
        self.get_logger().info("씨앗 심기를 시작합니다.")

        self.pickup_zone()
        self.move_seed()    # 씨앗 위치로 이동
        self.pickup_seed()  # 씨앗 집기
        self.plant_seed()   # 씨앗 심기
        self.move_zone()    # 화분 이동
        self.end_planting()   # 종료 알림

    def pickup_zone(self):
        self.get_logger().info('화분을 가져오는 중...')
        tts("화분을 가져오는 중...")
        self.robot_instance.move_relative([0.0, 0.0, 50.0, 0.0, 0.0, 0.0])  # 살짝 위로 올라가기
        time.sleep(1.0)
        self.robot_instance.move(POS_PLANT[self.zone_number])
        time.sleep(1.0)
        self.robot_instance.open_grip()
        time.sleep(1.0)
        self.robot_instance.move_relative([0.0, 0.0, -300.0, 0.0, 0.0, 0.0])
        time.sleep(1.0)
        self.robot_instance.close_grip()
        time.sleep(1.0)
        self.robot_instance.move(POS_PLANT[self.zone_number])
        time.sleep(1.0)
        self.robot_instance.move_relative([0.0, 0.0, 120.0, 0.0, 0.0, 0.0])

        self.robot_instance.move(POS_TABLE2)
        time.sleep(1.0)
        self.robot_instance.move_relative([0.0, 0.0, -200.0, 0.0, 0.0, 0.0])
        time.sleep(1.0)
        self.robot_instance.open_grip()
        time.sleep(1.0)
        self.robot_instance.move(POS_TABLE2)
        self.robot_instance.close_grip()

        self.get_logger().info('화분 픽업 완료')


    def move_seed(self):
        if self.flower_name == "해바라기":
            self.get_logger().info('해바라기 씨앗 바구니로 이동 중...')
            tts("해바라기 씨앗 바구니로 이동합니다")
            self.robot_instance.move(POS_PLANT[5])
        elif self.flower_name == "튤립":
            self.get_logger().info('튤립 씨앗 바구니로 이동 중...')
            tts("튤립 씨앗 바구니로 이동합니다")
            self.robot_instance.move(POS_PLANT[4])
        else:
            self.get_logger().info('원하시는 씨앗이 없습니다.')
            tts("원하시는 씨앗이 없습니다")

    def pickup_seed(self):
        self.get_logger().info('씨앗 가져오는 중...')
        tts("씨앗을 가져옵니다")
        

        attempt = 0
        success = False
        # 예외사항
        while attempt < MAX_ATTEMPTS and not success:
            print(f"[시도 {attempt+1}] YOLO로 감지 중...")

            self.robot_instance.open_grip()
            time.sleep(1.0)
            
            # YOLO로 객체 위치 감지 및 이동
            target = "씨앗"
            x = 0
            y = 10
            z = -9
            self.yolo_instance.grip_target(target, x, y, z)
            time.sleep(7.0)

            # 그리퍼 닫기
            self.robot_instance.close_grip()
            time.sleep(1.0)

            # 그리퍼 상태 확인
            grip_status = self.gripper_instance.get_status()[1]
            if grip_status == 1:
                print("물체를 성공적으로 집었습니다.")
                success = True
                # 위로 이동
                self.robot_instance.move_relative([0.0, 0.0, 100.0, 0.0, 0.0, 0.0])
                time.sleep(1.0)
                    
            else:
                print("물체를 집지 못했습니다. 다시 감지 시도합니다.")
                attempt += 1
                self.robot_instance.move_relative([0.0, 0.0, 50.0, 0.0, 0.0, 0.0])
                if self.flower_name == "해바라기":
                    self.robot_instance.move(POS_PLANT[5])
                elif self.flower_name == "튤립":
                    self.robot_instance.move(POS_PLANT[4])
                time.sleep(1.0)  # 재시도 전 잠시 대기

        if attempt == 3:
            tts("관리자 호출 합니다")
        
    def plant_seed(self):
        self.get_logger().info('씨앗 운반 중...')
        tts("씨앗을 운반합니다")
        self.robot_instance.move_home()
        time.sleep(1.0)

        # yolo 이동
        self.get_logger().info('씨앗 심는 중...')
        tts("씨앗을 심습니다")
        target = "화분"
        x = -10
        y = 10
        z = 110
        self.yolo_instance.grip_target(target,x, y,z)
        time.sleep(5.0)
        self.robot_instance.open_grip() # 씨앗 심기

    def move_zone(self):
        self.get_logger().info('화분 운반 중...')
        tts("화분을 운반합니다")
        self.robot_instance.move_relative([-60.0, 0.0, 0.0, 0.0, 0.0, 0.0])  # 집기 위한 위치 맞추기
        self.robot_instance.move_relative([0.0, 0.0, -20.0, 0.0, 0.0, 0.0])  # 집기 위해 살짝 내려가기
        self.robot_instance.close_grip()
        self.robot_instance.move_relative([0.0, 0.0, 100.0, 0.0, 0.0, 0.0])  # 살짝 위로 올라가기

        self.robot_instance.move(POS_PLANT[self.zone_number])
        self.robot_instance.move_relative([0.0, 0.0, -250.0, 0.0, 0.0, 0.0])  # 살짝 밑으로 내려가기
        time.sleep(1.0)
        self.robot_instance.force_on_z(-10) # z축 방향 힘
        time.sleep(1.0)
        self.robot_instance.check_touch(max=14)   # 힘 감지시 정지
        time.sleep(1.0)
        self.robot_instance.open_grip()

        # 복귀
        self.get_logger().info('복귀 중...')
        self.robot_instance.move(POS_PLANT[self.zone_number])
        self.robot_instance.move_home()
        self.robot_instance.close_grip()

    def end_planting(self):
        msg = FlowerInfo()
        msg.id = self.id
        msg.command = self.command + 1
        msg.zone_number = self.zone_number
        msg.flower_name = self.flower_name
        msg.flower_meaning = self.flower_meaning
        msg.growth_duration_days = self.growth_duration_days
        msg.watering_cycle = self.watering_cycle
        msg.growth_state = 0  # 꽃 성장 상태 

        self.cmd_pub.publish(msg)
        self.get_logger().info('전송 완료')

    
def main(args=None):
    node = SeedPlanting()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        # if rclpy.ok():  # shutdown이 이미 되지 않았을 때만 호출
        #     rclpy.shutdown()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
