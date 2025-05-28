# Wound Compute Graphical User Interface (GUI)


## Table of Contents
* [Package Summary](#summary)
* [Installation Instructions](#install)
* [Tutorial](#tutorial)


## Package Summary <a name="summary"></a>

UNDER CONSTRUCTION


## Installation Instructions <a name="install"></a>

### Get a copy of the Wound Compute GUI repository on your local machine

The best way to do this is to create a GitHub account and ``clone`` the repository. However, you can also download the repository by clicking the ``Code`` button and selecting ``Download ZIP``. Downloaded and unzip the ``woundcomputeGUI-main`` folder and place it in a convenient location on your computer.

### Create and activate a conda virtual environment

1. Install [Anaconda](https://docs.anaconda.com/anaconda/install/) on your local machine.
2. Open a ``Terminal`` session (or equivalent) -- note that Mac computers come with ``Terminal`` pre-installed (type ``⌘-space`` and then search for ``Terminal``).
3. Type in the terminal to create a virtual environment with conda:
```bash
conda create --name wound-compute-gui python=3.9.13
```
4. Type in the terminal to activate your virtual environment:
```bash
conda activate wound-compute-gui
```
5. Check to make sure that the correct version of python is running (should be ``3.9.13``)
```bash
python --version
```
6. Update some base modules (just in case)
```bash
pip install --upgrade pip setuptools wheel
```

Note that once you have created this virtual environment you can ``activate`` and ``deactivate`` it in the future -- it is not necessary to create a new virtual environment each time you want to run this code, you can simply type ``conda activate wound-compute-gui`` and then pick up where you left off (see also: [conda cheat sheet](https://docs.conda.io/projects/conda/en/4.6.0/_downloads/52a95608c49671267e40c689e0bc00ca/conda-cheatsheet.pdf)).

### Install wound compute

1. Use a ``Terminal`` session to navigate to the ``woundcomputeGUI-main`` folder. The command ``cd`` will allow you to do this (see: [terminal cheat sheet](https://terminalcheatsheet.com/))
2. Type the command ``ls`` and make sure that the file ``pyproject.toml`` is in the current directory.
3. Now, create an editable install of wound compute:
```bash
pip install -e .
```
4. If you would like to see what packages this has installed, you can type ``pip list``