import os
import rclpy
from rclpy.node import Node
from bloom_for_you_interfaces.srv import VoiceUpload  # 네가 정의한 서비스 타입
import bloom_for_you.function_modules.voice_upload as voice_upload

class VoiceUploadServiceServer(Node):
    def __init__(self):
        super().__init__('voice_upload_service_server')
        self.srv = self.create_service(
            VoiceUpload, 'voice_upload', self.callback
        )
        self.get_logger().info("음성 업로드 서비스(voice_upload) 준비 완료")

    def callback(self, request, response):
        # 예: request.res_num, request.message 등을 받았다면
        res_num = request.res_num
        message = request.message
        self.get_logger().info(f"업로드 요청: 예약번호={res_num}")

        try:
            # 외부에서 함수로 실행 가능!
            voice_upload.main(res_num=res_num, message=message)
            response.success = True
        except Exception as e:
            self.get_logger().error(f"업로드 실패: {e}")
            response.success = False

        return response

def main():
    rclpy.init()
    node = VoiceUploadServiceServer()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
