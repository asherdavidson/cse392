# CSE392 Spring 2018 Homework 0

In this course a Linux virtual machine will be used as the development environment, and Docker will be used to make your applications portable and deployable.
In addition, we will provide you with a git repository hosted on a department GitLab server.
This document will briefly outline how to set up the git respostiory, virtual machine, and Docker.

## Setting up your CSE392 Git repository

Git is an open-source distributed version control system.
Git repositories will be used to manage your homework submissions.
The use of git allows the Professor and TAs to access and view your your code remotely in order to assist you.
Additionally, you have the option of working with a partner and sharing a git repository.
Git will allow you and your partner to efficiently work on your homework assignments in tandem.

You will use a CSE department supported git web interface called Gitlab to manage your git respository.
Gitlab is similar to other git interfaces such as github, bitbucket, etc.
These services are nothing more than INTERFACES to git, not git itself.
You *may not* use external repositories as we will use the repo provided to you to grade your submitted work and share gradesheets with you.

To setup your repository:

1. Navigate to [https://gitlab03.cs.stonybrook.edu](https://gitlab03.cs.stonybrook.edu/) and log into it with you CS email account (user name only, do not include the `@cs.stonybrook.edu`).
If you forgot your CS email password you can reset it by following the instructions [here](https://auth02.cs.stonybrook.edu:10443/react/).
If those instructions fail, please email `rt@cs.stonybrook.edu` requesting a password reset.
A response from them may take up to 24-48 hours.
2. Once logged in, fill out this [form](https://goo.gl/forms/A3raoQIPJWEbH8P23) and wait to receive an email from cse392@cs.stonybrook.edu confirming repository creation.
A response from them may take up to 24-48 hours. **Fill out only one form per group.**

## Setting up the Virtual Machine

The Linux Mint 18.3 "Sylvia" - Cinnamon (64-bit) distribution will be used as this semester's development environment.
Any virtualization software can be used to run your virtual machine, however, we advise that you take advantage of the free VMWare license provided to Stony Brook students.

#### Getting VMware

Download VMWare Workstation for Windows/Linux or VMWare Fusion for OSX.

You can find VMware on Stony Brook's [OnTheHub](https://stonybrook.onthehub.com) software distribution site, under the vmware tab.
If you're running Linux or Windows you'll need **VMware Workstation 14**.
If you're running MacOS you'll need **VMware Fusion 10**.

If you need help installing VMWare or retrieving the license you please contact Stony Brook's [Customer Engagement and Support](https://it.stonybrook.edu/services/service-center).

#### Installing Linux Mint

Download the Linux Mint 18.3 "Sylvia" - Cinnamon (64-bit) distribution from [here](https://linuxmint.com/edition.php?id=246).

If you are using VMWare follow these [instructions](https://partnerweb.vmware.com/GOSIG/Ubuntu_16_04_LTS.html) in order to install the distribution you just downloaded.
Otherwise follow the instructions listed in the documentation of the virtualization software that you are using.

# Docker

Docker is a platform that provides a way to automate the development and deployment of applications as portable self-sufficient **containers**.
A container is an image that has everything that a piece of software needs to run including code, runtime tools, libraries, and settings.

Docker and Docker Compose will be used for this course as they:
* Give you complete control over how your program is ran.
* Easily run multiple instances of your program.
* Isolate your program from the rest of your operating system.

Follow the installation instructions below as the one's on docker's site do not work out of the box for Linux Mint.
Please take the time to complete the Docker [tutorial](https://docs.docker.com/get-started/#a-brief-explanation-of-containers).
You do not need a docker account to use docker.

The Docker tutorial is very extensive and you do not need to go through all of it. 
Most of the docker materials and commands will be provided / explained in the homework document. 
However, it is best to familiarize yourself with Docker as much as possible for your own knowledge. 

## Installing Docker in your VM

Run apt update to get latest repository information:
```sh
sudo apt update
```
Install some prerequisites:
```sh
sudo apt install apt-transport-https ca-certificates curl software-properties-common
```
Add Docker's official GPG key:
```
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
```
Add the Docker repository:
```sh
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu xenial stable"
```
Apt update and Install docker:
```sh
sudo apt update
sudo apt install docker-ce
```

Add your user to the docker group. **You must logout and log back in after executing this command**
```sh
sudo usermod -aG docker $USER
```

Test it!
```sh
docker run hello-world
```

### Install Docker Compose

Download the script and make sure its executable
```sh
sudo curl -L https://github.com/docker/compose/releases/download/1.18.0/docker-compose-`uname -s`-`uname -m` -o /usr/local/bin/docker-compose && sudo chmod +x /usr/local/bin/docker-compose
```

### Install Docker Machine

Download the script && Make sure its executable
```sh
sudo curl -L https://github.com/docker/machine/releases/download/v0.13.0/docker-machine-`uname -s`-`uname -m` -o /usr/local/bin/docker-machine && sudo chmod +x /usr/local/bin/docker-machine
```

# Python

Some of the assignments in this course permit you to choose between working in Python or C.
If you choose to use python you need to ensure that you are working in the same environment that the TAs will grade in.

0. Install the supporting packages

```sh
sudo apt-get install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev
```

1. Install [pyenv](https://github.com/pyenv/pyenv-installer) in your vm. (It's just the curl command)
2. Close and reopen your shell and you should be able to run `pyenv versions` to test that it works correctly.
3. Run `pyenv install 3.6.4` to install the version of python we'll be using this semester. Not, this takes a while.
4. Run `pyenv global 3.6.4` to set the version of python to the correct one.
5. If you run either `python` or `python3` you should see 3.6.4 displayed as the version

### Modules

Lucky for us Python includes everything you need to do low level socket programming out of the box.
One thing you may encounter in you assignments is working with binary data in some of the more system's specific functions.
Python does have the [`struct`](https://docs.python.org/3/library/struct.html) and [`array`](https://docs.python.org/3/library/array.html) modules to assist with this but it can be cumbersome as the data's complexity increases.

We recommend taking a look now at the `struct` api just see how it works.
Essentially it makes you define a format string representing the various data types in your "struct" and after filling the struct with data you access it using python's index/slice operator `[]`.

To make life a little easier there is a module called [`construct`](https://construct.readthedocs.io/en/latest/).
Take a look here at how you accomplish [structs in construct](https://construct.readthedocs.io/en/latest/basics.html#structs).

You can see that you can name the fields just like you would in C albeit with an alternative syntax.
It is entirely optional to use this module but we will permit it if you find yourself wanting something more capable then the build in `struct` module.

To install it run:

```sh
pip install construct
```

Beyond this module no other third party libraries/modules are permitted. The grading environment is as follows:

```
Package    Version
---------- -------
construct  2.9.25
pip        9.0.1
setuptools 38.4.0
```
> Note: that `setuptools` and `pip` come with your installation of python and their version numbers do not matter.

> Also note that this doesn't mean you cannot install more things in your python environment if you so wish your project just cannot depend on them. (Example. a python linter that installs via pip)

# Homework 0

This part of the document will walk you through completing the academic honesty statement and running a simple client-server program in both your virtual machine and in Docker.

## Directory Layout

```
hw0
├── academic_honesty.txt
├── docker-compose.yml
├── echo_client
│   ├── Dockerfile
│   ├── Makefile
│   └── echo_client.c
└── echo_server
    ├── Dockerfile
    ├── Makefile
    └── echo_server.c
```

Inside of the `hw0` folder you'll find the above directory layout.

* `academic_honesty.txt` - An academic honesty statement that you will sign in the section below.
* `docker-compose.yml`   - A docker compose file that will configure an echo server to run in a docker container.
* `hw0/echo_client`      - A folder containing a `Makefile`, `Dockerfile`, and `C` file for an `echo_client`.
* `hw0/echo_server`      - A folder containing a `Makefile`, `Dockerfile`, and `C` file for an `echo_server`.

## Academic Honesty Statement

In this course we take academic honesty EXTREMELY seriously.
Please read and sign the statement in `academic_honesty.txt`.
Once finished, commit and push your changes to the Gitlab repository.

## Echo Client/Server in a VM

We'll start off by running the client/server on a Linux virtual machine.
This is how you'll be running your code during development and testing.
  
First read through the `Makefile` and `echo_server.c`files so that you have a basic understanding of how this program is compiled and run.
Next compile the server and run it in the background, on a port of your choice, using the following commands.

```sh
make clean all
./echo_server [PORT] &
```

Then `cd` into the `hw0/echo_client` directory and do the same for the `Makefile` and `echo_client.c` files in this directory.
Next compile and run the client using the following commands.

```
make clean all
./echo_client localhost [PORT]
```

You should now be able to type anything you want into the client and have it echoed back to you by the server.
You can also run multiple instances of the client to see how it behaves with the server.

Take a screenshot of the client and server running in your Virtual Machine and upload it to your Gitlab repository under the hw0 folder as `hw0/vm.png`.

A setup like this is nice for development and testing, however, it's not so useful for deployment.
Every single time someone wants to run an instance of the program they have to compile and run it on every server hosting it.
In the next section of this document we'll show you how Docker is used to make the echo server application deployable.

## Echo Client/Server in Docker

Start off by reading through the `Dockerfile`s located in `hw0/echo_client` and `hw0/echo_server` and the `docker-compose.yml` file located in `hw0/`.
Next run the following command to bring up a dockerized instance of the echo server.

```sh
docker-compose up -d
```

If the command executed successfully you should get something similar to the following output when you run `docker-compose ps`.

```sh
$ docker-compose ps
      Name                     Command              State           Ports         
----------------------------------------------------------------------------------
hw0_echo_server_1   /bin/sh -c ./echo_server 5000   Up      0.0.0.0:5000->5000/tcp
```

In order to connect to a dockerized instance of the client to server we need to first build the image and then run it on the same network as the server.
Run the following commands to build and run the client.

```sh
docker build echo_client -t echo_client:latest
docker run -it --network=host echo_client
```

You should now be able to type anything you want into the dockerized client and have it echoed back to you by the dockerized server.
You can also run multiple instances of the dockerized client to play around with docker and to see how it behaves with the dockerized server.

Take a screenshot of the running dockerized client and server and upload it to your Gitlab repository under the hw0 folder as `hw0/docker.png`.

## How to submit your assignment

To submit your assignment for grading tag the commit you intend to submit with `hw0` before the deadline.
This can be done through the Gitlab user interface or through the git command line using the following command.

```sh
git tag -a hw0 [commit]
git push origin --tags
```

> :warning: You only get one change to tag.
> Make sure all your files are committed and push to the gitlab server before you tag. 
