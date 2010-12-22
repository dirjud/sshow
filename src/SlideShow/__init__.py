import Reader
import logging
log = logging.getLogger(__name__)

class Config(dict):
    def __init__(self):
        import os
        dict.__init__(self)
        defaults = dict(
            outdir       = os.path.abspath("."),
            audiosmp     = 1,  # default to do audio in background...
            bgfile       = "black",

            debug        = 0, # 0-2
            pal          = 0,  
            copy         = 0,
            low_quality  = 0,
            high_quality = 0,
            autocrop     = 0,
            ac3          = 1,
            widescreen   = 0,
            border       = 0,  
            sharpen      = '',
            subtitle_type="dvd",	# or, use empty for default.
            font_dirs    = [ "/usr/share/fonts/","/usr/X11R6/lib/X11/fonts/","/usr/local/share/fonts/"],
            default_fonts= ['n019004l.pfb', # helvetica bold URW fonts
                            'helb____.ttf', # helvetica bold truetype
                            ],
            ## Subtitle
            subtitle_font_size=24,
            subtitle_color="white",
            subtitle_outline_color="black",
            subtitle_location="bottom", # or "top"
            subtitle_location_x=0,
            subtitle_location_y=105,
            
            ## Title
            title_font_size=48,
            title_font_color='black',  # or use hex "#RRGGBB"
            
            ## top title
            toptitle_font_size=48,
            toptitle_font_color='black', # or use hex "#RRGGBB"
            toptitle_bar_height=125,  # 0 for no 50% white behind text
            toptitle_text_location_x=80,
            toptitle_text_location_y=50,
            
            # bottom title: 
            bottomtitle_font_size=36,
            bottomtitle_font_color="black",  # or use hex "#RRGGBB"
            bottomtitle_bar_location_y=156, # relative to bottom of image
            bottomtitle_bar_height=55,  # 0 for no 50% white behind text
            bottomtitle_text_location_x=0,
            bottomtitle_text_location_y=155,

            theme='default',
            themedir='/opt/sshow/themes',  # LSB/FHS compliant.  see: http://www.pathname.com/fhs/pub/fhs-2.3.html#OPTADDONAPPLICATIONSOFTWAREPACKAGES
            local_themedir="~/.sshow/themes",  # local theme directory
            
            ## not user configurable
            verbosity=0,  # for mpeg2enc and such
            slideshow_name="",
            titletext="",
            i_audio=0,
            j_audio=0,
            write_chap=0,
            subtitle_number=0,
            n=0,
            m=0,
            browse_num=0,
            submenu=0,
            write_chaps=0,
            chapmenu=0,
            browsable=0,
            yuvfirstfile=1,              # tells when to strip yuv headers
            write_last_subtitle=0,
            write_last_subtitle2=0,
            commandline_audiofiles=0,
            nocleanup=1, 
            function_error=0,
            vcd=0,
            svcd=0,
            first_title=1,
            first_image=1,
            filtermethod="Lanczos",

            #image_postprocess='shadow'
            image_postprocess='none',
            mpeg_encoder='ffmpeg', # or mpeg2enc.  I find ffmpeg 2x faster than mpeg2enc
            #mpeg_encoder='mpeg2enc' # or mpeg2enc.  I find ffmpeg 2x faster than mpeg2enc
            output_format='mpeg2', # or flv, mpg, mp4, mp4_ipod.  mpeg2 is default
            #output_format='flv' # or flv, mpg, mp4, mp4_ipod
            ignore_seq_end='-M',

            smp = 0,
            kenburns_acceleration=2,  # in seconds
            )
        self.update(defaults)

    vars = [
        "debug"             ,
        "pal"               ,
        "ac3"               ,
        "copy"              ,
        "autocrop"          ,
        "high_quality"      ,
        "title_font"        ,
        "subtitle_type"     ,
        "theme"             ,
        "theme_designed_for",
        "high_quality"      ,
        "widescreen"        ,
        "debug"                      ,
        "title_font_size"            ,
        "title_font_color"           ,
        "toptitle_font_size"         ,
        "toptitle_font_color"        ,
        "toptitle_bar_height"        ,
        "toptitle_text_location_x"   ,
        "toptitle_text_location_y"   ,
        "bottomtitle_font_size"      ,
        "bottomtitle_font_color"     ,
        "bottomtitle_bar_location_y" ,
        "bottomtitle_bar_height"     ,
        "bottomtitle_text_location_x",
        "bottomtitle_text_location_y",
        "border"                     ,
        "slideshow_image_filter"     ,
        "sharpen"                    ,
        "kenburns_acceleration"      ,
        "subtitle_font"              ,
        "subtitle_font_size"         ,
        "subtitle_color"             ,
        "subtitle_outline_color"     ,
        "subtitle_location"          ,
        "subtitle_location_x"        ,
        "subtitle_location_y"        ,
        "logo"                       ,
        ]

    def is_var(self, key):
        return key in Config.vars

    def set_var(self, key, val):
        self[key] = val

    def parse_argv(self):
        """Updates this config with variables passed on the command line"""

        import sys, optparse, os
        self.parser = parser = optparse.OptionParser()
        parser.add_option("-o", "--outdir",    dest="outdir", default=None, help="Directory where work directory, the final .vob, and dvdauthor .xml files will be written.  Default is to write in the directory where sshow was run.")
        parser.add_option("--themes",          dest="print_themes", action="store_true", default=False, help="print available themes")
        
        parser.add_option("-p", "--pal",       dest="pal",      action="store_true", default=None, help="Use PAL output video format instead of NTSC")
        parser.add_option("-r", "--autocrop",  dest="autocrop", action="store_true", default=None, help="Autocrop horizontal images to fill the full size of the screen.")
        parser.add_option("-C", "--copy",      dest="copy",     action="store_true", default=None, help="make backup copy of all pictures passed.")
        parser.add_option("--mp2",             dest="ac3",      action="store_false", help="Use MP2 audio instead of AC3. Default audio format is now AC3 because it seems to be more compatible with the DVD hardware players.")
        parser.add_option("--ac3",             dest="ac3",      action="store_true", help="use ac3 audio", default=None)
        parser.add_option("-V", "--debug",     dest="debug",    default=None, type="int", help="debug level 0-2")
        parser.add_option("--theme",           dest="theme",    default=None, help="Use the given theme when setting variables/colors/etc. Themes are installed in /opt/sshow/themes or in a local directory ~/.sshow/themes")
        parser.add_option("-H", "--high-quality", dest="high_quality", action="store_true", default=None, help ="(Beta) Render a higher-quality video. This uses the default dvd resolution and keeps all other output parameters the same, but enables some pixel-sampling methods that make the scroll effect look better at very slow velocities. This will make sshow take up to 4x longer to process the scroll effect. Only applied when needed; the output will explain.")
        parser.add_option("-L", "--low-quality", dest="low_quality", action="store_true", default=None, help ="Render a low-quality video suitable for debugging. This sets the resolution to 1/2 of full resolution and decreases the quality of fades/transitions.")
        parser.add_option("-s", "--output-size",  dest="output_size", default=None, help="output size (over-rides defaults).  use something like 320x204. Specify output< size other than default with -s 320x240 (alpha)")
        parser.add_option("-F", "--fps",          dest="output_framerate", default=None, help="output framerate (over-rides defaults). use 15 or 10 or 20 (integers only now)  # DO NOT USE")
        parser.add_option("--border",          dest="border", type="int", default=None, help="Make a border of N pixels around each image.")
        parser.add_option("--sharpen",         dest="sharpen", default=None, action="store_true", help="Sharpen image")
        parser.add_option("--logo",            dest="logo", default=None, help="option to add a logo to each slide. (does not work with transitions yet)")
        
        parser.add_option("-b",       dest="bgfile", help="Image to use for the background of the slideshow. All of the pictures will be overlaid on top of this background image. If no file is specified, black will be used for the slideshow and a blue gradient for the title slide.");
        parser.add_option("-n",       dest="slideshow_name", default="", help="The program uses this string as the filename base for the output files so you can distinguish it from other slideshows that you can send to the same output directory.")
        parser.add_option("-t",       dest="time_per_picture=", help="in tenths or hundredths of seconds?")
        parser.add_option("--writechaps", dest="write_chaps", action="store_true", default=False, help="Write out chapter times to $slideshow_name.chap")
        parser.add_option("-f", dest="input_txtfile", default=None, help="input_file.txt (-f is optional if the file is the last argument).  File to specify all the parameters and order easily for bigger slideshows.")
        parser.add_option("--nocleanup", dest="nocleanup", action="store_true", default=None, help="Leave temporary files in the temporary directory.  Useful for debugging.")
        parser.add_option("--smp", dest="smp", action="store_true", default=None, help="Enable more processes to run at the same time for multiprocessor machines.  Basically, this just renders each frame of a transition in the background at the same time, and then waits for them to be finished. Use this at your own risk on slower machines! If you do not have enough memory to hold all the frames for one 'crossfade' or 'kenburns' effect, then linux starts swapping to disk, and your machine may seem to lock up for a while.  USE THIS AT YOUR OWN RISK!")
        parser.add_option("-w", "--widescreen", dest="widescreen", action="store_true", default=None, help="Alpha! Render widescreen output (16:9) instead of standard (4:3). Please send bug reports to scott at dylewski dot com")
        parser.add_option("-a", dest="audio", help="No longer supported")
        
        # Options: 
        #  [-a <audio file>]
        #           Audio file to play in background during the slideshow.
        #           It will be faded out at the end.  Supports mp3, ogg, 
        # 	  aac, mp4, or wav formats at this point.
        # 	  Multiple files will be joined.
        # 	  See also the more flexible text file input method.
        # 	  To pass multiple files, use the -a switch again.
        
        (options, args) = parser.parse_args()
        
        #if(options.print_themes):
        #	echo("Printing theme list...")
        #	print_themes(config["themedir"])
        #	print_themes(config["local_themedir"])
        #        sys.exit()
        
        # merge command line options into the config
        cli_opts = self["cli_options"] = {}
        for k,v in options.__dict__.items():
            if not(v is None):
                self.set_var(k, v)
                cli_opts[k] = v

        if not(options.input_txtfile) and args:
            self["input_txtfile"] = args[0]
            cli_opts[k] = v

        if self.has_key("input_txtfile") and not(os.path.exists(self["input_txtfile"])):
            raise Exception("Input file "+ self["input_txtfile"] + " does not exist.")

