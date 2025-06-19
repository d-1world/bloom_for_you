# bloom_for_you/function_modules/wake_up_word_.py

import os
import numpy as np
from openwakeword.model import Model
from scipy.signal import resample
from ament_index_python.packages import get_package_share_directory

class WakeupWord:
    def __init__(self, stream, model_name="hello_rokey_8332_32.tflite", buffer_size=1024):
        package_path = get_package_share_directory("bloom_for_you")
        model_path = os.path.join(package_path, "resource/voice_model", model_name)

        self.model_name = model_name.split(".", 1)[0]
        self.model = Model(wakeword_models=[model_path])
        self.stream = stream
        self.buffer_size = buffer_size

    def is_wakeup(self):
        audio_chunk = np.frombuffer(
            self.stream.read(self.buffer_size, exception_on_overflow=False),
            dtype=np.int16,
        )
        audio_chunk = resample(audio_chunk, int(len(audio_chunk) * 16000 / 48000))
        outputs = self.model.predict(audio_chunk, threshold=0.1)
        confidence = outputs[self.model_name]
        print("confidence: ", confidence)
        if confidence > 0.3:
            print("Wakeword detected!")
            return True
        return False
