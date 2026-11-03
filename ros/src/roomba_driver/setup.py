from setuptools import setup

package_name = "roomba_driver"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Anders Frandsen",
    maintainer_email="anfran@anfran.dk",
    description="Roomba 600 Open Interface driver over a pigpio bit-bang UART",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "roomba_driver = roomba_driver.node:main",
        ],
    },
)