def cmd(x):
    log.debug(x)
    p = subprocess.Popen(x, shell=True, stdout=subprocess.PIPE)
    return p.stdout.read()[:-1] # chop off final carriage return

def read_pipeline(filename, config):
    import os
    if not(os.path.exists(filename)):
        raise Exception(filename + " file cannot be opened.")

    filename = os.path.abspath(filename)
    config["input_txtfile"] = filename

    # change to directory of the input file
    os.chdir(os.path.dirname(os.path.abspath(filename)))
    

    # set the slideshow name in the config to default as the basename
    # of input file
    fname = os.path.basename(filename)
    config["slideshow_name"] = ".".join(fname.split(".")[:-1])#remove file suffix
    log.debug("Setting default slideshow name: " + config["slideshow_name"])

    if(config["debug"] >= 1):
        config["ffmpeg_out"] = config["outdir"]+"/"+config["logfile"]
    else:
        config["ffmpeg_out"] = '/dev/null'

    config["workdir"] = config["outdir"]+"/"+config["slideshow_name"] + "_work"
    if not(os.path.exists(config["workdir"])):
        os.mkdir(config["workdir"])
    return Reader.DVDSlideshow(filename).get_pipeline(config)

##############################################
#  Set default fonts
def find_font(font_name, font_dirs):
    for font_dir in font_dirs:
	font_path = cmd("find -L "+font_dir+" -name "+font_name+" | head -n 1")
        if font_path:
            return font_path
    raise Exception("Font not found")
        

