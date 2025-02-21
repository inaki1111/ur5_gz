from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command, TextSubstitution
from launch_ros.substitutions import FindPackageShare
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.conditions import IfCondition
from launch.substitutions import IfElseSubstitution

def generate_launch_description():
    declared_arguments = []

    # Argumentos
    declared_arguments.append(
        DeclareLaunchArgument(
            "description_file",
            default_value=PathJoinSubstitution(
                [FindPackageShare("moveit_ur_config"), "config", "ur5.urdf.xacro"]
            ),
            description="Robot description.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "world_file",
            default_value="empty.sdf",
            description="Gazebo empty world file",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "gazebo_gui",
            default_value="true",
            description="Launch Gazebo with GUI enabled.",
        )
    )

    # Incluir el launch de MoveIt
    moveit_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare("moveit_ur_config"), "launch", "demo.launch.py"])
        )
    )

    # Configuración de Gazebo Sim
    world_file = LaunchConfiguration("world_file")
    gazebo_gui = LaunchConfiguration("gazebo_gui")

    gz_launch_description = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [FindPackageShare("ros_gz_sim"), "/launch/gz_sim.launch.py"]
        ),
        launch_arguments={
            "gz_args": IfElseSubstitution(
                gazebo_gui,
                if_value=[" -r -v 1 --physics-engine gz-physics-bullet-featherstone-plugin ", world_file],
                else_value=[" -s -r -v 1 --physics-engine gz-physics-bullet-featherstone-plugin ", world_file],
            )
        }.items(),
    )

    # Convertir XACRO a URDF antes de pasarlo a Gazebo
    robot_description_file = PathJoinSubstitution([
        FindPackageShare("moveit_ur_config"), "config", "ur5.urdf.xacro"
    ])
    robot_description_content = Command([
        TextSubstitution(text="xacro "), robot_description_file
    ])

    # Spawning del robot en Gazebo
    gz_spawn_entity = Node(
        package="ros_gz_sim",
        executable="create",
        output="screen",
        arguments=[
            "-string", robot_description_content,
            "-name", "ur",
            "-allow_renaming", "true",
        ],
    )

    # Bridge entre ROS 2 y Gazebo
    gz_sim_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=[
            "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock]",
            "/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model]",
        ],
        output="screen",
    )

    # Agregar el spawner de joint_state_broadcaster antes de los otros controladores
    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster"],
        output="screen",
    )

    follow_joint_trajectory_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["follow_joint_trajectory_controller"],
        output="screen",
    )


    return LaunchDescription(
        declared_arguments + [
            moveit_launch,
            gz_launch_description,
            gz_spawn_entity,
            gz_sim_bridge,
            joint_state_broadcaster_spawner,
            follow_joint_trajectory_spawner,
        ]
    )
