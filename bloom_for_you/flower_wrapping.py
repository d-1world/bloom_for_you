import os
import time
import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_share_directory

from bloom_for_you.function_modules.tts import tts
from bloom_for_you_interfaces.msg import FlowerInfo
from bloom_for_you_interfaces.srv import CardSrv
from bloom_for_you.function_modules import robot

########### FlowerWrapping ############

CMD_START_WRAPPING = 20
CMD_PRINT_CARD = 21
CMD_END_WRAPPING = 22

POS_TABLE = [280.28, 63.48, 250.00, 20.24, -179.96, 19.97]
POS_TABLE2 = [324.59, 8.09, 330.00, 73.11, 180.00, -13.77]
POS_ZONE1 = [108.99, -461.86, 197.16, 104.45, -178.30, -168.57]
POS_ZONE2 = [-114.80, -460.45, 197.16, 69.36, 180.00, 163.36]
POS_PLANT = [POS_TABLE, POS_ZONE1, POS_ZONE2]

# POS_READY = [367.41, 8.00, 247.25, 20.15, -180.00, 20.00]
POS_BAG = [360.00, -325.51, 225.75, 124.00, 180.00, -144.00] # 75 다운
POS_BAG_DES = [350.00, 230.00, 345.00, 26.91, -180.00, 118.81]
POS_CARD1 = [544.50, 247.54, 247.95, 55.85, 180.00, 150.87]
POS_CARD2 = [544.50, 70.00, 247.95, 169.0, 180.00, -96.08]
POS_CARD3 = [308.48, -8.55, 348.27, 12.91, -180.00, 14.34] #3 100 다운
POS_CARD = [POS_CARD1,POS_CARD2,POS_CARD3]
POS_PICKUP = []

POT = "화분"
# BABY = ["해바라기새싹", "튤립새싹"]
FLOWER = ["해바라기", "튤립"]


