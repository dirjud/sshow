import Element, os

def annotate(config, imgs, params, progress):
    params = map(str.strip, params.split(";"))
    opts = " -gravity center "
    # valid params:
    #  text= ;
    #  position = [+-]X%, [+-]Y%;   (as percent of total image)
    #  pointsize=X%;                (as percent of total image)
    #  stroke=color;                ('black', 'white', 'orange','0x556633')
    #  fill=color;                  ('black', 'white', 'orange','0x556633')
    #  font=font;
    #  undercolor=color;
    position = " +0+0 "
    text = "Please Specify 'text' param"
    for param in params:
        key,val = param.split("=",1)
        if key == "text":
            text = val
        elif key == "position":
            x,y = map(str.strip, val.split(",",1))
            posx = int(round((eval(x.replace("%",""))-50)*config["dvd_width"] /100.))
            posy = int(round((eval(y.replace("%",""))-50)*config["dvd_height"]/100.))
            if(posx >= 0):
                position = "+"+str(posx)
            else:
                position = str(posx)
            if(posy >= 0):
                position += "+"+str(posy)
            else:
                position += str(posy)
        elif key == "pointsize":
            val = round(config["dvd_height"] * eval(val.replace("%","")) / 10.)/10.
            opts += " -%s %s " % (key, val)
        else:
            opts += " -%s '%s' " % (key, val)
    new_imgs = []
    progress.task_start(len(imgs), "Annotate")
    for i, (filename,num_frames) in enumerate(imgs):
        progress.task_update(i)
        ofile = filename + "_annotate_"+Element.get_unique()+".ppm"
        convert = "convert " + filename + opts + "-annotate "+position+" '" + text.replace("'","'\"'\"'") + "' " + ofile
        #print convert
        Element.cmd(convert)
        new_imgs.append((ofile, num_frames))
    progress.task_done()
    return new_imgs

def cleanup(config, ifile):
    import Element
    ofile = config["workdir"]+"/"+os.path.basename(ifile)+"*_annotate_*.ppm"
    Element.cmd("rm -f "+ofile)
    
