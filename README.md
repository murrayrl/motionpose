
# Installation Instructions

Follow these steps to get your Python environment set up and run the program:
Prerequisites:

    Python 3.11 (make sure Python is installed)

    pip (Python package manager, comes with Python)

## Steps to Install:
### 1. Clone the Repository

Clone the repository to your local machine using git:

`git clone https://github.com/murrayrl/motionpose.git` (Make sure you are in the ZED branch)

`cd motionpose`

### 2. Set Up a Virtual Environment (Recommended)

It’s a good idea to use a virtual environment to manage dependencies. This helps keep your project’s dependencies isolated from other Python projects.

Create a virtual environment:

On Windows:

`python -m venv venv`


Activate the virtual environment:

On Windows:

`.\venv\Scripts\activate`

### 3. Install Required Packages

Now, install all the required dependencies listed in the requirements.txt file:

`pip install -r requirements.txt`

This will install all the necessary packages for your project.
### 4. Verify Installation

To verify that everything was installed correctly, you can check the installed packages:

`pip list`

You should see the list of packages installed from your requirements.txt.


### 5. Install the ZED SDK from this instruction 
https://www.stereolabs.com/docs/app-development/python/install
 
 Make sure you move the 'get_python_api.py' file to a non admin area (for example user folder)
