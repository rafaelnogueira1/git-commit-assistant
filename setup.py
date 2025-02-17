from setuptools import setup, find_packages

setup(
    name="git-commit-assistant",
    version="1.1.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
        "rich>=13.7.0",
        "gitpython>=3.1.40",
        "questionary>=2.0.1",
        "openai>=1.12.0",
        "anthropic>=0.18.1",
    ],
    entry_points={
        "console_scripts": [
            "git-commit-assistant=git_commit_assistant.main:main",
            "ga=git_commit_assistant.main:main",
        ],
    },
    author="Rafael Nogueira",
    description="AI-powered Git commit assistant using multiple AI services",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/rafaelnogueira1/git-commit-assistant",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
) 