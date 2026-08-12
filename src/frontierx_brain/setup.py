from setuptools import find_packages, setup

package_name = 'frontierx_brain'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name] if False else []),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='FrontierX Labs',
    maintainer_email='architect@frontierx.ai',
    description='Central AI Brain and Multi-Robot Orchestrator Platform',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'brain_node = frontierx_brain.ros.ros2_bridge:main',
            'mock_robot_node = frontierx_brain.sim.mock_robot_node:main',
        ],
    },
)
