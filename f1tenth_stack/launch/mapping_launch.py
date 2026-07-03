from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    slam_toolbox_launch = os.path.join(
        get_package_share_directory('slam_toolbox'),
        'launch',
        'online_async_launch.py'
    )

    default_params_file = os.path.join(
        get_package_share_directory('f1tenth_stack'),
        'config',
        'f1tenth_online_async.yaml'
    )

    default_rviz_config = os.path.join(
        get_package_share_directory('f1tenth_stack'),
        'launch',
        'mapping.rviz'
    )

    params_file_la = DeclareLaunchArgument(
        'params_file',
        default_value=default_params_file,
        description='SLAM Toolbox parameter file'
    )

    rviz_la = DeclareLaunchArgument(
        'rviz',
        default_value='true',
        description='Start RViz2 with the mapping visualization config'
    )

    rviz_config_la = DeclareLaunchArgument(
        'rviz_config',
        default_value=default_rviz_config,
        description='RViz2 config file for onboard mapping'
    )

    slam_toolbox = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(slam_toolbox_launch),
        launch_arguments={
            'params_file': LaunchConfiguration('params_file')
        }.items()
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2_mapping',
        arguments=['-d', LaunchConfiguration('rviz_config')],
        condition=IfCondition(LaunchConfiguration('rviz')),
        output='screen'
    )

    return LaunchDescription([
        params_file_la,
        rviz_la,
        rviz_config_la,
        slam_toolbox,
        rviz_node,
    ])
