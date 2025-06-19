# default function
import os
from scipy.spatial.transform import Rotation
import numpy as np

# ros2
import rclpy
from rclpy.node import Node

# bloom module
from bloom_for_you.function_modules import robot
from bloom_for_you.function_modules.realsense_ import ImgNode

# bloom interfaces
from bloom_for_you_interfaces.srv import SrvDepthPosition
from bloom_for_you_interfaces.msg import GripTarget
from ament_index_python.packages import get_package_share_directory

package_path = get_package_share_directory("bloom_for_you")

MIN_DEPTH = -1000.0

class SetYoloRobot(Node):
    def __init__(self):
        # 노드명
        super().__init__("use_yolo_set")
        self.grip_command = 0   # 타겟 명령이 왔는지
        self.grip_target = ""   # 타겟 이름
        self.x_move = 0 # 타겟에서 x 오프셋 입력
        self.y_move = 0 # 타겟에서 y 오프셋 입력
        self.z_move = 0 # 타겟에서 z 오프셋 입력
        
        # 1. 로봇 인스턴스
        self.robot_instance= robot.Robot()
        
        # 2. 포지션을 가져올 때 사용하는 서비스 client
        self.get_position_client = self.create_client(
            SrvDepthPosition, "/get_3d_position"
        )
        while not self.get_position_client.wait_for_service(timeout_sec=3.0):
            self.get_logger().info("Waiting for get_depth_position service...")
        self.get_position_request = SrvDepthPosition.Request()

        # 3. 타겟 수신 후 해당 위치로 이동
        self.listen_target = self.create_subscription(
            GripTarget,              # 메시지 타입
            "/grip_target",          # 토픽 이름
            self.grip_target_callback,    # 콜백 함수
            10                       # 큐 사이즈
        )
        
    def grip_target_callback(self, msg:GripTarget):
        self.grip_target = msg.target
        self.x_move = msg.offset_x
        self.y_move = msg.offset_y
        self.z_move = msg.offset_z
        self.grip_command = 1
        
    def robot_control(self, target, x_move, y_move, z_move):
        target_pos = self._get_target_pos(target, x_move, y_move, z_move)
        self.grip_command = 0
        if target_pos is None:
            self.get_logger().warn("No target position")
        else:
            self.get_logger().info(f"Final Move position: {target_pos}")
            self.robot_instance.move(target_pos)

    def _get_robot_pose_matrix(self, x, y, z, rx, ry, rz):
        R = Rotation.from_euler("ZYZ", [rx, ry, rz], degrees=True).as_matrix()
        T = np.eye(4)
        T[:3, :3] = R
        T[:3, 3] = [x, y, z]
        return T

    def _transform_to_base(self, camera_coords, gripper2cam_path, robot_pos):
        """
        Converts 3D coordinates from the camera coordinate system
        to the robot's base coordinate system.
        """
        gripper2cam = np.load(gripper2cam_path)
        coord = np.append(np.array(camera_coords), 1)  # Homogeneous coordinate

        x, y, z, rx, ry, rz = robot_pos
        base2gripper = self._get_robot_pose_matrix(x, y, z, rx, ry, rz)

        # 좌표 변환 (그리퍼 → 베이스)
        base2cam = base2gripper @ gripper2cam
        td_coord = np.dot(base2cam, coord)

        return td_coord[:3]

    def _get_target_pos(self, target, x_move = 0, y_move = 0, z_move = 0):
        self.get_position_request.target = target
        self.get_logger().info("call depth position service with object_detection node")
        get_position_future = self.get_position_client.call_async(
            self.get_position_request
        )
        rclpy.spin_until_future_complete(self, get_position_future)

        if get_position_future.result():
            result = get_position_future.result().depth_position.tolist()
            self.get_logger().info(f"Received depth position: {result}")
            if sum(result) == 0:
                print("No target position")
                return None

            gripper2cam_path = os.path.join(
                package_path, "resource", "T_gripper2camera.npy"
            )
            robot_posx = self.robot_instance.get_current_posx()[0]
            td_coord = self._transform_to_base(result, gripper2cam_path, robot_posx)

            if td_coord[2] and sum(td_coord) != 0:
                td_coord[0] = td_coord[0] + x_move
                td_coord[1] = td_coord[1] + y_move
                td_coord[2] = td_coord[2] + z_move
                
                td_coord[2] = max(td_coord[2], MIN_DEPTH)  # MIN_DEPTH: float = 3.0
            target_pos = list(td_coord[:3]) + robot_posx[3:]

            return target_pos
        
        else:
            return None

def main(args=None):
    # init 안 되어 있으면
    if not rclpy.ok():
        rclpy.init(args=args)

    yolo_robot_node = SetYoloRobot()
    
    while rclpy.ok():
        rclpy.spin_once(yolo_robot_node, timeout_sec=0.1)

        if(yolo_robot_node.grip_command ==1):
            x = yolo_robot_node.x_move
            y = yolo_robot_node.y_move
            z = yolo_robot_node.z_move
            yolo_robot_node.robot_control(yolo_robot_node.grip_target, x, y, z)
    rclpy.shutdown()
    yolo_robot_node.destroy_node()

if __name__ == "__main__":
    main()
