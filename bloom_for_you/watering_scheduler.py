import os
import time
from datetime import datetime
import cv2
import sys
import numpy as np
import rclpy
from rclpy.node import Node

from bloom_for_you.function_modules.tts import tts

from bloom_for_you.function_modules import robot

from bloom_for_you.function_modules.realsense_ import ImgNode
from bloom_for_you.function_modules import yolo

from bloom_for_you_interfaces.msg import FlowerInfo

########### FlowerWatering ############

current_dir = os.path.dirname(os.path.abspath(__file__))
# package_path = "/home/rokey/r2_ws/src/bloom_for_you"
package_path = os.path.abspath(os.path.join(current_dir, ".."))

CMD_START_WATERING = 30
CMD_END_WATERING = 31

POS_TABLE = [280.28, 63.48, 250.00, 20.24, -179.96, 19.97]
POS_ZONE1 = [108.99, -461.86, 197.16, 104.45, -178.30, -168.57]
POS_ZONE2 = [-114.80, -460.45, 197.16, 69.36, 180.00, 163.36]
POS_PLANT = [POS_TABLE, POS_ZONE1, POS_ZONE2]

POS_WATER = [600.00,-328.98,134.89,160.31,180.00,160.02]

POT = "화분"
BABY = ["해바라기새싹", "튤립새싹"]
FLOWER = ["해바라기", "튤립"]


class FlowerWatering(Node):
    def __init__(self):
        super().__init__("watering_node")
        self.cmd_sub = self.create_subscription(FlowerInfo, 'flower_info', self.water_the_flower, 10)
        self.growth_pub = self.create_publisher(FlowerInfo, 'flower_info', 10)
        self.img_node = ImgNode()
        self.robot = robot.Robot()
        self.yolo = yolo.Yolo()


    def water_the_flower(self, msg):
        self.command = msg.command
        if self.command != CMD_START_WATERING:
            return
    
        self.id = msg.id
        self.zone_number = msg.zone_number
        self.flower_name = msg.flower_name
        self.flower_meaning = msg.flower_meaning
        self.growth_duration_days = msg.growth_duration_days
        self.watering_cycle = msg.watering_cycle
        self.growth_state = msg.growth_state


        tts("물 주기 노드를 시작합니다.")
        self.get_logger().info("물 주기 노드 시작")
        
        self._get_flower()
        self._water()
        self._check_growth()
        

        tts("물 주기 노드를 완료하였습니다.")
        self.get_logger().info("물 주기 노드 완료")
        
    def _get_flower(self):
        self.get_logger().info("화분 가져오는 중...")
        
        self.robot.move(POS_PLANT[0])

        self.robot.move(POS_PLANT[self.zone_number])
        time.sleep(1.0)
        self.robot.open_grip()
        time.sleep(1.0)
        self.robot.move_relative([0,0,-200,0,0,0])
        time.sleep(1.0)
        self.robot.close_grip()
        time.sleep(1.0)
        self.robot.move(POS_PLANT[self.zone_number])

        self.robot.move(POS_PLANT[0])
        # self.robot.move_relative([0,0,-20,0,0,0])
        self.robot.force_on_z(-40)
        self.robot.check_touch(max=15)

        self.robot.open_grip()
        self.robot.move(POS_PLANT[0])
        self.robot.close_grip()

        self.get_logger().info("화분 픽업 완료")
        

    def _water(self):
        self.get_logger().info("물 주기 실행")
        self.robot.move(POS_TABLE)
        time.sleep(1.0)
        self.robot.move(POS_WATER)
        self.robot.open_grip()
        self.robot.move_relative([0,0,-30,0,0,0])
        self.robot.close_grip()
        self.robot.move(POS_WATER)

        self.robot.move(POS_PLANT[0])
        
        self.get_logger().info("물 주기 완료")


    def _check_growth(self):
        # 욜로로 체크 했다 치고
        self._take_pictures()

    def _take_pictures(self):
        rclpy.spin_once(self.img_node)
        color_image = self.img_node.get_color_frame()
        if color_image is not None:
            timestamp = datetime.today().strftime('%Y%m%d')
            filename = f"flower_{self.id}_{timestamp}.jpg"
            save_dir= os.path.join(package_path, "resource", "pictures", str(self.id))
            os.makedirs(save_dir, exist_ok=True)

            filepath = os.path.join(save_dir, filename)

            cv2.imwrite(filepath, color_image)
            self.get_logger().info(f"사진 저장 완료: {filepath}")
        else:
            self.get_logger().warn("사진 저장 실패: 이미지 프레임이 비어 있음")

        self._return_flower()

    def _return_flower(self):
        msg = FlowerInfo()
        msg.id = self.id
        msg.command = CMD_END_WATERING
        msg.flower_name = self.flower_name
        msg.flower_meaning = self.flower_meaning
        msg.growth_duration_days = self.growth_duration_days
        msg.watering_cycle = self.watering_cycle
        
        grow_state = 1
        self.growth_state=grow_state
        
        msg.growth_state = self.growth_state
        self.growth_pub.publish(msg)



def main(args=None):
    # rclpy.init(args=args)
    node = FlowerWatering()
    try:
        rclpy.spin_once(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()