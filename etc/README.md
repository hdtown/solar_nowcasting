This systemd service config file image_downloader.service should be
installed into the directory returned by:

`pkg-config systemd --variable=systemdsystemunitdir`
	
It runs the commands in /home/nowcast/run/image_downloader.sh.
To enable add boot

`systemctl enable image_downloader`
	
To start

`systemctl start image_downloader`
	
The status is shown with

`systemctl status -l image_downloader`
	
Note: This also shows the subprocesses started, and the last error
messages.

The process is supposed to restart with a 1 s delay when it dies and
disable itself if there are more than 5 restarts in a 10 s interval.
Killing a sub-process restarts automatically within 1 s.
