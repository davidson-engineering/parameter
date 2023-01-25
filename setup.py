from setuptools import setup, find_packages

with open("README.md") as f:
    readme = f.read()

with open("LICENSE") as f:
    license = f.read()

setup(
    name="project_name",
    version="0.1.0",
    description="module description",
    long_description=readme,
    url="https://github.com/generalmattza/project_name.git",
    author="Matthew Davidson",
    author_email="matthew.davidson@generalfusion.com",
    license=license,
    packages=find_packages(exclude=("tests", "docs")),
    install_requires=[
        "module_name @ git+https://github.com/generalmattza/module_name.git@main",
        "package0>=0.0.0",
        "package1==0.0.0",
    ],
    classifiers=[
        "Development Status :: 1 - Planning",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3.10",
    ],
)
