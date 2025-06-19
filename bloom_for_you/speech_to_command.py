import rclpy
from rclpy.node import Node
from bloom_for_you.function_modules import wake_up_word_
from bloom_for_you.function_modules import tts
# for mic
import pyaudio

# multi thread에서 사용
import threading

# for keyword 추출
from bloom_for_you.function_modules import keyword_extraction
from std_msgs.msg import String

from ament_index_python.packages import get_package_share_directory
import os

"""
진행 상황
- 메시지 입력 받음
- 입력 받은 메시지 listen_command 토픽으로 퍼블리시

추가 할 일
- 추가 명령 받기
    - 명령 부족할 때 명령만 다시 받기
    - 번호 부족할 때 번호만 다시 받기
    - 다시하기를 고르면 다시하기

"""

DEBUG_ON_OFF = 0 # 0: 디버그, 1: 일반



class SpeechToCommand(Node):
    def __init__(self):
        super().__init__('speech_to_command_node')
        self.WAKE_UP_STATE = 0
        
        self.publisher = self.create_publisher(String, 'listen_command', 10)
        
        # 응답 "1234/1" 형식
        self.response = ""

        # 🧵 run_loop는 별도 스레드에서 실행
        self.loop_thread = threading.Thread(target=self.run_loop, daemon=True)
        self.loop_thread.start()

    def run_loop(self):
        while rclpy.ok():
            self.wake_up()
            self.listen_command()
            self.publish_command()

    def wake_up(self):
        if self.WAKE_UP_STATE == 0:
            self.get_logger().info("SAY HELLO ROKEY TO START!!!")

            # 🔊 오디오 스트림 열기
            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=48000,
                input=True,
                frames_per_buffer=1024
            )

            # 🧠 Wakeword 감지 모델 초기화
            wakeup = wake_up_word_.WakeupWord(
                stream=stream,
                model_name="hello_rokey.tflite",
                buffer_size=1024
            )
            
            if DEBUG_ON_OFF:
                while not wakeup.is_wakeup():
                    pass
            else:
                print("hello rokey 말하기 완료")
                input("enter to next")

            self.WAKE_UP_STATE = 1
            print("WAKE UP!!")
            
            return_val = "네 안녕하세요!! 명령은 씨앗선택, 음성녹음, 포장이 있습니다. 예약번호와 원하시는 명령을 말해주세요."
            if DEBUG_ON_OFF:
                tts.tts(return_val)
            else:
                print(return_val)
                input("enter to next")

        else:
            pass

    def listen_command(self):
        package_share_dir = get_package_share_directory('bloom_for_you')
        # 리소스 파일 경로 설정
        prompt_path = os.path.join(package_share_dir, 'resource', 'get_command_prompt.txt')

        if self.WAKE_UP_STATE == 1:
            self.response = keyword_extraction.keyword_extraction(prompt_path)
            
            res_num, cmd_num = self.response.split('/')
            res_num = int(res_num)
            cmd_num = int(cmd_num)

            if res_num == 0 or cmd_num == 0:
                return_val = "잘못 입력하였습니다 다시 말해주세요"
                
                if DEBUG_ON_OFF:
                    tts.tts(return_val)
                else:
                    print(return_val)
                    input("enter to next")

                self.WAKE_UP_STATE = 1
            
            else:
                if cmd_num == 1:
                    temp_txt = "씨앗 선택"
                elif cmd_num == 10:
                    temp_txt = "음성 녹음"
                elif cmd_num == 20:
                    temp_txt = "포장"
                
                return_val = tts.make_txt("예약번호는 {}입니다. {}을 고르셨습니다", [res_num, temp_txt])
                if DEBUG_ON_OFF:
                    # 음성 -> 커맨드 추출 실행
                    tts.tts(return_val)
                    # # 음성 -> 커맨드 추출 실행, 다시 선택 버전
                    # return_val = tts.make_txt("예약번호는 {}입니다. {}을 고르셨습니다 이대로 진행할까요?", [res_num, "cmd_num"])
                    # tts.tts(return_val)            

                else:
                    print(return_val)
                    input("enter to next")
                                    

                
                

                print(self.response)
                self.WAKE_UP_STATE = 2

    def publish_command(self):
        if self.WAKE_UP_STATE == 2:
            
            msg = String()
            msg.data = str(self.response)
            self.publisher.publish(msg)
            self.get_logger().info(f"🚀 Published String: {msg.data}")

            self.WAKE_UP_STATE = 0

        else:
            pass

def main(args=None):
    rclpy.init(args=args)
    node = SpeechToCommand()

    try:
        rclpy.spin(node)  # 이벤트 루프 계속 유지
    except KeyboardInterrupt:
        print("🛑 Ctrl+C pressed, shutting down...")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
