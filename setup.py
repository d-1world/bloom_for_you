from setuptools import find_packages, setup
from glob import glob
import os

package_name = 'bloom_for_you'


resource_files = [
    (os.path.join('share', package_name, os.path.dirname(path)), [path])
    for path in glob('resource/**/*', recursive=True)
    if os.path.isfile(path)
]

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(include=[package_name, package_name + '.*']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        
    ]+ resource_files,  # ✅ resource 전체 추가
    install_requires=[
        'setuptools',
        'bloom_for_you_interfaces'  # 추가: 인터페이스 패키지 의존성
    ],
    zip_safe=True,
    maintainer='d-1',
    maintainer_email='your@example.com',
    description='Python-based ROS 2 package with custom messages.',
    license='Apache License 2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'scenario_manager = bloom_for_you.scenario_manager:main',
            'flower_recommender = bloom_for_you.flower_recommender:main',
            'seed_planting = bloom_for_you.seed_planting:main',
            'pub_test = bloom_for_you.publisher_test:main',
            'sub_test = bloom_for_you.subscriber_test:main',
            'test = bloom_for_you.test:main',
            'wrap = bloom_for_you.flower_wrapping:main',
            'water = bloom_for_you.watering_scheduler:main',            
            'gui_test = bloom_for_you.gui_test:main',
            'juntae_pub = bloom_for_you.juntae_pub:main',
            
            'speech_to_command = bloom_for_you.speech_to_command:main',

            # set code by wsh - "ros2 run before start your code"
            'set_yolo_model = bloom_for_you.set_yolo_model:main',
            'set_yolo_robot = bloom_for_you.set_yolo_robot:main',
            
            # test code by wsh - "how to run module"
            'test_robot = bloom_for_you.test_robot:main',
            'test_yolo = bloom_for_you.test_yolo:main',            
        ],
    },
)
