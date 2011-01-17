import SlideShow, Element
import logging, math, os
log = logging.getLogger(__name__)


def configure_kenburns(self, kenburns, duration):
    import gst
    for i, fx in enumerate(self.effects):
        if fx.name == "kenburns":
            zstart, pstart, zend, pend = map(str.strip, fx.param.split(";"))
            zpos1, xpos1, ypos1 = parse_kb_params(zstart, pstart, self.config, self.width, self.height)
            zpos2, xpos2, ypos2 = parse_kb_params(zend,   pend,   self.config, self.width, self.height)
            c = gst.Controller(kenburns, "zpos", "ypos", "xpos")
            c.set_interpolation_mode("xpos", gst.INTERPOLATE_LINEAR)
            c.set_interpolation_mode("ypos", gst.INTERPOLATE_LINEAR)
            c.set_interpolation_mode("zpos", gst.INTERPOLATE_LINEAR)
            c.set("zpos", 0,        zpos1)
            c.set("zpos", duration, zpos2)
            c.set("xpos", 0,        xpos1)
            c.set("xpos", duration, xpos2)
            c.set("ypos", 0,        ypos1)
            c.set("ypos", duration, ypos2)
            self.controllers.append(c)
            #kenburns.props.verbose = 1


def parse_kb_params(zoom, pos, config, width, height):
    img_ratio = width / float(height)
    vid_ratio = config["aspect_ratio_float"]

    if(img_ratio > vid_ratio):
        src_width = width
        src_height = int(round(src_width / vid_ratio))
    else:
        src_height = height
        src_width = int(round(src_height * vid_ratio))

    if zoom == "imagewidth":
        z = width / float(src_width)
    elif zoom == "imageheight":
        z = height / float(src_height)
    elif(zoom.endswith("%")):
        z = eval(zoom.replace("%",""))/100.
    else:
        raise Exception("Unknown kenburns zoom parameter '%s'" % (zoom, ))

    if pos[:3] in ["top", "bot", "lef", "rig", "mid"]:
        if pos.find("bottom") > -1:
            yc = (src_height - height)/2. - (src_height  * z)/2 + height
        elif pos.find("top") > -1:
            yc = (src_height - height)/2. + (src_height  * z)/2
        else:
            yc = src_height / 2.
        
        if pos.find("left") > -1:
            xc = (src_width - width)/2. + (src_width  * z)/2
        elif pos.find("right") > -1:
            xc = (src_width - width)/2. - (src_width  * z)/2 + width
        else:
            xc = src_width / 2.

        xcenter = xc / float(src_width)
        ycenter = yc / float(src_height)
    else:
        xcp,ycp = map(str.strip, pos.split(","))
        if(xcp.find("%")>-1):
            xcenter = eval(xcp.replace("%","")) / 100.
        else:
            xcenter = eval(xcp) / float(src_width)

        if(ycp.find("%")>-1):
            ycenter = eval(ycp.replace("%","")) / 100.
        else:
            ycenter = eval(ycp) / float(src_height)

    return (z, (xcenter-0.5)*2, (ycenter-0.5)*2)


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
        ofile = config["workdir"]+"/"+os.path.basename(ifile)+"_"+Element.get_unique()+".ppm"
        dest_img.write(ofile)
        imgs.append((ofile, stepsize))

    progress.task_done()
    return imgs

def cleanup(config, ifile):
    import Element
    ofile = config["workdir"]+"/"+os.path.basename(ifile)+"*.ppm"
    Element.cmd("rm -f "+ofile)
