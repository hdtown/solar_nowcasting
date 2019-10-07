import numpy as np
import glob
import sys
from matplotlib import pyplot as plt
import stat_tools as st
from datetime import datetime
from scipy import ndimage
import ephem
import configparser as cfg


#####params: nx0,cy,cx,rotation,beta,azm
params = {'HD2C':[2821.0000,1442.8231,1421.0000,0.1700,-0.0135,-2.4368,0.3465,-0.0026,-0.0038],\
          'HD2A':[2821.0000,1424,1449.0000,0.0310,-0.0114,-0.9816,0.3462,-0.0038,-0.0030 ],\
#           'HD490':[2843.0000,1472.9511,1482.6685,0.1616,0.0210,-0.5859,0.3465,-0.0043,-0.0030], \
          'HD1B':[2830.0007,1473.2675,1459.7203,-0.0986,-0.0106,-1.2440,0.3441,-0.0015,-0.0042], \
          'HD1A':[2826.5389,1461.0000,1476.6598,-0.0097,0.0030,2.9563,0.3415,0.0004,-0.0044], \
          'HD1C':[2812.7874,1475.1453,1415.0000,0.1410,-0.0126,0.4769,0.3441,0.0004,-0.0046],
          'HD4A':[2813.3741,1435.1706,1453.7087,-0.0119,-0.0857,-1.8675,0.3499,-0.0033,-0.0027], \
          'HD4B':[2809.2813,1446.4900,1438.0777,-0.0237,-0.0120,-1.3384,0.3479,-0.0024,-0.0037], \
          'HD5A':[2813.7462,1472.2066,1446.3682,0.3196,-0.0200,-1.9636,0.3444,-0.0008,-0.0042], \
          'HD5B':[2812.1208,1470.1824,1465.0000,-0.1228,-0.0020,-0.5258,0.3441,-0.0001,-0.0042],\
#           'HD3A':[2807.8902,1436.1619,1439.3879,-0.3942,0.0527,2.4658,0.3334,0.0129,-0.0085],\
          'HD3A':[ 2831.6921,1461.7740,1465.0000,-0.4073,0.0054,2.0156,0.3564,-0.0176,0.0009 ],\
          'HD3B':[2814.3693,1473.3718,1445.8960,0.1977,-0.0350,-1.3646,0.3473,-0.0031,-0.0031],\
          'HD2B':[2810.0000,1428.1154,1438.3745,0.1299,0.0167,2.0356,0.3480,-0.0049,-0.0025]}


if __name__ == "__main__":  
    ######load the configuration file
    config_file = sys.argv[1] if len(sys.argv) >= 2 else 'imager_calibration.conf'
    config = cfg.ConfigParser()
    config.read(config_file)
    
    cameraID = config['camera']['cameraID']
    imagepath = config['path']['imagepath']
    outpath = config['path']['outpath']
    lat = float(config['geolocation']['lat'])
    lon = float(config['geolocation']['lon'])
    
nx0=ny0=params[cameraID][0]
nr0=(nx0+ny0)/4
xstart=int(params[cameraID][2]-nx0/2+0.5); ystart=int(params[cameraID][1]-ny0/2+0.5)
nx0=int(nx0+0.5); ny0=int(ny0+0.5)
roi=np.s_[ystart:ystart+ny0,xstart:xstart+nx0]

gatech = ephem.Observer(); 
gatech.lat, gatech.lon = '40.88', '-72.87'
moon=ephem.Moon() 

#ref=np.load(outpath+cameraID+'.npy').item();
ref={}

flist=sorted(glob.glob(imagepath + '/' + cameraID + '*jpg'));  
print(imagepath,flist)
for cnt,f in enumerate(flist):     
#     print(f)
    doy=f[-18:-4]
    
    gatech.date = datetime.strptime(doy,'%Y%m%d%H%M%S').strftime('%Y/%m/%d %H:%M:%S')
    moon.compute(gatech) 
    sz=np.pi/2-moon.alt; saz=(params[cameraID][3]+moon.az-np.pi)%(2*np.pi);     
     
    rref=np.sin(sz/2)*np.sqrt(2)*nr0
    xref,yref=nx0//2+rref*np.sin(saz),ny0//2+rref*np.cos(saz)
    xref=int(xref); yref=int(yref)
    
    img=plt.imread(f).astype(np.float32);
    img=img[roi]
#     plt.figure(); plt.imshow(img/255);
    img=(0.8*img[:,:,2]+0.2*img[:,:,0])
#     img=np.nanmean(img,axis=2); #plt.figure(); plt.imshow(img)
    
    x1,x2=max(0,xref-150),min(nx0,xref+150)
    y1,y2=max(0,yref-150),min(ny0,yref+150)
    img=img[y1:y2,x1:x2]
    
#     img_m=st.rolling_mean2(img,11)
#     thresh=img_m>200
    
    img_m=st.rolling_mean2(img,71,ignore=0)
    img_m=img-img_m; img_m-=np.nanmean(img_m)
    std=np.nanstd(img_m)
    thresh=img_m>4*std
    
#     t=time.time()
    s = ndimage.generate_binary_structure(2,2) # iterate structure
    labeled_mask, cc_num = ndimage.label(thresh,s)
    try:
        thresh = (labeled_mask == (np.bincount(labeled_mask.flat)[1:].argmax() + 1))
    except:
        continue
    if  np.sum(thresh)<=9:
        print('Moon not found.')
        continue
    
    # Find coordinates of thresholded image
    [y,x] = np.nonzero(thresh)[:2];
    filter=(np.abs(y-np.mean(y))<2.5*np.std(y)) & (np.abs(x-np.mean(x))<2.5*np.std(x))
    # Find average
    xmean = xstart+x1+np.nanmean(x[filter]);
    ymean = ystart+y1+np.nanmean(y[filter]);
    if xmean>200 and ymean>100:
        ref[doy]=[ymean,xmean]
        print('\''+doy+'\': [',int(ymean+0.5),int(xmean+0.5),'], ')
    if cnt % 15==0:
        fig,ax=plt.subplots(1,3,sharex=True,sharey=True); 
        ax[0].imshow(img);    ax[1].imshow(img_m);   ax[2].imshow(thresh);         

np.save(outpath + '/' + cameraID + 'calibration_data',ref)    
    