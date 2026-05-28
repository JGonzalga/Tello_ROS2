"""
tello_driver.launch.py
----------------------
Launches only the driver node (no teleop).
Useful when you want to control the drone programmatically.

Usage:
  ros2 launch tello_driver tello_driver.launch.py
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():

    tello_ip_arg = DeclareLaunchArgument(
        'tello_ip', default_value='192.168.10.1',
        description='IP address of the Tello drone')

    stream_fps_arg = DeclareLaunchArgument(
        'stream_fps', default_value='30',
        description='Target FPS for the video stream')

    driver_node = Node(
        package='tello_driver',
        executable='tello_driver_node',
        name='tello_driver',
        output='screen',
        emulate_tty=True,
        parameters=[{
            'tello_ip':        LaunchConfiguration('tello_ip'),
            'stream_fps':      LaunchConfiguration('stream_fps'),
            'frame_width':     960,
            'frame_height':    720,
            'cmd_vel_timeout': 0.5,
        }],
    )

    return LaunchDescription([tello_ip_arg, stream_fps_arg, driver_node])
