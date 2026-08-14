from setuptools import find_packages, setup

package_name = 'frontierx_bringup'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', [
            'launch/core.launch.py',
            'launch/navigation.launch.py',
            'launch/perception.launch.py',
            'launch/central_brain.launch.py',
        ]),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='FrontierX Labs',
    maintainer_email='robotics@frontierxlabs.com',
    description='Bringup launch files for FrontierX Scout',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [],
    },
)
