import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'frontierx_sim'


def package_files(folder: str, pattern: str = '*'):
    return glob(os.path.join(folder, pattern)) if os.path.isdir(folder) else []


setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', package_files('launch', '*.py')),
        ('share/' + package_name + '/worlds', package_files('worlds', '*.sdf')),
        ('share/' + package_name + '/config', package_files('config', '*.yaml')),
        ('share/' + package_name + '/scripts',
         package_files(os.path.join(package_name, 'scripts'), '*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='FrontierX Labs',
    maintainer_email='robotics@frontierxlabs.com',
    description='Simulation interface for FrontierX robot bodies using Isaac Sim and Gazebo Sim',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'joint_state_publisher = frontierx_sim.scripts.joint_state_publisher:main',
        ],
    },
)
