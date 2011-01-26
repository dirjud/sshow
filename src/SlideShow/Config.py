import optparse, logging, os, gst

log = logging.getLogger(__name__)

class Config(dict):
    def __init__(self):
        dict.__init__(self)
        self.unique = {}
        defaults = dict(
            outdir       = os.path.abspath("."),
            audiosmp     = 1,  # default to do audio in background...
            bgfile       = "black",

            transition   = None,
            debug        = 0, # 0-2
            pal          = 0,  
            copy         = 0,
            low_quality  = 0,
            high_quality = 0,
            autocrop     = 0,
            ac3          = 1,
            widescreen   = 0,
            border       = 0,  
            width        = 640,
            height       = 480,
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
            
            ## Title
            title_font_size=48,
            title_font_color='white',  # or use hex "#RRGGBB"
            
            ## top title
            toptitle_font_size=48,
            toptitle_font_color='black', # or use hex "#RRGGBB"
            toptitle_bar_height=125,  # 0 for no 50% white behind text
            toptitle_text_location_x=0.15,
            toptitle_text_location_y=0.25,
            toptitle_text_justification="left",
            
            # bottom title: 
            bottomtitle_font_size=36,
            bottomtitle_font_color="black",  # or use hex "#RRGGBB"
            bottomtitle_bar_height=55,  # 0 for no 50% white behind text
            bottomtitle_text_location_x=0.5,
            bottomtitle_text_location_y=0.65,
            bottomtitle_text_justification="center",

            # annotate
            annotate_size = "8%",
            annotate_font      = "Helvetica-Bold",
            annotate_color     = "#FFFFFF",
            annotate_halign    = "center",
            annotate_valign    = "baseline",
            annotate_vertical  = 0,
            annotate_justification = "center",
            annotate_fontstyle = "BOLD",
            
            theme='default',
            themedir='/opt/sshow/themes',  # LSB/FHS compliant.  see: http://www.pathname.com/fhs/pub/fhs-2.3.html#OPTADDONAPPLICATIONSOFTWAREPACKAGES
            local_themedir="~/.sshow/themes",  # local theme directory
            
            ## not user configurable
            verbosity=0,  # for mpeg2enc and such
            slideshow_name="",
            titletext="",
            write_chap=0,
            subtitle_number=0,
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

            mpeg_encoder='ffmpeg', # or mpeg2enc.  I find ffmpeg 2x faster than mpeg2enc
            #mpeg_encoder='mpeg2enc' # or mpeg2enc.  I find ffmpeg 2x faster than mpeg2enc
            output_format='mpeg2', # or flv, mpg, mp4, mp4_ipod.  mpeg2 is default
            #output_format='flv' # or flv, mpg, mp4, mp4_ipod
            ignore_seq_end='-M',

            )
        self.update(defaults)
        
        if gst.element_factory_find("videomixer2") and False:
            self["videomixer"] = "videomixer2"
        else:
            self["videomixer"] = "videomixer"


    vars = [
        "transition",
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
        "toptitle_text_justification",
        "bottomtitle_font_size"      ,
        "bottomtitle_font_color"     ,
        "bottomtitle_bar_height"     ,
        "bottomtitle_text_location_x",
        "bottomtitle_text_location_y",
        "bottomtitle_text_justification",
        "annotate_size"              ,
        "annotate_font"              ,
        "annotate_fontstyle"         ,
        "annotate_color"             ,
        "annotate_position"          ,
        "annotate_vertical"          ,
        "annotate_justification"     ,
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

    def get_unique(self, name):
        self.unique[name] = self.unique.get(name, 0) + 1
        if self.unique[name] == 1:
            return name
        else:
            return name + "_" + str(self.unique[name])
        
    def is_var(self, key):
        return key in Config.vars

    def set_var(self, key, val):
        self[key] = val

    def get_video_caps(self, fourcc="AYUV", custom_config={}):
        """returns a gst.Caps with the configured caps. Set the fourcc 
        argument to specify a desired format, otherwise leave it None"""
        for key in ["border", "width", "height",]:
            if custom_config.has_key(key):
                exec("%s = custom_config['%s']" % (key, key))
            else:
                exec("%s = self['%s']" % (key, key))

        caps = "video/x-raw-yuv,width=%d,height=%d,framerate=(fraction)%d/%d,format=(fourcc)%s" % (width-2*border, height-2*border, self["framerate_numer"], self["framerate_denom"], fourcc)
        return gst.Caps(caps)

    def get_audio_caps(self):
        """returns a gst.Caps with the configured caps. Set the fourcc 
        argument to specify a desired format, otherwise leave it None"""
        return gst.Caps(self["audio_caps"])

    def parse_argv(self):
        """Updates this config with variables passed on the command line"""

        self.parser = parser = optparse.OptionParser()
        parser.add_option("-o", "--outdir",    dest="outdir", default=None, help="Directory where the final .vob, and dvdauthor .xml files will be written.  Default is to write in the directory where sshow was run.")
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
        parser.add_option("--logo",            dest="logo", default=None, help="option to add a logo to each slide. (does not work with transitions yet)")
        
        parser.add_option("-b",       dest="bgfile", help="Image to use for the background of the slideshow. All of the pictures will be overlaid on top of this background image. If no file is specified, black will be used for the slideshow and a blue gradient for the title slide.");
        parser.add_option("-n",       dest="slideshow_name", default="", help="The program uses this string as the filename base for the output files so you can distinguish it from other slideshows that you can send to the same output directory.")
        parser.add_option("-t",       dest="time_per_picture=", help="in tenths or hundredths of seconds?")
        parser.add_option("--writechaps", dest="write_chaps", action="store_true", default=False, help="Write out chapter times to $slideshow_name.chap")
        parser.add_option("-f", dest="input_txtfile", default=None, help="input_file.txt (-f is optional if the file is the last argument).  File to specify all the parameters and order easily for bigger slideshows.")
        parser.add_option("--nocleanup", dest="nocleanup", action="store_true", default=None, help="Leave temporary files in the temporary directory.  Useful for debugging.")
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
