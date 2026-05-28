"""
tello_bringup.launch.py
-----------------------
Launches:
  1. tello_driver_node  – connects to the drone, publishes camera & state
  2. tello_teleop_key   – keyboard control (runs in its own terminal via
                          prefix='xterm -e' so it gets keyboard focus)

Usage:
  ros2 launch tello_driver tello_bringup.launch.py
  ros2 launch tello_driver tello_bringup.launch.py tello_ip:=192.168.10.1 speed:=0.5
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():

    # ── Launch arguments ──────────────────────────────────────────────────────
    tello_ip_arg = DeclareLaunchArgument(
        'tello_ip', default_value='192.168.10.1',
        description='IP address of the Tello drone')

    speed_arg = DeclareLaunchArgument(
        'speed', default_value='0.6',
        description='Teleoperation speed (0.0 – 1.0)')

    stream_fps_arg = DeclareLaunchArgument(
        'stream_fps', default_value='30',
        description='Target FPS for the video stream')

    # ── Nodes ──────────────────────────────────────────────────────────────────
    driver_node = Node(
        package='tello_driver',
        executable='tello_driver_node',
        name='tello_driver',
        output='screen',
        parameters=[{
            'tello_ip':    LaunchConfiguration('tello_ip'),
            'stream_fps':  LaunchConfiguration('stream_fps'),
            'frame_width':  960,
            'frame_height': 720,
            'cmd_vel_timeout': 0.5,
        }],
    )

    teleop_node = Node(
        package='tello_driver',
        executable='tello_teleop_key',
        name='tello_teleop_key',
        output='screen',
        prefix='xterm -e',        # opens its own terminal for keyboard input
        parameters=[{
            'speed': LaunchConfiguration('speed'),
        }],
    )

    return LaunchDescription([
        tello_ip_arg,
        speed_arg,
        stream_fps_arg,
        driver_node,
        teleop_node,
    ])
