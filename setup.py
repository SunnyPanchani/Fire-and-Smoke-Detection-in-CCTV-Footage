from setuptools import setup, find_packages

setup(
    name='fire_smoke_detection',
    version='0.1.0',
    description='Real-time fire and smoke detection using YOLOv8 and Flask',
    author='Your Name',
    packages=find_packages(include=['src', 'utils']),
    include_package_data=True,
    install_requires=[],
)
