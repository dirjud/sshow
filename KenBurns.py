import Element
import logging, math
log = logging.getLogger(__name__)

def parse_window(args, filename, config):
    # pass a string $1 (kenburns start or end arguments)
    
    # xi,yi is the top left corner of the image relative to the frame
    # xw,yh are the width and height of the crop (must be even numbers)
    # x0,y0 is the top left corner of the crop in the image frame.
    # x1,y1 is the bottom right corner of the crop in the image frame.
    # textfile format is:  
    # file:duration:comment:kenburns:xs0,ys0;xs1,ys1;xe0,ye0;xe1,ye1;[startangle,endangle]
    # or
    # file:duration:comment:kenburns:start 0%-100%;start_location;end 0%-100%;end_location;[startangle,endangle]
    # where 0%-100% indicates the fraction of the window width/height, and
    # where start_location and end_location can be:
    # 	topleft			topmiddle|top		topright
    #	middleleft|left		middle			middleright|right
    #	bottomleft		bottommiddle|bottom	bottomright
    # or
    # 	x%,y%
    #	where % is a percentage of the window width/height starting from the
    # 	top left corner of the screen.
    # or
    # 	imagewidth | imageheight
    #	where the window width or height will be scaled to fill the full
    #	width or height of the dvd screen.
    #	
    # ( angles not implemented yet! )
    # and the optional startangle,endangle parameters will allow for rotation of the image during
    # the kenburns effect.  Startangle is optional, and if omitted, will default to zero.
    # Positive numbers denote clockwise rotation, and negative numbers denote counter-clockwise rotation.
    
    image_width, image_height = Element.get_dims(filename)
    image_width = int(round(image_width * config["resize_factor"]))

    ## calculate frame size after adding black side bars for portrait pictures:

    ratio     = 1000 * image_width / image_height
    out_ratio = 1000 * config["frame_width"] / config["frame_height"] # doesn't change during script

    if ratio > out_ratio:
    	# image width greater than output width at same scale
    	new_image_width = image_width
    	new_image_height= int(round(config["frame_height"] * image_width / float(config["frame_width"])))
    	xi=0  # will need to add frame border later...
    	yi= int(round((new_image_height - image_height ) / 2.))
    else: # ratio <= out_ratio
    	# image height greater than output height at same scale 
    	new_image_width= int(round(config["frame_width"] * image_height / float(config["frame_height"])))
    	new_image_height=image_height
    	yi=0 # will need to add frame border later...
    	xi= int(round(( new_image_width - image_width ) / 2. ))

    if args[0].index("%")>-1 or args[0] in ['imagewidth', 'imageheight']:
    	## use "keywords"
    	## first parse the zoom amount:
    	loc=args[1]
    	if args[0] == 'imagewidth':
            # scale width to equal output dvd width:
            xw=image_width
            yh= int(round( config["frame_height"] * xw / float(config["frame_width"])))
    	elif args[0] == 'imageheight':
            # scale height to equal output dvd width:
            yh=image_height
            xw=int(round( config["frame_width"] * yh / float(config["frame_height"])))
    	else:
            ## this needs to be in the non-square pixel frame, hence the
            ## resize_factor
            zoom_percent=eval(args[0][:args[0].index("%")])
            ## need to make the largest dimension smaller, and then scale the
            ## other dimension to the correct aspect ratio!
            if ratio > out_ratio:
                # image width greater than output width at same scale
                # take percentage of width and calculate height:
                xw=int(round(new_image_width * zoom_percent / 100.))
                yh=int(round(config["frame_height"] * xw / float(config["frame_width"])))
            else:
                # image height greater than output height at same scale 
                # take percentage of height and calculate width:
                yh=int(round(new_image_height * zoom_percent / 100.))
                xw=int(round(config["frame_width"] * yh / float(config["frame_height"])))

    	## next line is because we want the zoom % coordinates to be
    	## relative to the whole screen size, so if you have a tall,
    	## narrow picture, 50% will mean half of the height, etc...
    
    	## middle calculations are for using the "middle" keywords:
    	ymiddle0=int(round(new_image_height / 2. - yh / 2.))
    	ymiddle1=int(round(new_image_height / 2. + yh / 2.))
    	xmiddle0=int(round(new_image_width  / 2. - xw / 2.))
    	xmiddle1=int(round(new_image_width  / 2. + xw / 2.))
    
    	## now parse the box location:
        if args[1].index("%") > -1: # second arg contains a %
            # location is specified as a percent of the window size
            try:
                xcenter_pct, ycenter_pct = map(eval, args[1].replace("%","").split(","))
            except:
                raise Exception("Bad xcenter/ycenter percentage")
            xcenter= new_image_width  * xcenter_pct / 100.
            ycenter= new_image_height * ycenter_pct / 100.
            x0= int(round(xcenter - xw / 2.))
            x1= x0 + xw
            y0= int(round(ycenter - yh / 2.))
            y1= y0 + yh
    	elif loc == 'topleft':
            x0=0; x1=xw
            y0=0; y1=yh
    	elif loc in [ 'middleleft', 'left' ]:
            x0=0; x1=xw
            y0=ymiddle0; y1=ymiddle1
    	elif loc == 'bottomleft':
            x0=0; x1=xw
            y0= new_image_height - yh; y1=new_image_height
    	elif loc in [ 'topmiddle', 'top' ]:
            x0=xmiddle0; x1=xmiddle1
            y0=0; y1=yh
    	elif loc in [ 'middle', 'center' ]:
            x0=xmiddle0; x1=xmiddle1
            y0=ymiddle0; y1=ymiddle1
    	elif loc in [ 'bottommiddle', 'bottom' ]:
            x0=xmiddle0; x1=xmiddle1
            y0= new_image_height - yh; y1=new_image_height
    	elif loc == 'topright':
            x0=new_image_width - xw; x1=new_image_width
            y0=0; y1=yh
    	elif loc in [ 'middleright', 'right' ]:
            x0= new_image_width - xw; x1=new_image_width
            y0=ymiddle0; y1=ymiddle1
    	elif loc == 'bottomright':
            x0= new_image_width  - xw; x1=new_image_width
            y0= new_image_height - yh; y1=new_image_height
    	else:
            raise Exception("Bad syntax in kenburns/crop location: %s" % (loc,))

    else:  # check for original format with explicit start/end coordinates:
    	## coordinate system is relative to the actual picture, unscaled, 
    	## in square pixel frame!!!
    	## we need to convert this to the buffered (dvd aspect ratio) 
    	## and non-square pixel coordinate system!!!	
