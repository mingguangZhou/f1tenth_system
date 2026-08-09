#!/usr/bin/env python3

"""Joystick-based drive mode manager for F1TENTH onboard bringup.

This node converts the autonomous enable button from a press-and-hold behavior
into a latched toggle behavior while preserving the existing button layout:

* button 5: toggle autonomous mode on/off
* button 4: manual-control deadman; pressing it immediately exits auto mode

The node works with ackermann_mux by publishing a Bool lock. When auto is
disabled, /drive is masked by the lock while /teleop remains allowed because
manual teleop has higher mux priority. The node also publishes a zero /teleop
command while auto is disabled and manual control is not active, so the car
stays stopped.
"""

from typing import List

import rclpy
from rclpy.node import Node
from ackermann_msgs.msg import AckermannDriveStamped
from sensor_msgs.msg import Joy
from std_msgs.msg import Bool


class DriveModeManager(Node):
    def __init__(self):
        super().__init__('drive_mode_manager')

        self.declare_parameter('manual_button_index', 4)
        self.declare_parameter('auto_button_index', 5)
        self.declare_parameter('joy_topic', 'joy')
        self.declare_parameter('teleop_topic', 'teleop')
        self.declare_parameter('auto_disabled_topic', 'auto_drive_disabled')
        self.declare_parameter('auto_enabled_topic', 'auto_drive_enabled')
        self.declare_parameter('publish_rate_hz', 20.0)
        self.declare_parameter('manual_button_timeout_sec', 0.3)

        self.manual_button_index = int(self.get_parameter('manual_button_index').value)
        self.auto_button_index = int(self.get_parameter('auto_button_index').value)
        self.joy_topic = str(self.get_parameter('joy_topic').value)
        self.teleop_topic = str(self.get_parameter('teleop_topic').value)
        self.auto_disabled_topic = str(self.get_parameter('auto_disabled_topic').value)
        self.auto_enabled_topic = str(self.get_parameter('auto_enabled_topic').value)
        publish_rate_hz = float(self.get_parameter('publish_rate_hz').value)
        self.manual_button_timeout_sec = float(
            self.get_parameter('manual_button_timeout_sec').value
        )
        if publish_rate_hz <= 0.0:
            publish_rate_hz = 20.0
        if self.manual_button_timeout_sec <= 0.0:
            self.manual_button_timeout_sec = 0.3

        self.auto_enabled = False
        self.manual_pressed = False
        self.prev_auto_button_pressed = False
        self.last_joy_time = self.get_clock().now()

        self.joy_sub = self.create_subscription(
            Joy,
            self.joy_topic,
            self.joy_callback,
            10,
        )
        self.auto_disabled_pub = self.create_publisher(
            Bool,
            self.auto_disabled_topic,
            10,
        )
        self.auto_enabled_pub = self.create_publisher(
            Bool,
            self.auto_enabled_topic,
            10,
        )
        self.zero_teleop_pub = self.create_publisher(
            AckermannDriveStamped,
            self.teleop_topic,
            10,
        )

        timer_period = 1.0 / publish_rate_hz
        self.timer = self.create_timer(timer_period, self.timer_callback)

        self.get_logger().info(
            'Drive mode manager started: auto OFF, /drive locked. '
            f'button {self.auto_button_index}=auto toggle, '
            f'button {self.manual_button_index}=manual override.'
        )

    @staticmethod
    def _button_pressed(buttons: List[int], index: int) -> bool:
        return 0 <= index < len(buttons) and buttons[index] != 0

    def joy_callback(self, msg: Joy):
        self.last_joy_time = self.get_clock().now()
        manual_pressed = self._button_pressed(msg.buttons, self.manual_button_index)
        auto_button_pressed = self._button_pressed(msg.buttons, self.auto_button_index)

        # Manual control has logical priority over autonomous mode. Pressing
        # the existing manual deadman button immediately exits auto mode.
        if manual_pressed:
            if self.auto_enabled:
                self.auto_enabled = False
                self.get_logger().warn(
                    'Manual override pressed: auto mode OFF, /drive locked.'
                )
            self.manual_pressed = True
        else:
            self.manual_pressed = False

            # Toggle auto only on the rising edge of the existing auto button,
            # so holding the button does not repeatedly toggle the state.
            if auto_button_pressed and not self.prev_auto_button_pressed:
                self.auto_enabled = not self.auto_enabled
                if self.auto_enabled:
                    self.get_logger().warn(
                        'Auto toggle pressed: auto mode ON, /drive allowed.'
                    )
                else:
                    self.get_logger().warn(
                        'Auto toggle pressed: auto mode OFF, /drive locked.'
                    )

        self.prev_auto_button_pressed = auto_button_pressed

    def timer_callback(self):
        now = self.get_clock().now()
        joy_age_sec = (now - self.last_joy_time).nanoseconds * 1e-9
        effective_manual_pressed = (
            self.manual_pressed and joy_age_sec <= self.manual_button_timeout_sec
        )

        auto_disabled_msg = Bool()
        auto_disabled_msg.data = not self.auto_enabled
        self.auto_disabled_pub.publish(auto_disabled_msg)

        auto_enabled_msg = Bool()
        auto_enabled_msg.data = self.auto_enabled
        self.auto_enabled_pub.publish(auto_enabled_msg)

        # With the old joy_teleop default command moved away from /teleop, this
        # explicit zero command keeps the car stopped whenever auto is OFF. Do
        # not publish it while the manual button is freshly held, otherwise it
        # would fight the real manual /teleop command from joy_teleop. If Joy
        # messages stop arriving, effective_manual_pressed times out and the
        # zero command resumes.
        if not self.auto_enabled and not effective_manual_pressed:
            zero_msg = AckermannDriveStamped()
            zero_msg.header.stamp = now.to_msg()
            zero_msg.header.frame_id = 'base_link'
            zero_msg.drive.speed = 0.0
            zero_msg.drive.steering_angle = 0.0
            zero_msg.drive.acceleration = 0.0
            zero_msg.drive.jerk = 0.0
            zero_msg.drive.steering_angle_velocity = 0.0
            self.zero_teleop_pub.publish(zero_msg)


def main(args=None):
    rclpy.init(args=args)
    node = DriveModeManager()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
