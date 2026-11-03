from glob import glob

from setuptools import setup

package_name = "slam_bringup"

setup(
    name=package_name,
    version="0.1.0",
    packages=[],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
        ("share/" + package_name + "/config", glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Anders Frandsen",
    maintainer_email="anfran@anfran.dk",
    description="Launch files and parameters for the RoboBob robot",
    license="MIT",
)