#    myecho "[dvd-slideshow:parse_window] numbered or explicit coorinates"
        try:
            x0,y0=args[0].split(",")
            x1,y1=args[1].split(",")
        except:
            raise Exception("Incorrect coordinates. You probably got the syntax wrong: image.jpg:duration:subtitle:crop:x0,y0;x1,y1 or image.jpg:duration:subtitle:kenburns:xs0,ys0;xs1,ys1;xe0,ye0;xe1,ye1")
    
    	## we also need to convert the x coordinates to the dvd aspect (non-square) pixel coordinates:
    	## fix provided by <add name>
    	x0= x0*config["resize_factor"] / 100
    	x1= x1*config["resize_factor"] / 100
    
    	# xi,yi already calculated.  now, the size of the image frame
    	# should be new_image_width x new_image_height. This mode
    	# assumes the image is placed in the center of the dvd window
    	# to start.
    	
    	# width and height of area passed:
    	xw = x1 - x0
        yh = y1 - y0
    
    	## make sure the image crop coordinates are not outside the image:
        x0 += xi
    	x1 += xi
    	y0 += yi
    	yi += yi

    return x0, y0, x1, y1, xi, yi

def crop_parameters(config, image_width, image_height, x0, y0, x1, y1, xi, yi):
    # converts the crop parameters reference in the full dvd aspect ratio
    # frame back to the actual crop parameters needed in the original 
    # image frame.
    #
    # the input coordinates are relative to the original image size, buffered out to
    # the output dvd aspect ratio
    #	
    # using the parameters x0,y0 ; x1,y1 ; xi,yi in memory (x1000)
    # output is just the crop parameters:
    # c_width, c_height xc0,yc0  (for the actual crop)
    # and for the corresponding composite command:
    # xci,yci for the location of the top left corner of the cropped image
    # relative to the output window.
    #
    # top left corner of dvd window is 0,0
    # top left corner of image is at xi,yi   from parse_window
    # top left corner of the cropped image is at x0,y0
    #
    # i.e., the "i" reference frame is in the unbuffered image (image alone)
    
    ##############################################
    ## figure out the size of the window scaled to the original image size:
    ratio    = 1000 * image_width / image_height
    out_ratio= 1000 * config["frame_width"] / config["frame_height"]
    
    ##############################################
    ## shift coordinate system to start at xi,yi: (all integers)
    ## xi,yi should already include the border
    xi0 = 1000*x0 - 1000*xi; yi0 = 1000*y0- 1000*yi # already x1000
    xi1 = 1000*x1 - 1000*xi; yi1 = 1000*y1- 1000*yi # already x1000
    w= xi1 - xi0 # already x1000
    h= yi1 - yi0 # already x1000
    
    ##############################################
    ## figure out where to crop the image:
    ## (make sure the image crop coordinates are not outside the image)
    xc0 = max(0, xi0)
    xc1 = min(1000 * image_width, xi1)
    yc0 = max(0, yi0)
    yc1 = min(1000 * image_height, yi1)
    c_width = xc1 - xc0; c_height = yc1 - yc0 # already x1000
    crop_ratio= 1000 * c_width / c_height
    
    ##############################################
    ## where to put the top left corner of the cropped image relative to the background?
    deltax= 1000 * 1000 * config["frame_width"] / c_width; deltay= 1000 * 1000 * config["frame_height"] / c_height
    ## rescale % will be the smaller of the two deltas: 
    rescale = min(deltax, deltay) # already x1000

    if xi0 < 0:
    	## left of cropped image is in the middle of the dvd window
    	xci= (-rescale * xi0)/1000
    	if(xci >= 1): xci -= 1
    else:
    	xci=0 ## left of cropped image should be at x=0 afterward

    if yi0 < 0:  ###*  rescale=deltax
    	## top of cropped image is in the middle of the dvd window
    	yci= (-rescale * yi0)/1000.
    	if(yci >= 1): yci -= 1
    else:
    	yci=0 ## top of cropped image should be at y=0 afterward
    
    c_width = (xc1 - xc0)/1000.; c_height = (yc1 - yc0 )/1000.
    
    if crop_ratio > out_ratio:
    	# image width greater than output width at same scale
    	resized_width  = 1000 * config["frame_width"]
    	resized_height = 1000 * c_height * config["frame_width"] / c_width
    elif crop_ratio < out_ratio:
    	# image height greater than output height at same scale 
    	resized_height = 1000 * config["frame_height"]
    	resized_width  = 1000 * c_width * config["frame_height"] / c_height
    else: # crop_ratio = out_ratio.  good.
    	resized_height = 1000 * config["frame_height"]
    	resized_width  = 1000 * config["frame_width"]

    predicted_resized_width = resized_width/1000.
    predicted_resized_height= resized_height/1000.

    xc0_whole = int(xc0); xc0_dec = xc0 - xc0_whole
    yc0_whole = int(yc0); yc0_dec = yc0 - yc0_whole
    xc0 = int(round(xc0 / 1000.)); yc0 = int(round(yc0 / 1000.))
    xci=int(round(xci/1000.)); yci=int(round(yci/1000.)) # rounding might cause problems.  watch this.
    ## make sure xci + predicted_resized_width < dvd_width 
    ## and yci + predicted_resized_height < dvd_height
    if yci + predicted_resized_height > config["frame_height"]:
    	yci = config["frame_height"] - predicted_resized_height
    if xci + predicted_resized_width  > config["frame_width"]:
    	xci = config["frame_width"]  - predicted_resized_width

    # used output is:
    # xc0,yc0 (coordinates of the top left corner of the image crop in the image frame)
    # c_width,c_height (crop width and height in the image frame)
    # xi0,yi0 (coordinates of where to put the top left corner of the image on the background)
    return (xc0, yc0), (c_width, c_height), (xi0, yi0), (xci, yci), (predicted_resized_width, predicted_resized_height)


