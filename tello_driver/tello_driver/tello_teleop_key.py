#!/usr/bin/env python3
"""
tello_teleop_key.py
-------------------
Keyboard teleoperation for DJI Tello via ROS2.

Controls:
  W / S        → Forward / Backward
  A / D        → Left / Right (strafe)
  Q / E        → Yaw left / right
  R / F        → Up / Down
  T            → Takeoff
  L            → Land
  SPACE        → Emergency stop
  ESC / Ctrl-C → Quit
"""

import sys
import tty
import termios
import threading
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Empty

BANNER = """
╔══════════════════════════════════════════╗
║       TELLO KEYBOARD TELEOPERATION      ║
╠══════════════════════════════════════════╣
║  W/S  ── Forward / Backward             ║
║  A/D  ── Strafe Left / Right            ║
║  Q/E  ── Yaw Left / Right               ║
║  R/F  ── Up / Down                      ║
║                                          ║
║  T    ── TAKEOFF                        ║
║  L    ── LAND                           ║
║  SPACE── EMERGENCY STOP                 ║
║  ESC  ── Quit                           ║
╚══════════════════════════════════════════╝
"""

# Key → (linear.x, linear.y, linear.z, angular.z)
KEY_BINDINGS = {
    'w': ( 1.0,  0.0,  0.0,  0.0),
    's': (-1.0,  0.0,  0.0,  0.0),
    'a': ( 0.0,  1.0,  0.0,  0.0),
    'd': ( 0.0, -1.0,  0.0,  0.0),
    'r': ( 0.0,  0.0,  1.0,  0.0),
    'f': ( 0.0,  0.0, -1.0,  0.0),
    'q': ( 0.0,  0.0,  0.0,  1.0),
    'e': ( 0.0,  0.0,  0.0, -1.0),
}

SPEED = 0.6  # fraction of max speed (0.0 – 1.0)


def get_key(settings):
    """Read a single keypress without echo."""
    tty.setraw(sys.stdin.fileno())
    key = sys.stdin.read(1)
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key


class TelloTeleopKey(Node):

    def __init__(self):

        super().__init__('tello_teleop_key')

        self.declare_parameter('speed', SPEED)
        self.speed = self.get_parameter('speed').value

        self.cmd_pub = self.create_publisher(Twist, '/tello/cmd_vel', 10)
        self.takeoff_pub = self.create_publisher(Empty, '/tello/takeoff', 1)
        self.land_pub = self.create_publisher(Empty, '/tello/land', 1)
        self.emergency_pub = self.create_publisher(Empty, '/tello/emergency', 1)

        # Estado actual
        self._active_twist = Twist()

        # Último mensaje publicado
        self._last_published = None

        # Control de timeout de teclas
        self.last_key_time = 0.0
        self.key_timeout = 0.15  # segundos

        # Thread safety
        self._lock = threading.Lock()

        # Timer ROS2
        self.timer = self.create_timer(0.05, self._heartbeat)

    def _heartbeat(self):
        """
        Publica cmd_vel SOLO si cambió.
        También detiene el drone automáticamente
        cuando se deja de presionar una tecla.
        """

        # Si no hubo teclas recientemente → STOP
        if time.time() - self.last_key_time > self.key_timeout:
            self._send_zero()

        with self._lock:

            current = (
                self._active_twist.linear.x,
                self._active_twist.linear.y,
                self._active_twist.linear.z,
                self._active_twist.angular.z
            )

            # Publicar SOLO si cambió
            if current != self._last_published:

                self.cmd_pub.publish(self._active_twist)
                self._last_published = current

    def _send_zero(self):

        msg = Twist()

        with self._lock:
            self._active_twist = msg

    def _send_twist(self, lx, ly, lz, az):

        msg = Twist()

        msg.linear.x = lx * self.speed
        msg.linear.y = ly * self.speed
        msg.linear.z = lz * self.speed
        msg.angular.z = az * self.speed

        with self._lock:
            self._active_twist = msg

    def run(self):

        settings = termios.tcgetattr(sys.stdin)

        print(BANNER)
        print(f'Speed: {self.speed:.1f}')
        print('Press keys to control the drone...\n')

        try:

            while rclpy.ok():

                key = get_key(settings)

                if key in KEY_BINDINGS:

                    # Actualizar tiempo de última tecla
                    self.last_key_time = time.time()

                    lx, ly, lz, az = KEY_BINDINGS[key]

                    self._send_twist(lx, ly, lz, az)

                    print(
                        f'Key [{key.upper()}] '
                        f'lin=({lx:+.0f},{ly:+.0f},{lz:+.0f}) '
                        f'yaw={az:+.0f}      ',
                        end='\r'
                    )

                elif key == 't':

                    self.get_logger().info('TAKEOFF')

                    print('\nTAKEOFF')

                    self.takeoff_pub.publish(Empty())

                elif key == 'l':

                    self.get_logger().info('LAND')

                    print('\nLAND')

                    self.land_pub.publish(Empty())

                elif key == ' ':

                    self.get_logger().warn('EMERGENCY STOP')

                    print('\n⚠ EMERGENCY STOP')

                    self.emergency_pub.publish(Empty())

                    self._send_zero()

                elif key in ('\x1b', '\x03'):  # ESC or Ctrl-C

                    print('\nQuitting teleop...')

                    self._send_zero()

                    break

                else:
                    # Cualquier otra tecla → STOP
                    self._send_zero()

        except Exception as e:

            self.get_logger().error(f'Teleop error: {e}')

        finally:

            termios.tcsetattr(
                sys.stdin,
                termios.TCSADRAIN,
                settings
            )

            self._send_zero()

    def destroy_node(self):

        # Asegurar STOP antes de cerrar
        self._send_zero()

        super().destroy_node()


def main(args=None):

    rclpy.init(args=args)

    node = TelloTeleopKey()

    # ROS2 spin en background
    spin_thread = threading.Thread(
        target=rclpy.spin,
        args=(node,),
        daemon=True
    )

    spin_thread.start()

    try:
        node.run()

    finally:

        node.destroy_node()

        rclpy.shutdown()


if __name__ == '__main__':
    main()
