from setuptools import setup, find_namespace_packages

# read the contents of the README file
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


setup(
    # meta data
    name='laserinterface',
    version='0.1',
    description='Interface for GRBL lasercutters with embedded Pi.',
    long_description=long_description,
    long_description_content_type='text/markdown',

    author='Jelmer Volbeda',
    author_email='jvolbeda22@gmail.com',

    # dependencies
    install_requires=[
        'docutils' ,
        'pygments' ,
        'pypiwin32' ,
        'kivy_deps.sdl2==0.1.*' ,
        'kivy_deps.glew==0.1.*',
        'kivy==1.11.1',

        'ruamel.yaml',
        'pyserial',
    ],

    packages=find_namespace_packages(),
    package_data={
        '': ['*.txt', '*.yaml'],
    }
)
