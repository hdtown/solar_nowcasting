import os
import glob
from datetime import datetime,timezone
import urllib.request as req
import time
import pysolar.solar as ps
import socket
import multiprocessing
from threading import Event, Thread
import configparser as cfg
import logging

organize_interval = 86400 ####organize files once per day

socket.setdefaulttimeout(2);

def call_repeatedly(intv, func, *args):
    stopped = Event()
    def loop():
        while not stopped.wait(intv): # the first call is in `intv` secs
            func(*args)
    Thread(target=loop).start()    
    return stopped.set

def organize_files(cams):
    for camera in cams:
        fns=glob.glob(cachepath+camera+'/*jpg')
        print(camera,len(fns))
        for fn in fns:
            doy=fn[-18:-10]
            dest=outpath+camera+'/'+doy
            if not os.path.isdir(dest):
                os.makedirs(dest)
                os.chmod(dest,0o755)
            os.rename(fn,dest+'/'+camera+'_'+fn[-18:])

def makeRequest(cam):
    starttime = datetime.utcnow()
    timestamp=starttime.strftime("%Y%m%d%H%M%S")
    proxy = req.ProxyHandler({})
    opener = req.build_opener(proxy)
    req.install_opener(opener)
    try:
        fn=cachepath+cam+"/"+cam+"_"+timestamp+".jpg"
        req.urlretrieve("http://"+ips[cam]+url_suffix, fn)
        os.chmod(fn,0o755); ####set the permission
    except Exception as e: 
        logger.error('Cannot retrieval image from: '+cam)
        return
    try:
        fn_latest=latest+cam+'_latest.jpg'
        os.system('cp '+fn+' '+fn_latest);
        os.chmod(fn_latest,0o755); ####set the permission
    except Exception as e: 
        return

if __name__ == "__main__":  
    ######load configuration file
    config=cfg.ConfigParser()
    config.read('config.conf')
    url_suffix=config['network']['url_suffix']
    interval_day=float(config['interval']['interval_day'])
    interval_night=float(config['interval']['interval_night'])
    cachepath=config['path']['cachepath']
    latest=config['path']['latest']
    imagepath=config['path']['imagepath']
    lat=float(config['geolocation']['lat'])
    lon=float(config['geolocation']['lon'])
    ips={}
    for cameraID,ip in config['camera'].items():
        cameraID=cameraID.upper()
        ips[cameraID]=ip
        dest=cachepath+cameraID
        if not os.path.isdir(dest):
            os.makedirs(dest)
            os.chmod(dest,0o755)
        dest=imagepath+cameraID
        if not os.path.isdir(dest):
            os.makedirs(dest)
            os.chmod(dest,0o755)
    
    #####initialize the logger
    logging.basicConfig(format='%(asctime)s [%(funcName)s] [%(process)d %(thread)d] %(levelname)s: %(message)s',\
                        level=logging.INFO,filename='downloader.log',filemode='w')
    logger=logging.getLogger(__name__)


    organize_event = call_repeatedly(organize_interval, organize_files, ips)

    p = multiprocessing.Pool(len(ips))
    while (True):
        day_flag = ps.get_altitude(lat,lon,datetime.now(timezone.utc))>5
        intv=interval_day if day_flag else interval_night
        saveimage_event = call_repeatedly(intv, p.map_async, makeRequest, ips)
        
        if day_flag:
            while ps.get_altitude(lat,lon,datetime.now(timezone.utc))>5:  
                time.sleep(180)
        else:
            while ps.get_altitude(lat,lon,datetime.now(timezone.utc))<=5:  
                time.sleep(600)
        saveimage_event()
            
