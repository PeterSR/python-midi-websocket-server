from setuptools import setup, find_packages

with open('README.md') as f:
    readme = f.read()

setup(
    name='midi-websocket-server',
    version='1.0.0',
    description='Python Websocket server to facilitate two-way communication with all connected MIDI devices.',
    long_description=readme,
    url='https://github.com/PeterSR/python-midi-websocket-server',
    author='Peter Severin Rasmussen',
    author_email='git@petersr.com',
    license='MIT',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.7',
    ],
    packages=find_packages(exclude=('tests', 'docs')),
    install_requires=[
        'websockets>=8.1',
        'python-rtmidi>=1.4.0',
    ],
    python_requires='>=3.7',
)