class FlowerWrapping(Node):
    def __init__(self):
        super().__init__("wrapping_node")
        self.cmd_sub = self.create_subscription(FlowerInfo, 'flower_info', self.wrap_flower, 10)
        self.cmd_pub = self.create_publisher(FlowerInfo, 'flower_info',qos_profile=10)
        self.card_cli = self.create_client(CardSrv,'cardsrv')
        self.robot = robot.Robot()
        
        self.robot.move_home()
        self.robot.close_grip()


    def wrap_flower(self, msg):
        self.command = msg.command
        if self.command != CMD_START_WRAPPING:
            return
        
        self.id = msg.id
        self.zone_number = msg.zone_number
        self.flower_name = msg.flower_name
        self.flower_meaning = msg.flower_meaning
        self.growth_duration_days = msg.growth_duration_days
        self.watering_cycle = msg.watering_cycle
        self.growth_state = msg.growth_state

        tts("포장을 시작합니다.")
        self.get_logger().info("포장을 시작합니다.")

        # self._get_bag()
        # self._get_flower()
        # self._insert_card()
        self._get_card()
        # self._offer_bag()

        tts('포장이 완료되었습니다.')
        self.get_logger().info("포장이 완료되었습니다.")


    def _get_bag(self):
        self.get_logger().info("쇼핑백 가져오는 중...")

        self.robot.move(POS_BAG)
        self.robot.open_grip()
        time.sleep(1)
        self.robot.move_relative([0,0,-75,0,0,0])
        self.robot.close_grip()
        time.sleep(1)
        # self.robot.move_relative([0,0,200,0,0,0])
        self.robot.move(POS_BAG)
        self.robot.move(POS_BAG_DES)
        self.robot.move_relative([0,0,-75,0,0,0])
        time.sleep(1)
        self.robot.force_on_z(-10)
        self.robot.check_touch(max=10)
        self.robot.force_off()

        self.robot.open_grip()
        time.sleep(1)
        self.robot.move_relative([0,0,50,0,0,0])
        self.robot.move(POS_PLANT[0])
        self.robot.close_grip()

        self.get_logger().info("쇼핑백 픽업 완료")
        

    def _get_flower(self):
        self.get_logger().info("화분 가져오는 중...")
        
        self.robot.move(POS_PLANT[0])

        self.robot.move(POS_PLANT[self.zone_number])
        time.sleep(1.0)
        self.robot.open_grip()
        time.sleep(1.0)
        self.robot.move_relative([0,0,-300,0,0,0])
        time.sleep(1.0)
        self.robot.close_grip()
        time.sleep(1.0)
        self.robot.move(POS_PLANT[self.zone_number])
        time.sleep(1.0)
        self.robot.move_relative([0,0,120,0,0,0])
        self.robot.move(POS_TABLE2)
        time.sleep(1.0)
        # self.robot.move_relative([0,0,-20,0,0,0])
        self.robot.move_relative([0,0,-200,0,0,0])
        time.sleep(1.0)
        # self.robot.force_on_z(-10)
        # time.sleep(1.0)
        # self.robot.check_touch(min=5, max=30)
        # time.sleep(1.0)
        self.robot.open_grip()
        time.sleep(1.0)
        self.robot.move(POS_TABLE2)
        self.robot.close_grip()

        self.get_logger().info("화분 픽업 완료")
        

    def _get_card(self):
        while not self.card_cli.wait_for_service(timeout_sec = 0.1):
            self.get_logger().warning("카드 서버 준비 안됨")

        future = self.request_card_print()
        future.add_done_callback(self._card_done_callback)
        

    def _insert_card(self):
        self.get_logger().info("카드 넣는 중...")
        self.robot.move(POS_PLANT[0])
        time.sleep(1.0)
        self.robot.move_relative([200,0,0,0,0,0])
        time.sleep(1.0)
   
        self.robot.move(POS_CARD1)
        time.sleep(1.0)
        self.robot.open_grip()
        time.sleep(1.0)
        self.robot.move_relative([0,0,-160,0,0,0])
        self.robot.close_grip()
        time.sleep(1.0)
        self.robot.move(POS_CARD1)
        time.sleep(1.0)
        self.robot.move(POS_CARD2)
        time.sleep(1.0)
        self.robot.move(POS_CARD3)
        time.sleep(1.0)
        self.robot.move_relative([0,0,-100,0,0,0])
        time.sleep(1.0)
        self.robot.open_grip()

        self.robot.move(POS_PLANT[0])
        self.get_logger().info("카드 넣기 완료")
        

    def _offer_bag(self):
        self.get_logger().info("사용자에게 꽃 전달 중...")
        # self.robot.move_home()

        self.robot.move(POS_PLANT[0])
        self.robot.open_grip()
        time.sleep(1)
        self.robot.move_relative([0,0,-70,0,0,0])
        self.robot.close_grip()
        time.sleep(1)
        # self.robot.move_relative([0,0,20,0,0,0])

        # self.robot.move(POS_PICKUP)
        # self.robot.force_on_z(-10)
        # self.robot.check_touch(max=10)
        # self.robot.force_off()

        self.robot.move_relative([0,200,0,0,0,0])
        self.robot.open_grip()
        time.sleep(1)
        self.robot.move_relative([0,0,70,0,0,0])
        time.sleep(1)
        self.robot.move(POS_PLANT[0])
        # self.robot.move(POS_PICKUP)
        self.robot.close_grip()
        time.sleep(1)
        

        self.complete_wrap()
        self.get_logger().info("사용자에게 전달 완료")
        
        
    def request_card_print(self):
        self.get_logger().info("카드를 출력중입니다...")
        info = FlowerInfo(
            id = self.id,
            command = CMD_PRINT_CARD,
            flower_name = self.flower_name,
            flower_meaning = self.flower_meaning,
            growth_duration_days = self.growth_duration_days,
            watering_cycle = self.watering_cycle,
            growth_state = self.growth_state
        )
        
        request = CardSrv.Request()
        request.flowerinfo = info
        
        future = self.card_cli.call_async(request)
        return future
    

    def _card_done_callback(self, future):
        try:
            response = future.result()
        except Exception as e:
            self.get_logger().warn(f"Service call failed: {str(e)}")
            return

        self.get_logger().info(f"카드 응답 받음: {response.success}")
        if response.success:
            self.get_logger().info("카드 출력 완료됨")
            self._insert_card()
    

    def complete_wrap(self):
        msg = FlowerInfo()
        msg.id = self.id
        msg.zone_number = self.zone_number
        msg.command = CMD_END_WRAPPING
        msg.flower_name = self.flower_name
        msg.flower_meaning = self.flower_meaning
        msg.growth_duration_days = self.growth_duration_days
        msg.watering_cycle = self.watering_cycle

        self.cmd_pub.publish(msg)
        self.get_logger().info("꽃 정보 전달 완료")

        return


def main(args=None):
    # rclpy.init(args=args)     # robot node안에서 실행
    node = FlowerWrapping()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

        
