from setuptools import find_packages, setup

package_name = 'frontierx_perception'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('lib/' + package_name,
            [package_name + '/perception_node.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='FrontierX Labs',
    maintainer_email='robotics@frontierxlabs.com',
    description='Computer vision & perception package',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'perception_node = frontierx_perception.perception_node:main',
        ],
    },
)
