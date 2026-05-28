#!/usr/bin/env python3
"""
tello_driver_node.py
--------------------
ROS2 Humble node that connects to a DJI Tello drone via UDP,
publishes the camera stream as sensor_msgs/Image and exposes
a /tello/cmd_vel topic (geometry_msgs/Twist) for velocity commands.

Topics published:
  /tello/image_raw        (sensor_msgs/Image)
  /tello/camera_info      (sensor_msgs/CameraInfo)
  /tello/battery          (std_msgs/Int32)
  /tello/state            (std_msgs/String)

Topics subscribed:
  /tello/cmd_vel          (geometry_msgs/Twist)
  /tello/takeoff          (std_msgs/Empty)
  /tello/land             (std_msgs/Empty)
  /tello/emergency        (std_msgs/Empty)
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

from sensor_msgs.msg import Image, CameraInfo
from geometry_msgs.msg import Twist
from std_msgs.msg import Empty, Int32, String

import threading
import time
import socket
import cv2
from cv_bridge import CvBridge

try:
    from djitellopy import Tello
except ImportError:
    raise ImportError(
        "djitellopy is required. Install it with:\n"
        "  pip install djitellopy"
    )


class TelloDriverNode(Node):
    def __init__(self):
        super().__init__('tello_driver')

        # ── Parameters ────────────────────────────────────────────────────────
        self.declare_parameter('tello_ip', '192.168.10.1')
        self.declare_parameter('stream_fps', 30)
        self.declare_parameter('frame_width', 960)
        self.declare_parameter('frame_height', 720)
        self.declare_parameter('cmd_vel_timeout', 0.5)  # seconds

        self.tello_ip = self.get_parameter('tello_ip').value
        self.stream_fps = self.get_parameter('stream_fps').value
        self.frame_width = self.get_parameter('frame_width').value
        self.frame_height = self.get_parameter('frame_height').value
        self.cmd_vel_timeout = self.get_parameter('cmd_vel_timeout').value

        # ── Internal state ─────────────────────────────────────────────────────
        self.bridge = CvBridge()
        self.tello = Tello(host=self.tello_ip)
        self.last_cmd_time = time.time()
        self.is_flying = False
        self._stop_event = threading.Event()

        # ── QoS ───────────────────────────────────────────────────────────────
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )

        # ── Publishers ────────────────────────────────────────────────────────
        self.image_pub = self.create_publisher(Image, '/tello/image_raw', sensor_qos)
        self.caminfo_pub = self.create_publisher(CameraInfo, '/tello/camera_info', sensor_qos)
        self.battery_pub = self.create_publisher(Int32, '/tello/battery', 10)
        self.state_pub = self.create_publisher(String, '/tello/state', 10)

        # ── Subscribers ───────────────────────────────────────────────────────
        self.cmd_vel_sub = self.create_subscription(
            Twist, '/tello/cmd_vel', self._cmd_vel_cb, 10)
        self.takeoff_sub = self.create_subscription(
            Empty, '/tello/takeoff', self._takeoff_cb, 10)
        self.land_sub = self.create_subscription(
            Empty, '/tello/land', self._land_cb, 10)
        self.emergency_sub = self.create_subscription(
            Empty, '/tello/emergency', self._emergency_cb, 10)

        # ── Timers ────────────────────────────────────────────────────────────
        self.battery_timer = self.create_timer(5.0, self._publish_battery)
        self.state_timer = self.create_timer(1.0, self._publish_state)
        self.safety_timer = self.create_timer(0.1, self._safety_check)

        # ── Connect and start ─────────────────────────────────────────────────
        self._connect()

    # ── Connection ────────────────────────────────────────────────────────────
    def _connect(self):
        self.get_logger().info(f'Connecting to Tello at {self.tello_ip}...')
        try:
            self.tello.connect()
            self.get_logger().info(
                f'Connected! Battery: {self.tello.get_battery()}%')
            self.tello.streamon()
            self.get_logger().info('Video stream started.')
            # Start frame capture thread
            self._frame_thread = threading.Thread(
                target=self._frame_loop, daemon=True)
            self._frame_thread.start()
        except Exception as e:
            self.get_logger().error(f'Connection failed: {e}')

    # ── Video frame loop (runs in separate thread) ─────────────────────────────
    def _frame_loop(self):
        reader = self.tello.get_frame_read()
        period = 1.0 / self.stream_fps
        self.get_logger().info('Frame loop started.')
        while not self._stop_event.is_set():
            try:
                frame = reader.frame
                if frame is None:
                    time.sleep(period)
                    continue
                frame = cv2.resize(frame, (self.frame_width, self.frame_height))
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                now = self.get_clock().now().to_msg()
                img_msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
                img_msg.header.stamp = now
                img_msg.header.frame_id = 'tello_camera'
                self.image_pub.publish(img_msg)
                # Basic CameraInfo
                ci = CameraInfo()
                ci.header = img_msg.header
                ci.width = self.frame_width
                ci.height = self.frame_height
                self.caminfo_pub.publish(ci)
            except Exception as e:
                self.get_logger().warn(f'Frame error: {e}')
            time.sleep(period)

    # ── Callbacks ─────────────────────────────────────────────────────────────
    def _cmd_vel_cb(self, msg: Twist):
        """
        Map Twist to Tello RC channels.
        linear.x  → forward/back  (cm/s  scaled)
        linear.y  → left/right    (cm/s  scaled)
        linear.z  → up/down       (cm/s  scaled)
        angular.z → yaw           (deg/s scaled)
        Values expected in [-1, 1] range.
        """
        self.last_cmd_time = time.time()
        scale = 100  # map [-1,1] → [-100,100]
        left_right   = int(msg.linear.y  * scale)
        forward_back = int(msg.linear.x  * scale)
        up_down      = int(msg.linear.z  * scale)
        yaw          = int(msg.angular.z * scale)

        # Clamp
        left_right   = max(-100, min(100, left_right))
        forward_back = max(-100, min(100, forward_back))
        up_down      = max(-100, min(100, up_down))
        yaw          = max(-100, min(100, yaw))

        try:
            self.tello.send_rc_control(left_right, forward_back, up_down, yaw)
        except Exception as e:
            self.get_logger().warn(f'RC control error: {e}')

    def _takeoff_cb(self, _):
        self.get_logger().info('Takeoff command received.')
        try:
            self.tello.takeoff()
            self.is_flying = True
        except Exception as e:
            self.get_logger().error(f'Takeoff error: {e}')

    def _land_cb(self, _):
        self.get_logger().info('Land command received.')
        try:
            self.tello.land()
            self.is_flying = False
        except Exception as e:
            self.get_logger().error(f'Land error: {e}')

    def _emergency_cb(self, _):
        self.get_logger().warn('EMERGENCY STOP!')
        try:
            #self.tello.emergency()
            node.destroy_node()
            self.is_flying = False
        except Exception as e:
            self.get_logger().error(f'Emergency error: {e}')

    # ── Periodic publishers ────────────────────────────────────────────────────
    def _publish_battery(self):
        try:
            bat = self.tello.get_battery()
            msg = Int32()
            msg.data = bat
            self.battery_pub.publish(msg)
            if bat < 15:
                self.get_logger().warn(f'Low battery: {bat}%')
        except Exception:
            pass

    def _publish_state(self):
        try:
            state_str = str(self.tello.get_current_state())
            msg = String()
            msg.data = state_str
            self.state_pub.publish(msg)
        except Exception:
            pass

    def _safety_check(self):
        """Stop motors if no cmd_vel received recently."""
        if self.is_flying:
            elapsed = time.time() - self.last_cmd_time
            if elapsed > self.cmd_vel_timeout:
                try:
                    self.tello.send_rc_control(0, 0, 0, 0)
                except Exception:
                    pass

    # ── Cleanup ───────────────────────────────────────────────────────────────
    def destroy_node(self):
        self.get_logger().info('Shutting down Tello driver...')
        self._stop_event.set()
        try:
            if self.is_flying:
                self.tello.land()
            self.tello.streamoff()
            self.tello.end()
        except Exception:
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = TelloDriverNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