def kenburns(config, params, ifile, frames):
# Kenburns $window_start $window_end $ifile $total_frames $startframe $lastframe bg [$char]



#    if [ "$bg" == "$transparent_bg" ] ; then
#    	local suffix='png'
#    else
#    	local suffix='ppm'
#    fi
    suffix = "ppm"

    image_width, image_height = Element.get_dims(ifile)
    image_width = int(round(image_width * config["resize_factor"]))

    fields = map(str.strip, params.split(";"))
    (xs0, ys0, xs1, ys1, xi, yi) = parse_window(fields[:2], ifile, config)
    (xe0, ye0, xe1, ye1, xi, yi) = parse_window(fields[2:], ifile, config)

    if xs0 == xe0 and ys0 == ye0 and xs1 == xe1 and ys1 == ye1:
    	# start and end are the same!
    	log.warn("WARNING: Start and end of kenburns effect are the same! Use crop and it will be MUCH faster!")

    
    # now we have the parameters set up.  The coordinate system is
    # relative to the ORIGINAL image size, buffered out to the full
    # DVD frame:
    # xi,yi   xw,yh  xs0,ys0  xs1,ys1  xe0,ye0  xe1,ye1
    
    s_width = xs1 - xs0
    s_height= ys1 - ys0
    e_width = xe1 - xe0
    e_height= ye1 - ye0
    
    ## adjust step size: ##############################
    if config["low_quality"]:
    	stepsize=3
    	interp=0
    	enable_kenburns_resize=0
    	multiple=1
    elif config["high_quality"]:
    	stepsize=1
    	interp=1
    	enable_kenburns_resize=0  # see if this still gives decent quality
    	multiple=3  # 720x480 x 3 = 2160x1440 or 3M pixels
    else:
    	stepsize=1
    	interp=0  # fix this for now?
    	enable_kenburns_resize=0
    	multiple=2  # 720x480 x 2 = 1440x960 or 1.4M pixels
    
    # check original image width and height.  if too large,
    # then make it smaller!
    factorx       = 1000 * image_width / config["dvd_width"]
    factory       = 1000 * image_height / config["dvd_height"]
    maxfactor     = max(factorx, factory)
    minfactor     = min(factorx, factory)
    factorlimit_x = multiple * 1000
    factorlimit_y = multiple * 1000

    if factorx > factorlimit_x and factory > factorlimit_y and enable_kenburns_resize:
    	# only rescale if both the image width and height are more
    	# than n times the output dvd width and height, respectively.
    	if minfactor == factorx:
            newsize= multiple * config["dvd_width"]
            resize='-resize '+str(newsize)+'x'
            resized_x=newsize
            #resized_y= 10 * resized_x * image_height / image_width 
            resized_y= int(round(resized_x * image_height / float(image_width)))
    	else:
            newsize= multiple * config["dvd_height"]
            resize='-resize x'+str(newsize)
            resized_y=newsize
            #resized_x=$(( $resized_y * $image_width / $image_height ))
            resized_x=int(round(resized_y * image_width / float(image_height)))

    	## now, update the coordinates with the new values after the scale. 
    	## we might want to use the actual resized image size instead?
    	xi = 1000 * xi  / minfactor
    	yi = 1000 * yi  / minfactor
    	xs0= 1000 * xs0 / minfactor
    	xe0= 1000 * xe0 / minfactor
    	ys0= 1000 * ys0 / minfactor
    	ye0= 1000 * ye0 / minfactor
    	xs1= 1000 * xs1 / minfactor
    	xe1= 1000 * xe1 / minfactor
    	ys1= 1000 * ys1 / minfactor
    	ye1= 1000 * ye1 / minfactor
    else:
    	resize=''

    convert = ("convert "+ifile+" -filter "+config["filtermethod"]+" -resize "+config["sq_to_dvd_pixels"]+" "+resize +" repage -type TrueColorMatte -depth 8 ").replace("%","%%") + " %s"
    file1 = Element.cmdif(ifile, config["workdir"], "mpc", convert)
    
    ############################ end crop/resize large images
    
    #echo 'x0,y0,x1,y1,xcenter,ycenter,xwidth,yheight,xc0,yc0,c_width,c_height' > kenburns_coordinates.csv
    #echo 'xc0,yc0,c_width,c_height,xci,yci,iwn,ihn,predicted_resized_width,predicted_resized_height,xc0_dec,yc0_dec' > kenburns_coordinates.csv
    #echo 'xc0,yc0,c_width,c_height,xci,yci,predicted_resized_width,predicted_resized_height' > kenburns_coordinates.csv

    xvelocity0 = (xe0-xs0)*(xe0-xs0) / float(frames)
    xvelocity1 = (xe1-xs1)*(xe1-xs1) / float(frames)
    xvelocity  = xvelocity0 + xvelocity1
    yvelocity0 = (ye0-ys0)*(ye0-ys0) / float(frames)
    yvelocity1 = (ye1-ys1)*(ye1-ys1) / float(frames)
    yvelocity  = yvelocity0 + yvelocity1

    if interp and ((xvelocity == 0 and yvelocity < 4000) or (yvelocity == 0 and xvelocity < 4000) or (xvelocity < 5000 and yvelocity < 4000)):
    	log.debug("Using interpolation. Velocity="+str(xvelocity)+" "+str(yvelocity))
    elif interp:
    	log.info("Disabling high-quality mode for fast effect. Velocity="+str(xvelocity)+" "+str(yvelocity))
    	interp=0
    
    ## smooth start and end parameters:
    smoothing=1  # (0=old method before 0.8.0)
    if not(config["kenburns_acceleration"]):
    	# do not use smoothing, or set it to a very small number
    	F1 = 1
    elif (type(config["kenburns_acceleration"]) is str) and (config["kenburns_acceleration"].index("%") > -1):
    	kb_acceleration_percent = eval(config["kenburns_acceleration"][:config["kenburns_acceleration"].index("%")])
    	F1 = frames * kb_acceleration_percent / 100.
    	if F1 == 0:
            F1=1
    else:
    	F1= config["kenburns_acceleration"] * config["framerate"]

    # make sure the acceleration time is shorter than half of the full kenburns time:
    if F1 > frames / 2:
        F1 = frames / 2

    F2  = frames - F1
    V0x = 2 * ( xe0 - xs0 ) / float( frames + F2 - F1 ) 
    V0y = 2 * ( ye0 - ys0 ) / float( frames + F2 - F1 )
    V1x = 2 * ( xe1 - xs1 ) / float( frames + F2 - F1 ) 
    V1y = 2 * ( ye1 - ys1 ) / float( frames + F2 - F1 )

    #subtitle1[$i]="$( echo "${subtitle[$i]}" | awk -F';' '{print $1}' )"
    #if [ -n "${subtitle1[$i]}" -a "$subtitle_type" == 'render' ] ; then
    #	# pre-render the subtitle:
    #	subtitle "${subtitle1[$i]}" $i transparent # creates subtitle_$i.png
    #fi
    pi=3.14159265
    ## start loop for kenburns effect: #################################
    imgs = []
    for fr in range(0, frames, stepsize):
    	dj="%04d"%fr
    	if fr <= F1:  # region 1   x0,y0,x1,y1 are floating point numbers
    	    x0 = xs0 + V0x/2. * (fr - F1/pi * math.sin(pi*fr/F1))
    	    y0 = ys0 + V0y/2. * (fr - F1/pi * math.sin(pi*fr/F1))
    	    x1 = xs1 + V1x/2. * (fr - F1/pi * math.sin(pi*fr/F1))
    	    y1 = ys1 + V1y/2. * (fr - F1/pi * math.sin(pi*fr/F1))
    	    D1x0 = x0; D1y0 = y0; D1x1 = x1; D1y1 = y1 # distance gone so far
    	    D2x0 = x0; D2y0 = y0; D2x1 = x1; D2y1 = y1  # (in case we never get to region2)

    	elif fr >= F2 + 1: # region 3
            x0 = D2x0 + V0x/2. * ((fr - F2) + (frames - F2)/pi * math.sin((fr-F2)*pi/(frames-F2)))
    	    y0 = D2y0 + V0y/2. * ((fr - F2) + (frames - F2)/pi * math.sin((fr-F2)*pi/(frames-F2)))
    	    x1 = D2x1 + V1x/2. * ((fr - F2) + (frames - F2)/pi * math.sin((fr-F2)*pi/(frames-F2)))
    	    y1 = D2y1 + V1y/2. * ((fr - F2) + (frames - F2)/pi * math.sin((fr-F2)*pi/(frames-F2)))

    	else: # middle region 2
    	    x0 = D1x0 + V0x * (fr-F1)
    	    y0 = D1y0 + V0y * (fr-F1)
    	    x1 = D1x1 + V1x * (fr-F1)
    	    y1 = D1y1 + V1y * (fr-F1)
    	    D2x0=x0 ; D2y0=y0 ; D2x1=x1 ; D2y1=y1  # distance gone so far

        x0_whole = int(x0); x0_dec = x0-x0_whole; x0 = int(round(x0))
        y0_whole = int(y0); y0_dec = y0-y0_whole; y0 = int(round(y0))
        x1_whole = int(x1); x1_dec = x1-x1_whole; x1 = int(round(x1))
        y1_whole = int(y1); y1_dec = y1-y1_whole; y1 = int(round(y1))
    
    	## now optionally do convolution if high-quality is enabled:
    	if interp:
    	    ## now, we're going to calculate the following parameters:
    	    # calculate subpixel-averaging weights:
            Afactor = 100*(1-x0_dec)*(1-y0_dec)
            Bfactor = 100*(  x0_dec)*(1-y0_dec)
            Cfactor = 100*(1-x0_dec)*(  y0_dec)
            Dfactor = 100*(  x0_dec)*(  y0_dec)
    	    convolve="-convolve 0,0,0,0,%f,%f,0,%f,%f" % (Afactor,Bfactor,Cfactor,Dfactor)
            log.debug(convolve)
    	else:
            convolve="-filter "+config["filtermethod"]
    
    	# [c_width c_height xc0 yc0 xci yci]=crop_parameters(image_width image_height frame_width frame_height x0 y0 x1 y1 xi yi)
        (xc0, yc0), (c_width, c_height), (xi0, yi0), (xci, yci), (predicted_resized_width, predicted_resized_height) = crop_parameters(config, image_width, image_height, x0, y0, x1, y1, xi, yi) # figure out final crop parameters
    	# outputs correct predicted_resized_width and predicted_resized_height
    
    	delta_width = config["dvd_width"]  - predicted_resized_width
    	delta_height= config["dvd_height"] - predicted_resized_height
    	if delta_width <= 1 and delta_height <= 1 and config["frame_border"] == 0:
            convert = "convert "+file1+" -filter "+config["filtermethod"]+" -crop "+str(c_width)+"x"+str(c_height)+"+"+str(xc0)+"+"+str(yc0)+" +repage -type TrueColorMatte -depth 8 "+convolve+" -resize "+str(config["dvd_width"])+"x"+str(config["dvd_height"])+"! "+config["sharpen"]+" -type TrueColorMatte -depth 8 ".replace("%","%%")+" %s"
            file2 = Element.cmdif(file1, config["workdir"], suffix, convert)
            #extracopies $fr $frames $suffix

            # force the output size to be exact:  no composite needed!
    	    #if [ -n "${subtitle1[$i]}" -a "$subtitle_type" == 'render' ] ; then
    	    #	if [ "$smp" -eq 1 ] ; then
    	    #		[ $debug -ge 3 ] && echo "deltawh<1 smp=1"
    	    #		(convert "$tmpdir"/temp_slideshow_image_scaled.mpc -filter $filtermethod -crop "$c_width"x"$c_height"+"$xc0"+"$yc0" +repage -type TrueColorMatte -depth 8 $convolve -resize "$dvd_width"x"$dvd_height"! $sharpen miff:- | composite -compose src-over -type TrueColorMatte -depth 8 "$tmpdir"/subtitle_"$i".png - "$tmpdir"/fade_"$dj.$suffix"  ; extracopies $fr $frames $suffix ) &
    	    #	elif [ "$smp" -eq 0 ] ; then
    	    #		[ $debug -ge 3 ] && echo "deltawh<1 smp=0"
    	    #		(convert "$tmpdir"/temp_slideshow_image_scaled.mpc -filter $filtermethod -crop "$c_width"x"$c_height"+"$xc0"+"$yc0" +repage -type TrueColorMatte -depth 8 $convolve -resize "$dvd_width"x"$dvd_height"! $sharpen miff:- | composite -compose src-over -type TrueColorMatte -depth 8 "$tmpdir"/subtitle_"$i".png - "$tmpdir"/fade_"$dj.$suffix"  ; extracopies $fr $frames $suffix ) 
    	    #	fi
    	    #else
    	    #	if [ "$smp" -eq 1 ] ; then
    	    #		[ $debug -ge 3 ] && echo "deltawh<1 smp=1"
    	    #		(convert "$tmpdir"/temp_slideshow_image_scaled.mpc -filter $filtermethod -crop "$c_width"x"$c_height"+"$xc0"+"$yc0" +repage -type TrueColorMatte -depth 8 $convolve -resize "$dvd_width"x"$dvd_height"! $sharpen -type TrueColorMatte -depth 8 "$tmpdir"/fade_"$dj.$suffix"  ; extracopies $fr $frames $suffix ) &
    	    #	elif [ "$smp" -eq 0 ] ; then
    	    #		[ $debug -ge 3 ] && echo "deltawh<1 smp=0"
    	    #		convert "$tmpdir"/temp_slideshow_image_scaled.mpc -filter $filtermethod -crop "$c_width"x"$c_height"+"$xc0"+"$yc0" +repage -type TrueColorMatte -depth 8 $convolve -resize "$dvd_width"x"$dvd_height"! $sharpen -type TrueColorMatte -depth 8 "$tmpdir/fade_$dj.$suffix"  ; extracopies $fr $frames $suffix
    	    #	fi
    	    #fi
        else:
    	    # calculate border size for possible speed improvement:
    	    # splice in black background if we can for better speed!
    	    # split the difference between the two sides. If odd, add extra
    	    # to bottom right?
    	    left  = xci + config["frame_border"]
            right = delta_width - left
    	    if right < 0: 
                left = left + right
                right = 0
    	    top    = yci + config["frame_border"]
            bottom = delta_height - top
    	    if bottom < 0: 
                top    = top + bottom
                bottom = 0

            convert = ("convert "+file1+" -filter "+config["filtermethod"]+" -crop "+str(c_width)+"x"+str(c_height)+"+"+str(xc0)+"+"+str(yc0)+" +repage -type TrueColorMatte -depth 8 $convolve -resize "+str(config["frame_width"])+"x"+str(config["frame_height"]) + " ").replace("%","%%") + "%s"
            file1a = Element.cmdif(file1, config["workdir"], suffix, convert)

    	    # now, get size of resized image because of roundoff errors:
    	    # need to get this correct in the future so we can run this in smp mode!
    	    resized_width, resized_height = Element.get_dims(file1a)
    	    delta_width   = config["dvd_width"]  - resized_width
    	    delta_height  = config["dvd_height"] - resized_height
    	    left  = xci + config["frame_border"]
            right = delta_width - left
    	    top   = yci + config["frame_border"]
            bottom= delta_height - top
            if right < 0:
                left = left + right
                right=0
            if bottom < 0:
                top    = top + bottom
                bottom = 0

            convert = "convert "+file1a+" -background black -splice "+str(right)+"x"+str(bottom)+"+"+str(resized_width)+"+"+str(resized_height)+" -splice "+str(left)+"x"+str(top)+" +repage "+config["sharpen"]+" -type TrueColorMatte -depth 8 %s"
            file2 = Element.cmdif(file1a, config["workdir"], suffix, convert)

            
            # works with imagemagick > 6.0.6  (convert "$tmpdir/temp_slideshow_image_scaled.mpc" -crop "$c_width"x"$c_height"+$xc0+$yc0 +repage -resize "$dvd_width"x"$dvd_height" -bordercolor black -compose src-over -border 0 -background black -splice "$right"x"$bottom"+$i_width+$i_height -splice "$left"x"$top" -type TrueColorMatte -depth 8 "$tmpdir/fade_$dj.ppm" ; extracopies $fr $frames )

        imgs.append((file2, stepsize))

        ## this next line only works for non-smp! (since file must exist first)
    	## errors here (not depth=8) will often cause ppmtoy4m errors
    	## like "Bad Raw PPM magic!"
    	#if [ "$debug" -ge 2 ] && [ "$smp" -eq 0 ] ; then
    	#	# do error checks on output kenburns image
    	#	outwidth=`imagewidth_sq "$tmpdir/fade_$dj.$suffix"`
    	#	outheight=`imageheight "$tmpdir/fade_$dj.$suffix"`
    	#	if [ "$outwidth" -ne "$dvd_width" ] ; then
    	#		myecho "ERROR: fade_$dj.$suffix is not $dvd_width wide"
    	#		exit 1
    	#	fi
    	#	if [ "$outheight" -ne "$dvd_height" ] ; then
    	#		myecho "ERROR: fade_$dj.$suffix is not $dvd_height high"
    	#		exit 1
    	#	fi
    	#fi
    	#progressbar $(( $fr - $startframe +1 )) $(( $endframe - $startframe + 1 )) "$c"
    return imgs