def set_font(config, name):
    import os
    if(config.has_key(name)): # title font passed
        if not(os.path.exists(config[name])):
            try:
                config[name] = find_font(config[name], config["font_dirs"])
                print name, " found font"
            except:
                raise Exception("Cannot find %s font named %s in %s." % (name, config[name], config["font_dirs"]))
    else:
        config[name] = config["default_font"]
    log.debug(name + " is "+config["title_font"])

################################################################################
def isSlide(element):
    return element.isa("Image") and element.duration > 0

def nextSlide(pos, pipeline):
    for element in pipeline[pos+1:]:
        if isSlide(element):
            return element
    raise Exception("No next slide")

def prevSlide(pos, pipeline):
    reverse_pipe = pipeline[:pos]
    reverse_pipe.reverse()
    for element in reverse_pipe:
        if isSlide(element):
            return element
    raise Exception("No prev slide")

def isNextTransition(pos, pipeline):
    for element in pipeline[pos+1:]:
        if isSlide(element):
            return False
        elif element.isa("Transition"):
            return True
    return False

def initialize_pipeline(pipeline, config):
    config["default_font"] = "Helvetica-Bold" # start with ImageMagick font and then see if other fonts are available.
    for font_name in config["default_fonts"]:
        try:
            config["default_font"] = find_font(font_name, config["font_dirs"])
            break
        except:
            pass
    log.debug("default_font is " + config["default_font"])
    set_font(config, "title_font")
    set_font(config, "subtitle_font")

