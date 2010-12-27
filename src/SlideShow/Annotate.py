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
    text = "Please Specify 'text' param"

    args = { "gravity" : "center", "duration" : 0 }
    for key in [ "annotate_pointsize", "annotate_font", "annotate_fill", "annotate_stroke", "annotate_position", "annotate_undercolor" ]:
        if config[key]:
            args[key.replace("annotate_","")] = config[key]

    for param in params:
        key,val = param.split("=",1)
        if key == "text":
            text = val
        else:
            args[key] = val

    if args.has_key("position"):
        x,y = map(str.strip, args["position"].split(",",1))
        posx = int(round((eval(x.replace("%",""))-50)*config["dvd_width"] /100.))
        posy = int(round((eval(y.replace("%",""))-50)*config["dvd_height"]/100.))
        if(posx >= 0):
            args["position"] = "+"+str(posx)
        else:
            args["position"] = str(posx)
        if(posy >= 0):
            args["position"] += "+"+str(posy)
        else:
            args["position"] += str(posy)

    if args.has_key("pointsize"):
        args["pointsize"] = round(config["dvd_height"] * eval(args["pointsize"].replace("%","")) / 10.)/10.


    keys = args.keys()
    keys.remove("position")
    keys.remove("duration")
    opts = " ".join(["-%s '%s'" % (k,args[k]) for k in keys])
    new_imgs = []
    progress.task_start(len(imgs), "Annotate")
    if(args["duration"] == 0):
        dur_frames = 100000
    else:
        dur_frames = int(round(eval(args["duration"]) * config["framerate"]))

    frame_count = 0
    done = False
    for i, (filename,num_frames) in enumerate(imgs):
        frame_count += num_frames
        if not(done):
            progress.task_update(i)
            ofile = filename + "_annotate_"+Element.get_unique()+".ppm"
            convert = "convert " + filename + " " + opts + " -annotate "+args["position"]+" '" + text.replace("'","'\"'\"'") + "' " + ofile
            #print convert
            Element.cmd(convert)
            new_imgs.append([ofile, num_frames])
            if(frame_count > dur_frames):
                extra = frame_count - dur_frames
                new_imgs[-1][1] -= extra
                new_imgs.append([filename, extra])
                done = True
        else:
            new_imgs.append(filename, num_frames)

    progress.task_done()
    return new_imgs

def cleanup(config, ifile):
    import Element
    ofile = config["workdir"]+"/"+os.path.basename(ifile)+"*_annotate_*.ppm"
    Element.cmd("rm -f "+ofile)
    
