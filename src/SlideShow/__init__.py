import Img
import Reader
import logging, time, sys, os, optparse, subprocess
log = logging.getLogger(__name__)
import gst, gobject

gobject.threads_init()

class Config(dict):
    def __init__(self):
        dict.__init__(self)
        defaults = dict(
            outdir       = os.path.abspath("."),
            audiosmp     = 1,  # default to do audio in background...
            bgfile       = "black",

            gui          = 0,
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

            # annotate
            annotate_pointsize = "8%",
            annotate_font      = "Helvetica-Bold",
            annotate_fill      = "#FFFFFF",
            annotate_stroke    = "#000000",
            annotate_position  = "50%,90%",
            annotate_undercolor= None,
            
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
            nocleanup=0, 
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
        "annotate_pointsize"         ,
        "annotate_font"              ,
        "annotate_fill"              ,
        "annotate_stroke"            ,
        "annotate_position"          ,
        "annotate_undercolor"        ,
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

        self.parser = parser = optparse.OptionParser()
        parser.add_option("--gui", dest="gui", default=None, action="store_true", help="Launch gui and use tool interactively")
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

class Progress(object):
    def hms(self, t):
        s = time.time() - t
        hours = int(s / 3600)
        mins  = int((s - (hours * 3600)) / 60)
        secs  = int((s - (hours * 3600) - (mins * 60)))
        tsec  = int((s - (hours * 3600) - (mins * 60) - secs ) * 10)
        return "%02d:%02d:%02d.%d" % (hours, mins, secs, tsec)

    def overall_start(self, N):
        self.overall_N = N
        self.overall_time = time.time()

    def overall_update(self, i, desc):
        print "*%d/%d %s Elapsed Time %s" % (i,self.overall_N, desc, self.hms(self.overall_time))

    def overall_done(self):
        print "Done: Elapsed Time: %s" % (self.hms(self.overall_time),)

    def task_start(self, N, desc):
        self.task_desc = desc
        self.task_N = N
        self.task_time = time.time()
        self.task_update(0)

    def task_update(self, i):
        M = 25
        m = int(round(M*i/float(self.task_N)))
        sys.stderr.write(("  %15s: |" + "="*m + " "*(M-m) + "| %d/%d (%3.0f%%) %s\r") % (self.task_desc, i, self.task_N, (100.*i/self.task_N), self.hms(self.task_time)))

    def task_done(self):
        sys.stderr.write("   %15s: Elapsed Time: %s                            \n" % (self.task_desc, self.hms(self.task_time)))


def cmd(x):
    log.debug(x)
    p = subprocess.Popen(x, shell=True, stdout=subprocess.PIPE)
    return p.stdout.read()[:-1] # chop off final carriage return

def check_system(config):
    ## Check for required programs
    progver=cmd("mplex 2>&1 | grep version | awk '{ print $4 }'")
    if progver: log.debug("Found mjpegtools version" + progver)
    it=cmd("which ppmtoy4m 2> /dev/null")
    if not(it): # no ppmtoy4m
        raise Exception("ERROR:  no mjpegtools found for audio processing.  You need to download and install mjpegtools. http://mjpegtools.sourceforge.net")
    
    if cmd("ppmtoy4m -S 420mpeg2 xxxxx 2>&1 | grep xxxxx"):
        log.debug("Using mjpegtools subsampling -S 420mpeg2")
        config["subsample"] ='420mpeg2'
    else:
        log.debug("Using mjpegtools subsampling -S 420_mpeg2")
        config["subsample"] ='420_mpeg2'
    	
    #checkforprog sox
    progver=cmd("sox -h 2>&1 | head -n 1 | awk '{ print $3 }'")
    log.debug("Found sox version " + progver)
    it=cmd("which sox 2> /dev/null")
    if not(it): # no sox
        raise Exception("ERROR:  no sox found for audio processing. You need to download and install sox. http://sox.sourceforge.net")
    
    #checkforprog convert
    progver=cmd("convert -help | head -n 1 | awk '{ print $3 }'")
    log.debug("Found ImageMagick version " + progver)
    it=cmd("which convert 2> /dev/null")
    if not(it): # no convert
        raise Exception("ERROR:  no ImageMagick found for audio processing. You need to download and install ImageMagick. http://ImageMagick.sourceforge.net")
    
    #checkforprog dvdauthor
    progver=cmd("dvdauthor -h 2>&1 | head -n 1 | awk '{ print $3 }'")
    log.debug("Found dvdauthor version " + progver)
    it=cmd("which dvdauthor 2> /dev/null")
    if not(it): # no dvdauthor
        raise Exception("ERROR:  no dvdauthor found for audio processing. You need to download and install dvdauthor. http://dvdauthor.sourceforge.net")
    
    # ffmpeg
    it=cmd("which ffmpeg 2> /dev/null")
    if not(it):
        # no ffmpeg!  use mp2 audio instead:
        log.warn("No ffmpeg found for AC3 audio encoding. Using MP2 audio instead. MP2 audio is less compatible with DVD player hardware. http://ffmpeg.sourceforge.net")
        config["ac3"] = 0
        config["mpeg_encoder"] = 'mpeg2enc'
    else:
        # found ffmpeg
        progver = cmd("ffmpeg -version 2>&1").split(",",1)[0]
        log.debug("Found "+ progver)
        ## check to see if we have mpeg2video output option:
        it=cmd("ffmpeg -f mpeg2video 2>&1 | grep 'Unknown input or output format: mpeg2video'")
        if it:
            log.warn("ffmpeg is not compiled with the mpeg2video option required for making dvds!  Using mpeg2enc instead.")
            config["mpeg_encoder"]='mpeg2enc'


def read_pipeline(filename, config):
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

    config["workdir"] = os.path.abspath("./"+config["slideshow_name"] + "_work")
    if not(os.path.exists(config["workdir"])):
        os.mkdir(config["workdir"])
        log.debug("Created work directory " + config["workdir"])
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

def find_prev_slide(element):
    if element.prev:
        if isSlide(element.prev):
            return element.prev
        else:
            return find_prev_slide(element.prev)
    else:
        return None

def find_prev_transition(element):
    """Walks the pipeline backward starting with element until it
    finds a transition or another slide. If it finds a transition, it
    returns the transition element. If it reaches the beginning or a
    slide, it returns None. This is useful for finding a transition
    between two slides (if one exists)."""
    if element.prev:
        if element.prev.isa("Transition"):
            return element.prev
        elif isSlide(element.prev):
            return None
        else:
            return find_next_transition(element.prev)
    else:
        return None

def find_next_transition(element):
    """Walks the pipeline forward starting with element until it
    finds a transition or another slide. If it finds a transition, it
    returns the transition element. If it reaches the end or a
    slide, it returns None. This is useful for finding a transition
    between two slides (if one exists)."""
    if element.next:
        if element.next.isa("Transition"):
            return element.next
        elif isSlide(element.next):
            return None
        else:
            return find_next_transition(element.next)
    else:
        return None

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
                    video_bitrate=1152,
                    audio_sample_rate=44100,
                    mplex_type=1,
                    aspect_ratio="4:3",
                    mpeg2enc_params="-v 0 -4 2 -2 1 -H -b 1150 -n n -s -f $mplex_type",
                    ))
        elif config["svcd"]:
            config.update(dict(
                    ac3=0,  # force mp2
                    audio_bitrate=128,
                    video_bitrate=4500,
                    audio_sample_rate=44100,
                    mplex_type=4,
                    aspect_ratio="4:3",
                    mpeg2enc_params="-v 0 -4 2 -2 1 -H -b 2500 -n n -s -f $mplex_type",
                    ))
        else:
            config.update(dict(
                    audio_bitrate=192,
                    video_bitrate=3800,
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


    framerate_numer = int(round(config["framerate"] * 100))
    framerate_denom = 100
    height = config["dvd_height"]
    width = int(round(config["dvd_height"] * config["aspect_ratio_float"]))
    config["caps"] = gst.Caps("video/x-raw-yuv,width=%d,height=%d,framerate=(fraction)%d/%d" % (width, height, framerate_numer, framerate_denom))

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
    audio_duration = 0
    video_duration = 0
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
            video_duration += element.duration
            video_element_count += 1
        elif element.isa("Audio"):
            audio_duration += element.duration
    
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
            raise
            raise Exception("%s: %s" % (element.location, str(e)))

    print "Audio Duration:", audio_duration
    print "Video Duration:", video_duration
    return dict(audio_duration=audio_duration, video_duration=video_duration, video_element_count=video_element_count)

def get_duration(filename):
    d = gst.parse_launch("filesrc location="+filename+" ! decodebin2 ! fakesink")
    d.set_state(gst.STATE_PAUSED)
    d.get_state() # blocks until state transition has finished
    duration = d.query_duration(gst.Format(gst.FORMAT_TIME))[0]
    d.set_state(gst.STATE_NULL)
    return duration

def get_video_composition(elements):
    comp = gst.element_factory_make("gnlcomposition")

    start_time = 0
    priority = 1
    for element in elements:
        if element.__class__ == Element.Image:
            src = gst.element_factory_make("gnlsource")
            src.add(element.get_bin())

            dur = element.duration
            src.props.start          = start_time
            src.props.duration       = dur
            src.props.media_start    = 0
            src.props.media_duration = dur
            src.props.priority       = priority
            comp.add(src)

            priority   += 1
            start_time += dur

    return comp, dict(duration=start_time)

def get_audio_composition(elements, video_info):
    comp = gst.element_factory_make("gnlcomposition")

    start_time = 0
    priority   = 1
    done = False
    for element in elements:
        if element.__class__ == Element.Audio:
            src = gst.element_factory_make("gnlsource")
            src.add(element.get_bin())

            dur = element.duration
            if(start_time + dur > video_info["duration"]):
                dur = video_info["duration"] - start_time
                done = True
            src.props.start          = start_time
            src.props.duration       = dur
            src.props.media_start    = 0
            src.props.media_duration = dur
            src.props.priority       = priority
            comp.add(src)

            priority   += 1
            start_time += dur
            if done:
                break

    return comp, dict(durtation=start_time)

def get_encoder_backend(config):

#    if config["mpeg_encoder"] == 'ffmpeg':
#        if config["output_format"] == 'flv':
#            ffmpeg_args = "-f flv "+config["workdir"]+"/video.flv"
#        elif config["output_format"] == 'swf':
#            ffmpeg_args = "-f flv "+config["workdir"]+"/video.swf"
#        elif config["output_format"] == 'mp4':
#            ffmpeg_args = "-f mp4 -vcodec mpeg4 "+config["workdir"]+"/video.mp4"
#        elif config["output_format"] == 'mpg':
#            ffmpeg_args = "-f mpeg2video "+config["workdir"]+"/video.mpg"
#        else:  # default mpeg2 video for dvd/vcd
#            ffmpeg_args = "-target "+config["ffmpeg_target"]+" -bf 2 -f mpeg2video "+config["workdir"]+"/video.mpg"
#    
#        encoder_cmd = "ffmpeg -f yuv4mpegpipe -i - -r "+str(config["framerate"])+" -b "+config["video_bitrate"]+" -an -aspect "+config["aspect_ratio"]+" -s "+str(config["dvd_width"])+"x"+str(config["dvd_height"])+" -y %s" % (ffmpeg_args,)
#    
#    else:
#        encoder_cmd = "mpeg2enc "+config["mpeg2enc_params"]+" -o "+config["workdir"]+"/video.mpg -" # < "$workdir"/$yuvfifo >> "$outdir/$logfile" 2>&1 & 
    
    backend = gst.Bin()
    
    #encoder = gst.element_factory_make("ffenc_mpeg4", "encoder")
    video_enc = gst.element_factory_make("x264enc",    "video_enc")
    audio_enc = gst.element_factory_make("lamemp3enc", "audio_enc")
    mux       = gst.element_factory_make("mp4mux", "mux")
    sink      = gst.element_factory_make("filesink", "sink")
    sink.set_property("location", config["outdir"]+"/"+config["slideshow_name"]+".mp4")
    video_enc.props.bitrate = config["video_bitrate"] # * 1000
    print "bitrate=", video_enc.props.bitrate

    backend.add(video_enc, audio_enc, mux, sink)
    video_enc.link(mux)
    audio_enc.link(mux)
    mux.link(sink)
    backend.add_pad(gst.GhostPad("video_sink", video_enc.get_pad("sink")))
    backend.add_pad(gst.GhostPad("audio_sink", audio_enc.get_pad("sink")))
    return backend

def build(elements, config, progress):
    video_comp, video_info = get_video_composition(elements)
    audio_comp, audio_info = get_audio_composition(elements, video_info)

    print "video_info", video_info
    print "audio_info", audio_info

    backend = get_encoder_backend(config)

    pipeline = gst.Pipeline()
    pipeline.add(video_comp, audio_comp, backend)

    def on_pad(comp, pad, backend):
        capspad = backend.get_compatible_pad(pad, pad.get_caps())
        print "caps, ", str(capspad), comp.get_name(), str(pad.get_caps()) 
        print "backcaps", str(backend.get_pad("audio_sink").get_caps())
        pad.link(capspad)
    video_comp.connect("pad-added", on_pad, backend)
    audio_comp.connect("pad-added", on_pad, backend)

    #slide_count = 0
    #for element in pipeline:
    #    if isSlide(element): slide_count += 1
    progress.overall_start(1)

    state = { "running": True }
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.enable_sync_message_emission()
    def on_message(bus, message, state):
        t = message.type
	if t == gst.MESSAGE_EOS:
            print "EOS"
            pipeline.set_state(gst.STATE_NULL)
            state["running"] = False
	elif t == gst.MESSAGE_ERROR:
            pipeline.set_state(gst.STATE_NULL)
            err, debug = message.parse_error()
            state["running"] = False
	    raise Exception("Error: %s %s" % (err, debug))
    bus.connect("message", on_message, state)
    pipeline.set_state(gst.STATE_PLAYING)

    loop = gobject.MainLoop()
    context = loop.get_context()
    while state["running"]:
        context.iteration(True)
        
    progress.overall_done()
    
#    video_duration = total_frames * 1000 / config["framerate"]
#    
#    log.info("Audio duration = %s" % (audio_duration,))
#    log.info("Video duration = %s" % (video_duration,))
#    
#    ############################################################################
#    # AUDIO section...
#    ##########################################################################
#    if(audio_duration < video_duration):
#        silence = Element.Silence("Auto-Inserted", video_duration-audio_duration)
#        silence.initialize(None, None, config)
#        audio_pipeline.append(silence)
#        log.info("Created Silence " + str(silence.duration))
#        audio_duration += silence.duration
#    
#    audio_raw = config["workdir"]+"/audio.raw"
#    audio_wav = config["workdir"]+"/audio.wav"
#    audio_dur = 0
#    reached_end = False
#    cmd("rm -f " + audio_raw)
#    for element in audio_pipeline:
#        if(audio_dur + element.duration > video_duration):
#            log.info("Trimming audio")
#            element.trim(video_duration - audio_dur, config)
#            reached_end = True
#    
#        element.apply_fx(config)
#        audio_dur += element.duration
#        cmd("cat %s >> %s" % (element.filename, audio_raw))
#    
#        if(reached_end):
#            break
#    audio_duration = audio_dur
#    log.info("Audio duration = %s" % (audio_duration,))
#    log.info("Video duration = %s" % (video_duration,))
#    
#    # now raw audio file should match in length
#        
#    cmd("sox -2 -e signed -c 2 -r %s %s %s" % (config["audio_sample_rate"], audio_raw, audio_wav))
#    
#    if config["ac3"] and config["output_format"] == 'mpeg2':
#        log.info("Creating ac3 audio...")
#        cmd("rm -f "+config["workdir"]+"/audio.ac3")
#        cmd("ffmpeg -i "+audio_wav+" -vn -ab "+str(config["audio_bitrate"])+"k -acodec ac3 -vol 100 -ar "+str(config["audio_sample_rate"])+" -ac 6 "+config["workdir"]+"/audio.ac3 >> "+config["ffmpeg_out"]+" 2>&1")
#    else:
#        raise Exception("Not yet supported")
#    
#    ## check to make sure the output files exist before running mplex:
#    if not(os.path.exists(config["workdir"]+"/video.mpg")):
#        raise Exception("ERROR: no output video.mpg file found! This usually happens when ffmpeg screws up something or one image is messed up and the resulting video can't be created")
#    	
#    log.info("Multiplexing audio and video...")
#    
#    ## now multiplex the audio and video:
#    ## -M option is important:  it generates a "single" output file instead of "single-segement" ones
#    ## if you don't use -M, the dvdauthor command will fail!
#    ## total mplex bitrate = 128kBit audio + 1500 kBit video + a little overhead
#    
#    #else  # default mpeg2 video for dvd/vcd
#    if config["ac3"]:
#        cmd("mplex -V "+config["video_buffer"]+" "+config["ignore_seq_end"]+" -f "+str(config["mplex_type"])+" -o "+config["outdir"]+"/"+config["slideshow_name"]+".vob "+config["workdir"]+"/video.mpg "+config["workdir"]+"/audio.ac3 >> "+config["ffmpeg_out"]+" 2>&1")
#    
