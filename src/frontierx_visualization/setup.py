from setuptools import find_packages, setup

package_name = 'frontierx_visualization'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('lib/' + package_name,
            [package_name + '/marker_publisher_node.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='FrontierX Labs',
    maintainer_email='robotics@frontierxlabs.com',
    description='Visualization & marker publisher package',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'marker_publisher_node = frontierx_visualization.marker_publisher_node:main',
        ],
    },
)