## setup video parameters:
    if config["output_format"] == 'flv':
        config.update(dict(
            video_bitrate=100,  # this works ok for 320x240. 
            ## video_bitrate will be scaled if user specifies -s 240x180, for example, by about 1/2
            video_suffix='flv',
            framerate=15.0,  # is this needed for .flv?
            #	sq_pixel_multiplier=$(( 1000 ))  # keep pixels square?
            ppmtoy4m_frc='15:1',  # 15 fps
            ppmtoy4m_aspect='1:1',  # square pixels
            # see http://www.uwasa.fi/~f76998/video/conversion
            dvd_width=320, 
            dvd_height=240,
            aspect_ratio="4:3",
            audio_sample_rate=44100,
            audio_bitrate=128,
            ))
    elif config["output_format"] == 'swf':
        config.update(dict(
                video_bitrate=100,
                video_suffix='swf',
                framerate=15.0,  # is this needed for .swf?
                #	sq_pixel_multiplier=$(( 1000 ))  # keep pixels square?
                ppmtoy4m_frc='15:1',  # 15 fps
                ppmtoy4m_aspect='1:1',  # square pixels
		# see http://www.uwasa.fi/~f76998/video/conversion
                dvd_width=320,
                dvd_height=240,  # default
                aspect_ratio="4:3",
                audio_sample_rate=44100,
                audio_bitrate=128,
                ))
    elif config["output_format"] == 'mp4':
        config.update(dict(
                video_bitrate=1000,
                video_suffix='mp4',
                framerate=29.97,
                #	sq_pixel_multiplier=$(( 1000 ))  # keep pixels square?
                ppmtoy4m_frc='30000:1001',
                ppmtoy4m_aspect='10:11',  # 4:3
		# see http://www.uwasa.fi/~f76998/video/conversion
                dvd_width=320,
                dvd_height=240,  # default
                aspect_ratio="4:3",
                audio_sample_rate=44100,
                audio_bitrate=128,
                ))
    else:  # assume mpeg2 video output (dvd, vcd, svcd or other)
        config["video_suffix"]='mpg'
        if config["pal"]:
            config["framerate"]=25.0
            config["ppmtoy4m_frc"]='25:1'
            config["ppmtoy4m_aspect"]='59:54'
            # see http://www.uwasa.fi/~f76998/video/conversion
            if config["vcd"]:
                config.update(dict(dvd_width=352, dvd_height=288, ffmpeg_target='pal-vcd'))
            elif config["svcd"]:
                config.update(dict(dvd_width=480, dvd_height=576, ffmpeg_target='pal-svcd'))
            elif config["high_quality"]:
                config.update(dict(dvd_width=720, dvd_height=576, ffmpeg_target='pal-dvd'))
            elif config["low_quality"]:
                config.update(dict(dvd_width=352, dvd_height=288, ffmpeg_target='pal-dvd'))
            else:
                config.update(dict(dvd_width=720, dvd_height=576, ffmpeg_target='pal-dvd'))

        else:  ## NTSC
            config["framerate"]=29.97
            config["ppmtoy4m_frc"]='30000:1001'
            config["ppmtoy4m_aspect"]='10:11'
            # see http://www.uwasa.fi/~f76998/video/conversion
            if config["vcd"]:
                config.update(dict(dvd_width=352, dvd_height=240, ffmpeg_target='ntsc-vcd'))
            elif config[ "svcd"]:
                config.update(dict(dvd_width=480, dvd_height=480, ffmpeg_target='ntsc-svcd'))
            elif config["high_quality"]:
                config.update(dict(dvd_width=720, dvd_height=480, ffmpeg_target='ntsc-dvd'))
            elif config["low_quality"]:
                config.update(dict(dvd_width=352, dvd_height=240, ffmpeg_target='ntsc-dvd'))
            else:
                config.update(dict(dvd_width=720, dvd_height=480, ffmpeg_target='ntsc-dvd'))

        config["mplex_bitrate"]=9500
        if config["vcd"]:
            config.update(dict(
                    ac3=0,  # force mp2
                    audio_bitrate=224,
                    video_bitrate='1152',
                    audio_sample_rate=44100,
                    mplex_type=1,
                    aspect_ratio="4:3",
                    mpeg2enc_params="-v 0 -4 2 -2 1 -H -b 1150 -n n -s -f $mplex_type",
                    ))
        elif config["svcd"]:
            config.update(dict(
                    ac3=0,  # force mp2
                    audio_bitrate=128,
                    video_bitrate='4500',
                    audio_sample_rate=44100,
                    mplex_type=4,
                    aspect_ratio="4:3",
                    mpeg2enc_params="-v 0 -4 2 -2 1 -H -b 2500 -n n -s -f $mplex_type",
                    ))
        else:
            config.update(dict(
                    audio_bitrate=192,
                    video_bitrate='3800',
                    audio_sample_rate=48000 ,
                    mplex_type=8,
                    ))
            if config["widescreen"]:
                config.update(dict(
                        aspect_ratio="16:9",
                        mpeg2enc_params="-v 0 -a 3 -q 4 -4 2 -2 1 -s -M 0 -f $mplex_type",
                        ))
            else:
                config.update(dict(
                        aspect_ratio="4:3",
                        mpeg2enc_params="-v 0 -a 2 -q 4 -4 2 -2 1 -s -M 0 -f $mplex_type -E -N -R 2",
                        ))
    config["video_buffer"] = '-b 1000'
    if config[ "output_format"] == 'mpg':  # assume computer output:
        config.update(dict(
                #sq_pixel_multiplier=$(( 1000 ))  # keep pixels square?
		ppmtoy4m_aspect='1:1',  # square pixels
	        ac3=0,  # force mp2 ?
	        audio_bitrate=192,
		video_bitrate=600 * config["dvd_width"] / 480,
	        audio_sample_rate=48000,
		mplex_type=3,
		aspect_ratio="1:1",
		mpeg2enc_params="-v 0 -4 2 -2 1 -H -b $video_bitrate -n n -s -f $mplex_type",
                ))
        
    aspect_ratio = map(float, config["aspect_ratio"].split(":"))
    config["aspect_ratio_float"] = aspect_ratio[0]/aspect_ratio[1]
    config["resize_factor"] = config["dvd_width"]/config["aspect_ratio_float"]/config["dvd_height"]

    config["sq_to_dvd_pixels"]=str(config["resize_factor"]*100)+"x100%"

    if config.has_key("output_size"):
	# used user-set size, instead of defaults!
	config.update(dict(
                orig_dvd_width=config["dvd_width"],
                orig_dvd_height=config["dvd_height"],
                ))
	config["dvd_width"], config["dvd_height"] = config["output_size"].split("x")
	if config["output_format"] in ['flv', 'swf' ]:
            config["video_bitrate"] = config["video_bitrate"] * config["dvd_width"] * config["dvd_height"] / config["orig_dvd_width"] / config["orig_dvd_height"]

    if config.has_key("output_framerate"):
        config["framerate"]=float(config["output_framerate"])
        config["ppmtoy4m_frc"]= str(config["framerate"])+":1"  # fps  need to fix this to allow any option!

    config["frame_border"] = config["border"]
    config["frame_width"]= config["dvd_width"] - 2 * config["frame_border"]
    config["frame_height"]= config["dvd_height"] - 2 * config["frame_border"]

    if config["sharpen"]:
        config["sharpen"]='-unsharp 4.8x2.2+0.5+0.05'
    else:
        config["sharpen"]=''

    audio_index = {}
    audio_length = 0
    video_length = 0
    prev_element = None
    video_element_count  = 0
    for pos, element in enumerate(pipeline):
        if element.isa("Audio"):
            try:
                audio_index[element.track] += 1
            except KeyError:
                audio_index[element.track] = 0
            element.index = audio_index[element.track]
            
        try:
            next_element = pipeline[pos+1]
        except:
            next_element = None
        try:
            element.initialize(prev_element, next_element, config)
        except Exception, e:
            raise
            raise Exception("%s: %s" % (element.location, str(e)))
    
        prev_element = element
    
        if isSlide(element):
            video_length += element.duration
            video_element_count += 1
        elif element.isa("Audio"):
            audio_length += element.duration
    
        try:
            if element.isa("Transition") and element.name == 'fadein':
                try:
                    nextSlide(pos, pipeline)
                except:
                    raise Exception("no next slide found to fadein to!")
                if isNextTransition(pos, pipeline):
                    raise Exception("Cannot fadein to another transition!")
            elif element.isa("Transition") and element.name in [ 'crossfade', 'wipe' ]:
                try:
                    next_slide = nextSlide(pos, pipeline)
                except:
                    raise Exception("No next slide to "+element.name+" to!")
                try:
                    prev_slide = prevSlide(pos, pipeline)
                except:
                    raise Exception("No previous slide to "+element.name+" to!")
                if isNextTransition(pos, pipeline):
                    raise Exception("Cannot "+element.name+" to another transition!")
            elif element.isa("Transition") and element.name == 'fadeout':
                try:
                    prevSlide(pos, pipeline)
                except:
                    raise Exception("no prevision slide to fadeout from!")
                if isNextTransition(pos, pipeline):
                    raise Exception("Cannot fadeout to another transition")
    
        except Exception, e:
            raise Exception("%s: %s" % (element.location, str(e)))

    return dict(audio_length=audio_length, video_length=video_length, video_element_count=video_element_count)
