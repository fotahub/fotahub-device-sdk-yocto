from setuptools import setup, find_packages

# Prerequisites: sudo apt-get install pkg-config libcairo2-dev gcc python3-dev libgirepository1.0-dev

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='fotahubclient',
    version='0.1.0',
    author='FotaHub',
    author_email='contact@fotahub.com',
    description='FotaHub Client enabling operating system or selected applications on Linux-based IoT edge devices to be over-the-air updated',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/fotahub/fotahub-device-sdk-yocto',
    project_urls = {
        "Issue Tracker": "https://github.com/fotahub/fotahub-device-sdk-yocto/issues"
    },
    license='Apache-2.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'gobject',
        'PyGObject',
        'pydbus',
        'stringcase',
    ],
    entry_points='''
        [console_scripts]
        fotahub=fotahubclient.cli.main:main
    ''',
)