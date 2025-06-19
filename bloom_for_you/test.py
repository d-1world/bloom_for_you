import os
import rclpy
from rclpy.node import Node

from std_msgs.msg import Int32
from bloom_for_you.function_modules.stt import stt
from bloom_for_you.function_modules.tts import tts
from bloom_for_you.function_modules.keyword_extraction import keyword_extraction

from bloom_for_you_interfaces.srv import CardSrv

openai_api_key = os.getenv("OPENAI_API_KEY")

# class Test(Node):
#     def __init__(self):
#         super().__init__('test_node')
#         self.stt = STT(openai_api_key)
#         self.stt.speech2text()


# def main():
#     rclpy.init()
#     node = Test()
#     rclpy.spin_once(node)
#     node.destroy_node()
#     rclpy.shutdown()


# if __name__ == "__main__":
#     main()

class Test(Node):
    def __init__(self):
        super().__init__('test_node')
    
        self.test = self.create_subscription(Int32, '/test', callback = self.recommend_flower, qos_profile=10)
        self.card_sv = self.create_service(CardSrv,'cardsrv',self.callback)

    def recommend_flower(self, msg):
        # ret_text = stt()
        # print(f'callback 결과: {ret_text}')
        # tts(ret_text)
        keyword_extraction("test.txt")

    def callback(self,request,response):
        self.get_logger().info("카드 출력 요청 수신됨")
        response.success = True
        self.get_logger().info("응답 리턴 완료됨")
        return response

def main():
    rclpy.init()
    node = Test()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()