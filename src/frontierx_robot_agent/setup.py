from setuptools import setup

package_name = 'frontierx_robot_agent'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('lib/' + package_name, ['frontierx_robot_agent/agent_node.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='FrontierX Labs',
    maintainer_email='robotics@frontierxlabs.com',
    description='AI Agent package',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'agent_node = frontierx_robot_agent.agent_node:main',
        ],
    },
)
