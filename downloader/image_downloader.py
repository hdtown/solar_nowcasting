import sys
import glob
from datetime import datetime,timezone
import urllib.request as req
import ssl
import time
import pysolar.solar as ps
import socket
import multiprocessing
from threading import Event, Thread
import configparser as cfg
import logging
from os import system,path,chmod,rename
try:
    from os import mkdirs  ###for python3.5
except:
    from os import makedirs as mkdirs ####for python3.6 and above

flush_interval = 86400 ####copy files from cache every day

socket.setdefaulttimeout(2);

####util function to call a routine at a specified interval
def call_repeatedly(intv, func, *args):
    stopped = Event()
    def loop():
        while not stopped.wait(intv): # the first call is in `intv` secs
            func(*args)
    Thread(target=loop).start()    
    return stopped.set

######copy files from cache to output directory
def flush_files(cams):
    for camera in cams:
        fns=glob.glob(cachepath+camera+'/*jpg')
        print(camera,len(fns))
        for fn in fns:
            doy=fn[-18:-10]
            dest=imagepath+camera+'/'+doy
            if not path.isdir(dest):
                mkdirs(dest)
                chmod(dest,0o755)
            rename(fn,dest+'/'+camera+'_'+fn[-18:])

####download images from cameras to "cache" and also make a copy to "latest" directory
####the "latest" directory enables the web dashboard to show real time images
def makeRequest(cam):
    starttime = datetime.utcnow()
    timestamp=starttime.strftime("%Y%m%d%H%M%S")
# for improper ssl certificates, try this to ignore CERTs
    context=ssl.create_default_context()
    context.check_hostname=False
    context.verify_mode=ssl.CERT_NONE

    proxy = req.ProxyHandler({})
    opener = req.build_opener(proxy,req.HTTPSHandler(context=context))
    req.install_opener(opener)
    try:
        fn=path.join(cachepath,cam,cam+"_"+timestamp+".jpg")
# neither this:
        req.urlretrieve(urls[cam]+url_suffix,fn)
# nor this:
#        with req.urlopen(urls[cam]+url_suffix) as f:
#            with open(fn,'w') as ofn:
#                ofn.write(f.read())
# works right now, no errors reported for some reason, but when I do it interactively,
# I get: urlopen error [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE]
        chmod(fn,0o755); ####set the permission
    except Exception as e: 
        logger.error('Cannot retrieve image from: '+cam)
        return
    try:
        fn_latest=latest+cam+'_latest.jpg'
        system('cp '+fn+' '+fn_latest);
        chmod(fn_latest,0o755); ####set the permission
    except Exception as e: 
        return

if __name__ == "__main__":  
    ######load the configuration file
    config_file = sys.argv[1] if len(sys.argv)>=2 else 'image_downloader.conf'
    config=cfg.ConfigParser()
    config.read(config_file)
    url_suffix=config['network']['url_suffix']
    interval_day=float(config['interval']['interval_day'])
    interval_night=float(config['interval']['interval_night'])
    cachepath=config['path']['cachepath']
    latest=config['path']['latest']
    imagepath=config['path']['imagepath']
    logpath=config['path']['logpath']
    lat=float(config['geolocation']['lat'])
    lon=float(config['geolocation']['lon'])
    urls={}
    ####create the directories if they do not already exist
    for dest in [cachepath,latest,imagepath]:
        if not path.isdir(dest):
            mkdirs(dest)
            chmod(dest,0o755)
    for cameraID,url in config['camera'].items():
        cameraID=cameraID.upper()
        urls[cameraID]=url
        dest=cachepath+cameraID
        if not path.isdir(dest):
            mkdirs(dest)
            chmod(dest,0o755)
        dest=imagepath+cameraID
        if not path.isdir(dest):
            mkdirs(dest)
            chmod(dest,0o755)
    
    #####initialize the logger
    logging.basicConfig(format='%(asctime)s [%(funcName)s] [%(process)d %(thread)d] %(levelname)s: %(message)s',\
                        level=logging.INFO,filename=path.join(logpath,'image_downloader.log'),filemode='w')
    logger=logging.getLogger(__name__)

    flush_event = call_repeatedly(flush_interval, flush_files, urls)

    p = multiprocessing.Pool(len(urls))
    while (True):
        day_flag = ps.get_altitude(lat,lon,datetime.now(timezone.utc))>5
        intv=interval_day if day_flag else interval_night
        saveimage_event = call_repeatedly(intv, p.map_async, makeRequest, urls)
        
        if day_flag:
            while ps.get_altitude(lat,lon,datetime.now(timezone.utc))>5:  
                time.sleep(180)
        else:
            while ps.get_altitude(lat,lon,datetime.now(timezone.utc))<=5:  
                time.sleep(600)
        saveimage_event()
            
