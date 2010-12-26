import SlideShow
import logging, math, os
log = logging.getLogger(__name__)

def accelerate(frame, frames, accel):
    return frame
#        x = 2.0*frame/(frames-1) - 1 # normalize between -1 and 1
#        y = 1./(max(0, min(accel,100)) / 100. + 1)
#        if x > 0:
#            sign = 1
#        else:
#            sign = -1
#        #return (2*abs(x)**y*sign - x + 1)*(frames-1)/2.
#        return (abs(x)**y*sign + 1)*(frames-1)/2.

        

def parse_params(zoom, pos, config, img, src_width, src_height, dest_width,dest_height):
    if zoom == "imagewidth":
        z = dest_width / float(img.width)
    elif zoom == "imageheight":
        z = dest_height / float(img.height)
    else:
        z = eval(zoom.replace("%",""))/100.

    if pos[:3] in ["top", "bot", "lef", "rig","mid"]:
        if pos.find("bottom") > -1:
            yc = img.height - (src_height * z)/2.
        elif pos.find("top") > -1:
            yc = (src_height * z)/2.
        else:
            yc = img.height / 2.
        
        if pos.find("left") > -1:
            xc = (src_width  * z)/2
        elif pos.find("right") > -1:
            xc = img.width  - (src_width  * z)/2
        else:
            xc = img.width / 2.
    else:
        xcp,ycp = map(str.strip, pos.split(","))
        if(xcp.find("%")>-1):
            xcp = eval(xcp.replace("%",""))
            xc  = xcp * src_width  / 100. - (src_width -  img.width )/2.
        else:
            xc = eval(xcp)

        if(ycp.find("%")>-1):
            ycp = eval(ycp.replace("%",""))
            yc = ycp * src_height / 100. - (src_height - img.height)/2.
        else:
            yc = eval(ycp)

    x0 = xc - src_width  / 2. * z
    x1 = xc + src_width  / 2. * z
    y0 = yc - src_height / 2. * z
    y1 = yc + src_height / 2. * z

    return (x0, y0, x1, y1)

def kenburns(config, params, ifile, frames, progress):
    src_img  = SlideShow.Img.read(ifile, SlideShow.Img.YUV)
    dest_img = SlideShow.Img.Image(config["dvd_width"], config["dvd_height"], SlideShow.Img.RGB)

    dest_height = config["dvd_height"]
    dest_width  = dest_height * config["aspect_ratio_float"]

    src_ratio = src_img.width / float(src_img.height)
    if(src_ratio > config["aspect_ratio_float"]):
        src_width  = src_img.width
        src_height = src_width  / config["aspect_ratio_float"]
    else:
        src_height = src_img.height
        src_width  = src_height * config["aspect_ratio_float"]


    field = map(str.strip, params.split(";"))
    img0 = parse_params(field[0], field[1], config, src_img, src_width, src_height, dest_width, dest_height)
    img1 = parse_params(field[2], field[3], config, src_img, src_width, src_height, dest_width, dest_height)

    ## adjust step size: ##############################
    if config["low_quality"]:
    	stepsize=3
    else:
    	stepsize=1
    
    imgs = []
    progress.task_start(frames, "Ken Burns")
    for frame in range(0, frames, stepsize):
        progress.task_update(frame)
        a = accelerate(frame, frames, 15)
        #print frame, a
        xy = [ (xy1-xy0) / float(frames-1) * a + xy0 for xy1, xy0 in zip(img1,img0) ]
        src_img.scale_and_crop(xy[0], xy[1], xy[2], xy[3], dest_img)
        ofile = config["workdir"]+"/"+os.path.basename(ifile)+"%04d"%frame+".ppm"
        dest_img.write(ofile)
        imgs.append((ofile, stepsize))

    progress.task_done()
    return imgs

def cleanup(config, ifile):
    import Element
    ofile = config["workdir"]+"/"+os.path.basename(ifile)+"*.ppm"
    Element.cmd("rm -f "+ofile)
