from setuptools import setup, find_packages

setup(
    name="git-commit-assistant",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests",
        "rich",
        "gitpython",
        "questionary"
    ],
    entry_points={
        "console_scripts": [
            "git-commit-assistant=git_commit_assistant.main:main",
            "gca=git_commit_assistant.main:main",
        ],
    },
    author="Rafael Nogueira",
    description="AI-powered Git commit assistant using Gemini",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/git-commit-assistant",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
) 