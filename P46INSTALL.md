# PhiloLogic 4.6 Installation Guide

If you have run into difficulties with the standard PhiloLogic installation guide, below is a step-by-step list of instructions that seem to generally work on a RedHat-flavored Linux+Apache setup.

**NOTE: These instructions are for users who know their way around the command line and have sudo privileges on a machine. If you are not yourself the sys admin for your machine, you may want to consult with them before proceeding.**

## System Prerequisites

- It goes wihout saying that usual development stuff like Make and GCC should already be installed on your system, as well as Apache and Python3. If you do not know what these things are, consult with your system administrator.
- *gdbm* may or may not be installed, so:
```bash
sudo yum install gdbm gdbm-devel
``` 
- Since PhiloLogic 4.6 is using Python3, make sure that you have *python3-devel* installed as well.
```bash
sudo yum install python3-devel
```
- Now some Python stuff:
```bash
sudo pip3 install scikit-build
```

## Install PhiloLogic

- Download PhiloLogic 4.6 from github [here](https://github.com/ARTFL-Project/PhiloLogic4/tree/PhiloLogic-4.6).
- Unzip the archive in some covenient place on your system.
- *cd* to the directory and
```bash
sudo ./install.sh
```
- If you run into build errors with CMake, you may need to update pip, followed by deleting the new config file and running the install again:
```bash
sudo pip3 install --upgrade pip
sudo rm /etc/philologic/philologic4.cfg
sudo ./install.sh
```
- In your Apache config file (probably */etc/httpd/conf/httpd.conf*) add the following:
```apacheconf
<Directory "/var/www/html/philologic4">
    Options FollowSymLinks Multiviews
    MultiviewsMatch Any
    AllowOverride All
    Require all granted
</Directory>
```
- Restart Apache
```bash
sudo apachectl restart
```

## Philo4Classics

- Download Philo4Classics from [here](https://github.com/ARTFL-Project/Philo4Classics) and unzip in a convenient location.
- *cd* to the Philo4Classics *load* directory.
- Modify *Classics_load_config.py* options as necessary.
- If you have a custom AngularJS theme.css, then modify the theme path in */etc/philologic/philologic4.cfg*. If you want to use the ARTFL theme, the css file is located in the *extras* directory in the Philo4Classics repository. **This must be done before you do a load**.
- Install a new load:
```bash
philoload4 -l Classics_load_config.py My_Load_Name /path/to/my/*.xml
```
- Make sure to open the PhiloLogic4.6 load in a browser before the next step.
- Now run the *fix_load.py* script (you should already be in the *load* directory in the Philo4Classics directory). By default, the fix "type" is "text", which is valid for almost all types of PhiloLogic 4.6 loads, except for dictionaries.
```bash
./fix_load.py My_Load_Name
```
