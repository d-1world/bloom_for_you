import rclpy
from rclpy.node import Node
from bloom_for_you_interfaces.msg import FlowerInfo
from std_msgs.msg import String # 음성으로 받은 명령어

class Flower:
    def __init__(self, 
                 id: int = 0, 
                 command: int = 0, 
                 zone_number: int = 0, 
                 flower_name: str = "nothing", 
                 flower_meaning: str = "nothing", 
                 growth_duration_days: int = 1000, 
                 watering_cycle: int = 1000, 
                 growth_state: int = 0):
        self.id = id
        self.command = command
        self.zone_number = zone_number
        self.flower_name = flower_name
        self.flower_meaning = flower_meaning
        self.growth_duration_days = growth_duration_days
        self.watering_cycle = watering_cycle
        self.growth_state = growth_state

    def __repr__(self):
        return (f"Flower(id={self.id}, command={self.command}, zone_number={self.zone_number}, "
                f"flower_name='{self.flower_name}', flower_meaning='{self.flower_meaning}', "
                f"growth_duration_days={self.growth_duration_days}, watering_cycle={self.watering_cycle}, "
                f"growth_state={self.growth_state})")


class ScenarioManager(Node):
    def __init__(self):
        super().__init__('scenario_manager_node')
        self.timestamp = 0

        self.command_queue = []
        self.ROBOT_STATE = 0 # 0은 사용 가능, 1은 사용 불가
        self.LISTEN_COMMAND_STATE = 0
        
        self.flower_info_list = []
        flower_temp = Flower(id = 1234, zone_number=1)
        self.flower_info_list.append(flower_temp)

        self.scenario_zone_number = [0]

        # ROS 퍼블리셔 및 서브스크라이버
        self.publisher = self.create_publisher(FlowerInfo, 'flower_info', 10)
        self.command_subscriber = self.create_subscription(String,'listen_command',self.listen_command_callback,10)
        self.flower_info_subscriber = self.create_subscription(FlowerInfo,'flower_info',self.flower_info_callback,10)
        
        self.watering_timer = self.create_timer(1.0, self.watering_scheduler)
        self.run_command_timer = self.create_timer(1.0, self.run_command)

        self.state_timer = self.create_timer(1.0, self.check_state)
        
    def check_state(self):
        self.get_logger().info(f"state = {self.ROBOT_STATE} command len = {len(self.command_queue)}, flower len = {len(self.flower_info_list)}")
    
    # 커맨드 큐에 들어가는 것 실행
    def run_command(self):
        if len(self.command_queue) != 0 and self.ROBOT_STATE == 0:
            # input("enter to start run command")
            
            temp_txt = "없음"
            if self.command_queue[0][1] == 1:
                temp_txt = "씨앗 선택"
            elif self.command_queue[0][1] == 10:
                temp_txt = "음성 녹음"
            elif self.command_queue[0][1] == 20:
                temp_txt = "포장"
            else:
                temp_txt = str(self.command_queue[0][1])
                
            
            self.get_logger().info(f"@@@@@@@@@@@@ run command!! 예약번호 = {self.command_queue[0][0]} 실행 명령 = {temp_txt} @@@@@@@@@@@@")

            for flower_ in self.flower_info_list:
                if flower_.id == self.command_queue[0][0]:
                    print("i find it")
                    flower_.command = self.command_queue[0][1]
                    msg = self.convert_flower_to_msg_(flower_)
                    
                    # "1: 꽃 추천" or "10: 음성 녹음 시작" or "20: 포장 시작" or "30: 물주기" 일 경우
                    # 로봇 STATE 1로 변경
                    if flower_.command == 1 or flower_.command == 10 or flower_.command == 20 or flower_.command == 30:
                        self.ROBOT_STATE = 1
                        
                    self.publisher.publish(msg)

            self.command_queue.pop(0)

    # 커맨드 큐 저장 1 - 음성인식 받아서 커맨드 큐에 저장
    def listen_command_callback(self, msg: String):
        self.get_logger().info(f"[Subscribe] id: {msg.data}")
        ## 예약 번호 커맨드 이름 추출 ##
        res_num, cmd_num = msg.data.split('/')
        res_num = int(res_num)
        cmd_num = int(cmd_num)

        if(res_num == 0 or cmd_num == 0):
            self.get_logger().warn(f"잘못된 데이터가 입력되었습니다!! 데이터: {msg.data}")
            return

        ############# 씨앗선택 #############
        if(cmd_num == 1):
            # 이미 있는 예약번호인지 확인
            for flower_ in self.flower_info_list:
                if(flower_.id == res_num):
                    self.get_logger().warn(f"이미 있는 예약번호입니다!! {res_num}")
                    return

            # 없을 경우 추가
            self.get_logger().info(f"꽃 번호 추가 id: {res_num}")
            
            # 존 추가
            zone = 1
            while zone in self.scenario_zone_number:
                zone += 1
            self.scenario_zone_number.append(zone)  # 할당된 존 번호 기록
            
            flower_temp = Flower(id = res_num, zone_number=zone)
            self.flower_info_list.append(flower_temp)

            # 명령어 추가 - 씨앗선택
            self.command_queue.append((res_num, cmd_num))
        
        ############# 음성녹음 #############
        if(cmd_num == 10):
            # 이미 있는 예약번호인지 확인
            for flower_ in self.flower_info_list:
                if(flower_.id == res_num):
                    self.command_queue.append((res_num, cmd_num))
        
        ############# 포장 #############
        if(cmd_num == 20):
            # 이미 있는 예약번호인지 확인
            for flower_ in self.flower_info_list:
                if(flower_.id == res_num):
                    self.command_queue.append((res_num, cmd_num))

    # 커맨드 큐 저장 2 - 물 스케줄에 맞춰서 커맨드 큐에 저장
    def watering_scheduler(self):
        self.timestamp +=1
        
        # 로봇 사용 중이면 물주기 추가 안함
        if self.ROBOT_STATE == 1:
            return
        for flower_ in self.flower_info_list:
            if (self.timestamp % flower_.watering_cycle) == 0:
                self.get_logger().info(f"물주기 실행 {flower_.id} 주기= {flower_.flower_name}")
                # 명령어 추가 - 씨앗선택
                self.command_queue.append((flower_.id, 30))

    # 꽃 관련 커맨드 받으면 해당 내용 처리
    def flower_info_callback(self, msg: FlowerInfo):
        self.get_logger().info(
            f"[Subscribe] id: {msg.id}, command: {msg.command}, zone: {msg.zone_number}, "
            f"name: {msg.flower_name}, meaning: {msg.flower_meaning}, "
            f"duration: {msg.growth_duration_days}d, cycle: {msg.watering_cycle}d, "
            f"state: {msg.growth_state}"
        )
        
        to_remove = None
        
        for flower_ in self.flower_info_list:
            if msg.id == flower_.id:
                self.get_logger().info(f"꽃 업데이트: {flower_.id}")
                self.update_flower_from_msg_(flower_,msg)
                
                # "3: 씨앗 심기 완료" or "11: 음성 녹음 완료" or "22: 포장 완료" or "31: 물 주기 완료" 일 경우 
                # 로봇 STATE 0로 변경
                if flower_.command == 3 or flower_.command == 11 or flower_.command == 22 or flower_.command == 31:
                    self.ROBOT_STATE = 0
                

                # 씨앗 심기 완료면 주기 10으로 줄이기
                if flower_.command == 3:
                    if flower_.zone_number == 1:
                        self.timestamp = 0
                        flower_.watering_cycle = 10
                    else:
                        flower_.watering_cycle = 10000
                
                # 물주기 완료면 주기 1000으로 늘리기
                if flower_.command == 31:
                    flower_.watering_cycle = 10000
                    

                # 포장 완료면 플라워 리스트에서 삭제 해야됨
                if flower_.command == 22:
                    # 존 번호 해제
                    if flower_.zone_number in self.scenario_zone_number:
                        self.scenario_zone_number.remove(flower_.zone_number)
                        self.get_logger().info(f"존 번호 {flower_.zone_number} 해제됨")
                    
                    to_remove = flower_
                    break

        if to_remove:
            self.flower_info_list.remove(to_remove)
            self.get_logger().info(f"포장 완료된 꽃 삭제: {to_remove.id}")


    def convert_flower_to_msg_(self, flower_) -> FlowerInfo:
        msg = FlowerInfo()
        msg.id = flower_.id
        msg.command = flower_.command
        msg.zone_number = flower_.zone_number
        msg.flower_name = flower_.flower_name
        msg.flower_meaning = flower_.flower_meaning
        msg.growth_duration_days = flower_.growth_duration_days
        msg.watering_cycle = flower_.watering_cycle
        msg.growth_state = flower_.growth_state
        return msg

    def update_flower_from_msg_(self, flower_, msg: FlowerInfo):
        flower_.id = msg.id
        flower_.command = msg.command
        flower_.zone_number = msg.zone_number
        flower_.flower_name = msg.flower_name
        flower_.flower_meaning = msg.flower_meaning
        flower_.growth_duration_days = msg.growth_duration_days
        flower_.watering_cycle = msg.watering_cycle
        flower_.growth_state = msg.growth_state

def main(args=None):
    rclpy.init(args=args)  # ROS 초기화
    scenario_manager = ScenarioManager()  # 노드 생성

    try:
        rclpy.spin(scenario_manager)  # 노드 실행 (콜백 대기)
    except KeyboardInterrupt:
        print("Shutting down node...")
    finally:
        scenario_manager.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
