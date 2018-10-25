# Development

How to setup and use a notams tool development environment

* Install vagrant on your host using the appropriate installer from [here](https://www.vagrantup.com/downloads.html).
* Pick a directory.  I used `~/src`.  Clone the notams repository into that directory.  For example:

        cd ~/src
        git clone git@github.com:amattheisen/notams.git notams
        cd notams && git checkout master && cd ..

* Start the development VM.  This may take over an hour the first time you run it and the box centos/7 is downloaded.  For example:

        cd ~/src/notams/vagrant
        vagrant up

* SSH into the development VM as user vagrant.

        cd ~/src/notams/vagrant
        vagrant ssh

    -OR-

        ssh notams@192.168.36.91

    -OR-

        ssh -p 2291 notams@localhost

* View the tool at

        http://192.168.36.91

    -OR-

        http://localhost:8091
