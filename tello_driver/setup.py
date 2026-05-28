from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'tello_driver'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Install launch files
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')),
        # Install config files
        (os.path.join('share', package_name, 'config'),
            glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Tu Nombre',
    maintainer_email='tu@email.com',
    description='ROS2 Humble driver for the DJI Tello drone.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # Driver node
            'tello_driver_node = tello_driver.tello_driver_node:main',
            # Keyboard teleoperation
            'tello_teleop_key  = tello_driver.tello_teleop_key:main',
        ],
    },
)
