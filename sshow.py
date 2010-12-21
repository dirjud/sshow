#!/usr/bin/env python

name='sshow'
version='0.8.2'

#    This program was ported from dvd-slideshow (Copyright 2003-2008
#    Scott Dylewski) from bash to python.
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from optparse import OptionParser
import sys, os, subprocess, logging
import Element, Reader

log = logging.getLogger("[sshow]")
logging.basicConfig(level=logging.INFO)

def echo(x):
    log.info(x)

def cmd(x):
    log.debug(x)
    p = subprocess.Popen(x, shell=True, stdout=subprocess.PIPE)
    return p.stdout.read()[:-1] # chop off final carriage return

echo(name + " " + version)
echo("Licensed under the GNU GPL")
echo("Copyright 2003-2007 by Scott Dylewski")

###################################################################
# Default variables:
# order of perference:  
# program defaults --> ~/.sshow/sshowrc --> command-line args --> .txtfile settings

## setup program default variables

def print_themes(themedir, config):
    """print the names of the built-in themes and quit"""
    config["themedir"] = os.path.expanduser(config["themedir"])
    if(os.path.exists(config["themedir"])): # check in default theme directory:
	echo("Using themes directory "+ config["themedir"])
	echo("Found built-in themes:")
	cmd('find "'+config["themedir"]+'"/ -maxdepth 2 -name "*.theme" -type f -print0 | xargs -0 ls')
    else:
	echo("Themes directory not found: " + config["themedir"])


class Config(dict):
    def __init__(self):
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

config = Config()

## check for the necessary programs:
def checkforprog(prog):
    res = cmd("which $1 2> /dev/null")
    if not(res):
        raise("ERROR: "+prog+" not found! Check the dependencies and make sure everything is installed.")

def cleanup(force=False):
    cmd("rm -rf " + config["workdir"])

def parse_config(filename):
    conf = {}
    f=open(filename, "r")
    for linenum, line in enumerate(f):
        # remove comments
        line = line.split("#", 1)[0].strip()
        if(line):
          x = line.split("=")
          if len(x) == 2:
              key = x[0]
              try:
                  val = eval(x[1])
              except:
                  val = x[1]
              conf[key] = val
          else:
              raise Exception("Line %d: Parse error in file %s" % (linenum, filename))

    f.close()
    return conf

def merge_configs(dest, src):
    for k,v in src.items():
        if(dest.has_key(k)):
            if type(dest[k]) is list:
                if type(v) is list:
                    dest[k] = dest[k] + v
                else:
                    dest[k].append(v)
            else:
                dest[k] = v
        else:
            dest[k] = v

############################################################
# read in the ~/.sshow/sshowrc file if it exists:

rc = os.environ["HOME"]+"/.sshow/sshowrc"
if os.path.exists(rc):
    merge_configs(config, parse_config(rc))

################################################################
## Now, set the variables that were passed on the command-line:
parser = OptionParser()
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
parser.add_option("-f", dest="input_txtfile", default="", help="input_file.txt (-f is optional if the file is the last argument).  File to specify all the parameters and order easily for bigger slideshows.")
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


if len(sys.argv) < 2:
    parser.print_usage()
    raise Exception("No arguments provided")

(options, args) = parser.parse_args()
if(options.audio):
    raise Exception("-a option to pass in audio files no longer supported")

if(options.print_themes):
	echo("Printing theme list...")
	print_themes(config["themedir"])
	print_themes(config["local_themedir"])
        sys.exit()

# merge command line options into the config
for k,v in options.__dict__.items():
    if not(v is None):
        config[k] = v
    
if not(options.input_txtfile) and args:
    config["input_txtfile"] = args[0]

if not(os.path.exists(config["input_txtfile"])):
    raise Exception("ERROR: Input file "+ config["input_txtfile"] + " does not exist.")

# make sure a slideshow name was given:
if not(config["slideshow_name"]):
    fname = os.path.basename(config["input_txtfile"])
    config["slideshow_name"] = ".".join(fname.split(".")[:-1])# remove file suffix
    echo("Using default slideshow name: " + config["slideshow_name"])

config["hilight_title"]=config["slideshow_name"]  # make default

if not(os.path.exists(config["outdir"])):
    echo("Creating output directory " + config["outdir"])
    cmd("mkdir -p " + config["outdir"])

config["pid"]    = str(os.getpid())
config["workdir"] = config["outdir"] + "/"+config["slideshow_name"] + "_work"
 
## create work directory:
if not(os.path.exists(config["workdir"])):
    os.mkdir(config["workdir"])

## initialize log file:
config["logfile"] = config["slideshow_name"] + ".log"
# myecho("[sshow] `date`" > "$outdir/$logfile"
# logecho "[sshow] Command line was:"
# logecho "[sshow] $0 $theargs"
# logecho "[sshow] sshow version $version" 
# logecho "[sshow] `uname -a`"
# logecho "[sshow] Output directory=$outdir" 
# logecho "[sshow] Locale: "
# logecho "`locale`"

#frame_border=$border ; frame_width=$(( $dvd_width - 2 * $frame_border "                              ); frame_height=$(( $dvd_height - 2 * $frame_border )) ; [ "$noecho" -eq 0 ] && echo "border=$border" ;;



def truncate_filename(filename):
    # truncate filenames so they're not longer than 40 characters:
    if len(filename) > 40:
        return filename[:40]
    else:
        return filename

def read_theme(theme):
    def get_theme_from_dir(themedir):
        files = os.listdir(themedir)
        for filename in files:
            if(filename[-6:] == ".theme"):
                theme=filename
                themefile=os.path.abspath(themedir+"/"+filename)
                return theme, themefile
        raise Exception("No .theme file found in directory " + themedir)

    if os.path.isdir(theme):
        themedir=theme
        theme, themefile = get_theme_from_dir(themedir)
    elif os.path.isfile(theme):
        themefile=os.path.abspath(theme)
        themedir=os.path.dirname(themefile)
        echo("Using theme " + truncate_filename(theme))
    else:
        # check in default theme directory:
        if os.path.isdir(themedir + "/" + theme):
            themedir=themedir+"/"+theme
            theme, themefile = get_theme_from_dir(themedir)
        elif os.path.isdir(local_themedir+"/"+theme):
            themedir=local_themedir+"/"+theme
            theme, themefile = get_theme_from_dir(themedir)
        else:
            raise Exception("ERROR!  Bad theme name (not found)")

    echo("Using theme "+ truncate_filename(themefile))
    echo("Reading theme file...")

    theme_config = parse_config(themefile)
    
#	if [ -n "$title_font" ] ; then
#	        if [ ! -f "$title_font" ] ; then
#	                title_font="$themedir"/"$title_font"
#	                if [ ! -f "$title_font" ] ; then
#	                        echo "Error:  bad title_font filename in theme"
#	                fi
#	        fi
#	fi
#	if [ -n "$subtitle_font" ] ; then
#	        if [ ! -f "$subtitle_font" ] ; then
#	                subtitle_font="$themedir"/"$subtitle_font"
#	                if [ ! -f "$subtitle_font" ] ; then
#	                        echo "Error:  bad subtitle_font filename in theme"
#	                fi
#	        fi
#	fi
#	# now, modify theme depending on ntsc/pal:
#	if [ -z "$theme_designed_for" ] ; then
#		theme_designed_for="ntsc"
#	fi
#	if [ "$theme_designed_for" == 'pal' ] && [ "$pal" == 0 ] ; then
#		# shift coordinates down by 96?
#		myecho "[sshow] Theme designed for PAL.  Shifting coordinates to NTSC"
#	elif [ "$theme_designed_for" == 'ntsc' ] && [ "$pal" == 1 ] ; then
#		# shift coordinates down by 96?
#		myecho "[sshow] Theme designed for NTSC.  Shifting coordinates to PAL"
#                #toptitle_bar_height=
#                #toptitle_text_location_y
#                # bottom title
#                #bottomtitle_font_size
#                #bottomtitle_font_color
#                #bottomtitle_bar_location_y
#                #bottomtitle_bar_height
#                #bottomtitle_text_location_y




## now, read the theme file if it was passed on the commandline:
if config["theme"] and config["theme"] != 'default':
    read_theme(theme)


## we will read the .txt file next...

if(config["debug"] >= 1):
    config["ffmpeg_out"] = config["outdir"]+"/"+config["logfile"]
else:
    config["ffmpeg_out"] = '/dev/null'




## Check for required programs
progver=cmd("mplex 2>&1 | grep version | awk '{ print $4 }'")
if progver: echo("Found mjpegtools version" + progver)
it=cmd("which ppmtoy4m 2> /dev/null")
if not(it): # no ppmtoy4m
    raise Exception("ERROR:  no mjpegtools found for audio processing.  You need to download and install mjpegtools. http://mjpegtools.sourceforge.net")

if cmd("ppmtoy4m -S 420mpeg2 xxxxx 2>&1 | grep xxxxx"):
    echo("Using mjpegtools subsampling -S 420mpeg2")
    config["subsample"] ='420mpeg2'
else:
    echo("Using mjpegtools subsampling -S 420_mpeg2")
    config["subsample"] ='420_mpeg2'
	
#checkforprog sox
progver=cmd("sox -h 2>&1 | head -n 1 | awk '{ print $3 }'")
echo("Found sox version " + progver)
it=cmd("which sox 2> /dev/null")
if not(it): # no sox
    raise Exception("ERROR:  no sox found for audio processing. You need to download and install sox. http://sox.sourceforge.net")

#checkforprog convert
progver=cmd("convert -help | head -n 1 | awk '{ print $3 }'")
echo("Found ImageMagick version " + progver)
it=cmd("which convert 2> /dev/null")
if not(it): # no convert
    raise Exception("ERROR:  no ImageMagick found for audio processing. You need to download and install ImageMagick. http://ImageMagick.sourceforge.net")

#checkforprog dvdauthor
progver=cmd("dvdauthor -h 2>&1 | head -n 1 | awk '{ print $3 }'")
echo("Found dvdauthor version " + progver)
it=cmd("which dvdauthor 2> /dev/null")
if not(it): # no dvdauthor
    raise Exception("ERROR:  no dvdauthor found for audio processing. You need to download and install dvdauthor. http://dvdauthor.sourceforge.net")

# ffmpeg
it=cmd("which ffmpeg 2> /dev/null")
if not(it):
    # no ffmpeg!  use mp2 audio instead:
    echo("Warning:  no ffmpeg found for AC3 audio encoding.")
    echo("          Using MP2 audio instead.")
    echo("          MP2 audio is less compatible with DVD player hardware.")
    echo("          http://ffmpeg.sourceforge.net")
    config["ac3"] = 0
    config["mpeg_encoder"] = 'mpeg2enc'
else:
    # found ffmpeg
    progver = cmd("ffmpeg -version 2>&1").split(",",1)[0]
    echo("Found "+ progver)
    ## check to see if we have mpeg2video output option:
    it=cmd("ffmpeg -f mpeg2video 2>&1 | grep 'Unknown input or output format: mpeg2video'")
    if it:
        echo("Warning:  ffmpeg is not compiled with the mpeg2video option")
        echo("          required for making dvds!  Using mpeg2enc instead.")
        config["mpeg_encoder"]='mpeg2enc'

################################################## done finding programs
pipeline = Reader.DVDSlideshow(config["input_txtfile"]).get_pipeline(config)


##############################################
#  Set default fonts
def find_font(font_name, font_dirs):
    for font_dir in font_dirs:
	font_path = cmd("find -L "+font_dir+" -name "+font_name+" | head -n 1")
        if font_path:
            return font_path
    raise Exception("Font not found")
        
config["default_font"] = "Helvetica-Bold" # start with ImageMagick font and then see if other fonts are available.
for font_name in config["default_fonts"]:
    try:
        config["default_font"] = find_font(font_name, config["font_dirs"])
        break
    except:
        pass
echo("default_font is " + config["default_font"])

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
    echo(name + " is "+config["title_font"])

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
#		sq_pixel_multiplier=$(( 1000 ))  # keep pixels square?
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

#cmd("awk -vw="+str(config["dvd_width"])+" -vh="+str(config["dvd_height"])+" -var="+config["aspect_ratio"]+" 'BEGIN{if (ar==\"4:3\"){ar=4/3} else {ar=16/9};printf \"%0.2f\", (100/((h/w)*(ar)));exit;}' | sed 's/,/\./g'")
#resize_factor=`awk -vw=$dvd_width -vh=$dvd_height -var=$aspect_ratio 'BEGIN{if (ar=="4:3"){ar=4/3} else {ar=16/9};printf "%0.2f", (100/((h/w)*(ar)));exit;}'`
# resize_factor is 93.75 for PAL
# resize_factor is 112.50 for NTSC
config["sq_to_dvd_pixels"]=str(config["resize_factor"]*100)+"x100%"
#sq_pixel_multiplier=$( printf %5.0f $( echo "scale=0; 10 * $resize_factor" | bc ) )
#[ $debug -ge 2 ] && myecho "[sshow] sq_to_dvd_pixels=$sq_to_dvd_pixels"

if config.has_key("output_size"):
	# used user-set size, instead of defaults!
	config.update(dict(
                orig_dvd_width=config["dvd_width"],
                orig_dvd_height=config["dvd_height"],
                ))
	config["dvd_width"], config["dvd_height"] = config["output_size"].split("x")
	if config["output_format"] in ['flv', 'swf' ]:
            config["video_bitrate"] = config["video_bitrate"] * config["dvd_width"] * config["dvd_height"] / config["orig_dvd_width"] / config["orig_dvd_height"]
            echo("Set new video bitrate to " + str(config["video_bitrate kb/s"]))

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

## summarize configuration:
if config["pal"]:
    config["ntsc_or_pal"]="PAL"
else:
    config["ntsc_or_pal"]="NTSC"
if config["ac3"]:
    config["mp2_or_ac3"]="AC3"
else:
    config["mp2_or_ac3"]="MP2"

#myecho "[sshow] Configuration summary:"
if config["vcd"]:  echo("VCD mode")
if config["svcd"]: echo("SVCD mode")
echo("Video: " + config["ntsc_or_pal"] + " " + str(config["dvd_width"]) + "x" + str(config["dvd_height"]) + " " + str(config["framerate"]) + "fps" + " " + config["aspect_ratio"])
echo("Audio: "+ config["mp2_or_ac3"] + " " + str(config["audio_sample_rate"]) + " " + str(config["audio_bitrate"])+"k")
echo("Debug="+str(config["debug"])+" Autocrop="+str(config["autocrop"])+" Subtitles="+config["subtitle_type"]+ " Border="+str(config["frame_border"]))


if not(pipeline[0].isa("Background")):
    pipeline.insert(0, Element.Background(None, "background", 0, "", config["bgfile"]))


###########################################################
# Preprocessing:  calcuate times 
# 		and do initial syntax / sanity check
###########################################################
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

log.info("Running initial error check...")
audio_index = {}
audio_length = 0
video_length = 0
prev_element = None
for pos, element in enumerate(pipeline):
    if element.isa("Audio"):
        try:
            audio_index[element.track] += 1
        except KeyError:
            audio_index[element.track] = 0
        element.index = audio_index[element.track]
        
    key = "%04d"%pos
    try:
        next_element = pipeline[pos+1]
    except:
        next_element = None
    try:
        element.initialize(key, prev_element, next_element, config)
    except Exception, e:
        raise
        raise Exception("%s: %s" % (element.location, str(e)))

    prev_element = element

    element.frames = int(round(config["framerate"] * element.duration/1000.))
    element.frames_extended += element.frames

    if isSlide(element):
        video_length += element.duration
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

	    ## Now calculate new slide times when using crossfade:
            f = element.frames/2
            prev_slide.frames_extended += f
            next_slide.frames_extended += element.frames-f
  	elif element.isa("Transition") and element.name == 'fadeout':
            try:
                prevSlide(pos, pipeline)
            except:
                raise Exception("no prevision slide to fadeout from!")
            if isNextTransition(pos, pipeline):
                raise Exception("Cannot fadeout to another transition")

    except Exception, e:
        raise Exception("%s (line %d): %s" % (element.srcfile, element.linenum, str(e)))
    
	

#  	elif [ "$file" == 'titlebar' ] ; then  # TITLEBAR
#  		nothing="nothing"
#  	elif [ "$file" == 'musictitle' ] ; then  # MUSICTITLE
#  		nothing="nothing"
#  	elif [ "${avi_file[$i]}" == 1 ] ; then  # AVI
#  		previous_transition_increment="`previousTransitionIncrement`"
#  		next_transition_increment="`nextTransitionIncrement`"
#  		if [ "${image[$i-$previous_transition_increment]}" == 'fadein' ] || [ "${image[$i-$previous_transition_increment]}" == 'crossfade' ] || [ "${image[$i-$previous_transition_increment]}" == 'wipe' ] ; then 
#  			myecho "[sshow] ERROR line ${line[$i]}. Cannot fadein or crossfade to a .avi file (yet)"
#  			exit 1
#  		fi
#  		if [ "${image[$i+$next_transition_increment]}" == 'fadeout' ] || [ "${image[$i+$next_transition_increment]}" == 'crossfade' ] || [ "${image[$i+$next_transition_increment]}" == 'wipe' ]; then
#  			myecho "[sshow] ERROR line ${line[$i]}. Cannot fadeout or crossfade from a .avi file (yet)"
#  			exit 1
#  		fi
#  	elif [ "${image_file[$i]}" == 1 ] && [ -z "${effect1[$i]}" ] ; then  # JPG
#  		nothing="nothing"
#  
#  	elif [ "${effect1[$i]}" == 'kenburns' ] ; then  # KENBURNS check
#  		if [ -z "${frames_extended[$i]}" ] ; then
#  			frames_extended[$i]=$frames
#  		fi
#  		previous_transition_increment="`previousTransitionIncrement`"
#  		previous_slide="${image[$i-$previous_transition_increment]}"
#  		if [ "$previous_transition_increment" -ne 0 ] ; then
#  			previous_duration="${duration[$i-$previous_transition_increment]}" # already in thousandths.
#  			previous_frames=`div1000 $(( $frames_per_ms * $previous_duration / 1000 ))` 
#  		fi
#  #		next_transition_increment="`nextTransitionIncrement`"
#  #		next_slide="${image[$i+$next_transition_increment]}"
#  	elif [ "${effect1[$i]}" == 'scroll' ] ; then  # SCROLL check
#  		if [ -z "${frames_extended[$i]}" ] ; then
#  			frames_extended[$i]=$frames
#  		fi
#  		previous_transition_increment="`previousTransitionIncrement`"
#  		previous_slide="${image[$i-$previous_transition_increment]}"
#  		if [ "$previous_transition_increment" -ne 0 ] ; then
#  			previous_duration="${duration[$i-$previous_transition_increment]}" # already in thousandths.
#  			previous_frames=`div1000 $(( $frames_per_ms * $previous_duration / 1000 ))` 
#  		fi
#  #		next_transition_increment="`nextTransitionIncrement`"
#  #		next_slide="${image[$i+$next_transition_increment]}"
#  	elif [ "${audio_file[$i]}" -eq 1 ] ; then  # AUDIO FILE CHECK
#  		progressbar_indicator='a'
#  		[ "$debug" -ge 2 ] && myecho "[sshow] Decoding audiofile $( truncate_filename "$file") "
#  		if [ "${audio_track[$i]}" -eq 1 ] ; then
#  			audio_1[$i_audio]="${file}"
#  			audio1_effect1[$i_audio]="${effect1[$i]}"
#  			audio1_effect1_params[$i_audio]="${effect1_params[$i]}"
#  			audio1_effect2[$i_audio]="${effect2[$i]}"
#  			audio1_effect2_params[$i_audio]="${effect2_params[$i]}"
#  			audio_index="$i_audio"
#  			audio_index_padded=`addzeros "$i_audio"`
#  			i_audio=$(( $i_audio + 1 ))
#  		elif [ "${audio_track[$i]}" -eq 2 ] ; then
#  			audio_2[$j_audio]="${file}"
#  			audio2_effect1[$j_audio]="${effect1[$i]}"
#  			audio2_effect1_params[$j_audio]="${effect1_params[$i]}"
#  			audio2_effect2[$j_audio]="${effect2[$i]}"
#  			audio2_effect2_params[$j_audio]="${effect2_params[$i]}"
#  			audio_index="$j_audio"
#  			audio_index_padded=`addzeros "$j_audio"`
#  			j_audio=$(( $j_audio + 1 ))
#  		else
#  			myecho "[sshow] ERROR: Bad audio track number."
#  			myecho "[sshow]        only use audio track 1 or 2"
#  			cleanup; exit 1
#  		fi
#  		track="${audio_track[$i]}"
#  		suffix=`echo "$file" | awk -F. '{print tolower($NF)}'`
#  #	else  
#  #		myecho "[sshow] Unrecognized or malformed line in your input file:"
#  #		myecho "[sshow] $file. effect=${effect1[$i]} effect_params=${effect1_params[$i]}"
#  #		myecho "Fix it and try again."
#  #		cleanup; exit 1
#  	fi
#  	i=$(( $i + 1 ))
#  done  ## end of error checking loop
#  if [ $debug -lt 2 ] ; then
#  	finish_progressbar $i "${#image[@]}"
#  fi
######################################################################3

def hms(ms):
    hours = ms / 1000 / 3600
    mins  = (ms - (hours * 1000 * 3600)) / 1000 / 60
    secs  = (ms - (hours * 1000 * 3600) - (mins * 1000 * 60)) / 1000.
    return "%02d:%02d:%f" % (hours, mins, secs)

log.info("Audio Length = " + hms(audio_length))
log.info("Video Length = " + hms(video_length))


if config["low_quality"]:
    log.warn("WARNING: Using low-quality mode.")
    log.warn("  This mode is for testing only.")
    log.warn("  output resolution is %dx%d" % (config["dvd_width"], config["dvd_height"],))
    log.warn("  Ignore [mpeg2enc] warnings (usually)")
elif config["high_quality"]:
    log.info("Using high-quality mode.")
elif config["svcd"]:
    log.info("Using svcd mode.")
elif config["vcd"]:
    log.info("Using vcd mode.")




has_subtitles=0
has_subtitles2=0
frame_time=0
total_slideshow_frames=0


if config["mpeg_encoder"] == 'ffmpeg':
    if config["output_format"] == 'flv':
        # do pass one first, then add audio at the end during pass 2?
        # don't do mplex, do second pass instead.
        log.info("Exporting .flv file")
        ffmpeg_args = "-f flv "+config["workdir"]+"/video.flv"
    elif config["output_format"] == 'swf':
        # do pass one first, then add audio at the end during pass 2?
        # don't do mplex, do second pass instead.
        log.info("Exporting .swf file")
        ffmpeg_args = "-f flv "+config["workdir"]+"/video.swf"
    elif config["output_format"] == 'mp4':
        # do pass one first, then add audio at the end during pass 2?
        # don't do mplex, do second pass instead.
        log.info("Exporting .mp4 file")
        ffmpeg_args = "-f mp4 -vcodec mpeg4 "+config["workdir"]+"/video.mp4"
    elif config["output_format"] == 'mp4_ipod':  # NOT TESTED YET
        # see http://www.ubuntuforums.org/showthread.php?t=114946
        # do pass one first, then add audio at the end during pass 2?
        # don't do mplex, do second pass instead.
        log.info("Exporting ipod .mp4 file")
        #ffmpeg_args = "-target $ffmpeg_target -f mp4 -vcodec mpeg4 -maxrate 1000 -b 700 -qmin 3 -qmax 5 -bufsize 4096 -g 300 "$workdir/video.mov"
    elif config["output_format"] == 'mpg':
        # do pass one first, then add audio at the end during pass 2?
        # don't do mplex, do second pass instead.
        log.info("Exporting .mpg file")
        ffmpeg_args = "-f mpeg2video "+config["workdir"]+"/video.mpg"
    else:  # default mpeg2 video for dvd/vcd
        ffmpeg_args = "-target "+config["ffmpeg_target"]+" -bf 2 -f mpeg2video "+config["workdir"]+"/video.mpg"

    encoder_cmd = "ffmpeg -f yuv4mpegpipe -i - -r "+str(config["framerate"])+" -b "+config["video_bitrate"]+" -an -aspect "+config["aspect_ratio"]+" -s "+str(config["dvd_width"])+"x"+str(config["dvd_height"])+" -y %s" % (ffmpeg_args,)

else:
    encoder_cmd = "mpeg2enc "+config["mpeg2enc_params"]+" -o "+config["workdir"]+"/video.mpg -" # < "$workdir"/$yuvfifo >> "$outdir/$logfile" 2>&1 & 

log.info(encoder_cmd)
encoder = subprocess.Popen(encoder_cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def encode(encoder, image, numframes, config):

    ppm_cmd = "ppmtoy4m -v "+str(config["verbosity"])+" -n "+str(numframes)+" -r -S "+config["subsample"]+" -F "+config["ppmtoy4m_frc"]+" -A "+config["ppmtoy4m_aspect"]+" -I p "+image
    #log.info(ppm_cmd)
    p = subprocess.Popen(ppm_cmd, shell=True, stdout=subprocess.PIPE)
    if(config["yuvfirstfile"]):
        config["yuvfirstfile"] = 0
    else:
        p.stdout.readline() # strip first line of yuv data

    encoder.stdin.write(p.stdout.read())
        
total_frames = 0
audio_duration = 0
audio_pipeline = []
prev_imgs0 = []
def num_frames(config, duration):
    return int(config["framerate"] * duration / 1000)

def split_imgs(imgs, prev_frames, curr_frames, next_frames):
    count = 0
    prev = []
    curr = []
    next = []
    prevN = prev_frames
    currN = prev_frames + curr_frames
    nextN = prev_frames + curr_frames + next_frames
    state = "prev"

    for img in imgs:
        available = img[1]
        if state == "prev":
            if count == prevN:
                state = "curr"
            elif count + available > prevN:
                state = "curr"
                prev.append( (img[0], prevN-count) )
                available -= prevN - count
                count     += prevN - count
            else:
                prev.append( (img[0], available) )
                count += available
        
        if state == "curr":
            if count == currN:
                state = "next"
            elif count + available > currN:
                state = "next"
                curr.append( (img[0], currN-count) )
                available -= currN - count
                count     += currN - count
            else:
                curr.append( (img[0], available) )
                count += available

        if state == "next":
            if available:
                next.append( (img[0], available) )
                count += available

    return prev, curr, next

for element in pipeline:
    element.start_frame = total_frames

    if(element.isa("Background") and element.duration == 0): 
        continue # drop 0 duration background slides

    if element.isa("Audio"):
        audio_duration += element.duration
        audio_pipeline.append(element)
        continue

    if(element.isa("Transition")):
        continue

    # calculate the number of frames this element will consume
    frames = num_frames(config, element.duration)

    # check if we need to generate frames to overlap with the
    # last/next element as part as part of a transition
    if element.prev and element.prev.isa("Transition"):
        prev_frames = num_frames(config, element.prev.duration)
    else:
        prev_frames = 0
    
    if element.next and element.next.isa("Transition"):
        next_frames = num_frames(config, element.next.duration)
    else:
        next_frames = 0

    # generate the frames
    imgs = element.get_images(prev_frames + frames + next_frames, config)

    # now split up the frames based on the transition
    prev_imgs1, cur_imgs, next_imgs = split_imgs(imgs, prev_frames, frames, next_frames)

    # process previous transition
    if prev_frames:
        comp_imgs = element.prev.compose(prev_imgs0, prev_imgs1, config)
        for img in comp_imgs:
            encode(encoder, img[0], img[1], config)
            total_frames += img[1]

    # process current frames (i.e. frames not in transition)
    for img in cur_imgs:
        encode(encoder, img[0], img[1], config)
        total_frames += img[1]

    # save off the frames of the next transition for the next time around
    prev_imgs0 = next_imgs

encoder.stdin.close()
encoder.wait()

video_duration = total_frames * 1000 / config["framerate"]

log.info("Audio duration = %s" % (audio_duration,))
log.info("Video duration = %s" % (video_duration,))

############################################################################
# AUDIO section...
##########################################################################
if(audio_duration < video_duration):
    silence = Element.Silence("Auto-Inserted", video_duration-audio_duration)
    silence.initialize("END", None, None, config)
    audio_pipeline.append(silence)
    log.info("Created Silence " + str(silence.duration))
    audio_duration += silence.duration

audio_raw = config["workdir"]+"/audio.raw"
audio_wav = config["workdir"]+"/audio.wav"
audio_dur = 0
reached_end = False
cmd("rm -f " + audio_raw)
for element in audio_pipeline:
    if(audio_dur + element.duration > video_duration):
        log.info("Trimming audio")
        element.trim(video_duration - audio_dur, config)
        reached_end = True

    element.apply_fx(config)
    audio_dur += element.duration
    cmd("cat %s >> %s" % (element.filename, audio_raw))

    if(reached_end):
        break
audio_duration = audio_dur
log.info("Audio duration = %s" % (audio_duration,))
log.info("Video duration = %s" % (video_duration,))

# now raw audio file should match in length
    
cmd("sox -2 -e signed -c 2 -r %s %s %s" % (config["audio_sample_rate"], audio_raw, audio_wav))


if config["ac3"] and config["output_format"] == 'mpeg2':
    log.info("Creating ac3 audio...")
    cmd("rm -f "+config["workdir"]+"/audio.ac3")
    cmd("ffmpeg -i "+audio_wav+" -vn -ab "+str(config["audio_bitrate"])+"k -acodec ac3 -vol 100 -ar "+str(config["audio_sample_rate"])+" -ac 6 "+config["workdir"]+"/audio.ac3 >> "+config["ffmpeg_out"]+" 2>&1")
else:
    raise Exception("Not yet supported")
# 	else
# 		## toolame is way faster! (3x in my test)
# 		it=`which toolame 2> /dev/null`
# 		if [ -n "$it" ] ; then
# 			toolame_version=`toolame -h | head -n 4 | grep version | awk '{ print $3 }'`
# 			myecho "[sshow] Creating mp2 audio using toolame $toolame_version..."
# 			if [ "$toolame_version" == '0.2m' ] ; then
# 				toolame -s $audio_sample_rate -b $audio_bitrate "$workdir/audio1.wav" "$workdir/audio1.mp2" >> "$outdir"/"$logfile" 2>&1
# 			else
# 				if [ "$vcd" -eq 1 ] || [ "$svcd" -eq 1 ] ; then
# 				toolame -s 44.1 -b $audio_bitrate "$workdir/audio1.wav" "$workdir/audio1.mp2" >> "$outdir"/"$logfile" 2>&1
# 				else
# 				toolame -s 48 -b $audio_bitrate "$workdir/audio1.wav" "$workdir/audio1.mp2" >> "$outdir"/"$logfile" 2>&1
# 				fi
# 			fi
# 		else
# 			myecho "[sshow] Creating mp2 audio using mp2enc"
# 			mp2enc -v $verbosity -b $audio_bitrate -r $audio_sample_rate -s -o "$workdir/audio1.mp2" < "$workdir/audio1.wav"
# 		fi
# 	fi



## check to make sure the output files exist before running mplex:
if not(os.path.exists(config["workdir"]+"/video.mpg")):
    raise Exception("ERROR: no output video.mpg file found! This usually happens when ffmpeg screws up something or one image is messed up and the resulting video can't be created")
	
log.info("Multiplexing audio and video...")

## now multiplex the audio and video:
## -M option is important:  it generates a "single" output file instead of "single-segement" ones
## if you don't use -M, the dvdauthor command will fail!
## total mplex bitrate = 128kBit audio + 1500 kBit video + a little overhead
verbosity=0

#if [ "$output_format" == 'flv' ] ; then  # only one audio track for .flv, .swf, and .mp4, etc...
#	myecho "[sshow] Adding audio to .flv file"
#	ffmpeg -y -i "$workdir/audio1.wav" -i "$workdir/video.flv" -vcodec copy -f flv -ar 22050 -ab 48 -ac 1 "$workdir/video1.flv" >> "$ffmpeg_out" 2>&1 
#	mv "$workdir/video1.flv" "$outdir"/"$slideshow_name".flv
#	myecho "[sshow] Generating video thumbnail..."
#	ffmpeg -y -i "$outdir"/"$slideshow_name".flv -f mjpeg -t 0.001 "$outdir"/"$slideshow_name".jpg >> "$ffmpeg_out" 2>&1
#	if [ -f "/usr/bin/flvtool2" ] ; then
#		myecho "[sshow] Running flvtool2 -U $slideshow_name".flv
#		/usr/bin/flvtool2 -U "$outdir"/"$slideshow_name".flv
#	fi
#elif [ "$output_format" == 'swf' ] ; then
#	myecho "[sshow] Adding audio to .swf file"
#	ffmpeg -y -i "$workdir/audio1.wav" -i "$workdir"/video.swf -vcodec copy -f flv -ar 22050 -ab 48 -ac 1 "$workdir"/video1.swf >> "$ffmpeg_out" 2>&1 
#	mv "$workdir"/video1.swf "$outdir"/"$slideshow_name".swf
#	myecho "[sshow] Generating video thumbnail..."
#	ffmpeg -y -i "$outdir"/"$slideshow_name".swf -f mjpeg -t 0.001 "$outdir"/"$slideshow_name".jpg >> "$ffmpeg_out" 2>&1
#elif [ "$output_format" == 'mp4' ] ; then   # lightly tested
#	myecho "[sshow] Adding audio to .mp4 file"
#	ffmpeg -y -i "$workdir/audio1.wav" -i "$workdir"/video.mp4 -vcodec copy -f mp4 -ar 22050 -ab 48 -ac 1 "$workdir"/video1.mp4 >> "$ffmpeg_out" 2>&1 
#	mv "$workdir"/video1.mp4 "$outdir"/"$slideshow_name".mp4
##	ffmpeg -f yuv4mpegpipe -i "$workdir"/$yuvfifo -r $framerate -an -aspect $aspect_ratio -s "$dvd_width"x"$dvd_height" -y -f mp4 -vcodec mpeg4 "$workdir/video.mp4" >> "$outdir/$logfile" 2>&1
#elif [ "$output_format" == 'mp4_ipod' ] ; then   # NOT TESTED YET
#	myecho "[sshow] Exporting ipod .mp4 file"
##	ffmpeg -f yuv4mpegpipe -i "$workdir"/$yuvfifo -target $ffmpeg_target -r $framerate -an -aspect $aspect_ratio -s "$dvd_width"x"$dvd_height" -y -f mp4 -vcodec mpeg4 -maxrate 1000 -b 700 -qmin 3 -qmax 5 -bufsize 4096 -g 300 "$workdir/video.mov" >> "$outdir/$logfile" 2>&1
#
#elif [ -n "${audio_2[0]}" ] && [ "$vcd" -eq 0 -a "$svcd" -eq 0 ] ; then
#	## two audio tracks!
#	echo "[dvd-slidehsow] two audio tracks found"
#	if [ "$ac3" -eq 1 ] ; then
#		mplex -V -v $verbosity $ignore_seq_end $video_buffer -f $mplex_type -o "$outdir"/"$slideshow_name".vob "$workdir/video.mpg" "$workdir"/audio1.ac3 "$workdir"/audio2.ac3 2>> "$outdir/$logfile"
#	else
#		mplex -V -v $verbosity $ignore_seq_end $video_buffer -f $mplex_type -o "$outdir"/"$slideshow_name".vob "$workdir/video.mpg" "$workdir"/audio1.mp2 "$workdir"/audio2.mp2 2>> "$outdir/$logfile"
#	fi
#else  # default mpeg2 video for dvd/vcd
if config["ac3"]:
    cmd("mplex -V "+config["video_buffer"]+" "+config["ignore_seq_end"]+" -f "+str(config["mplex_type"])+" -o "+config["outdir"]+"/"+config["slideshow_name"]+".vob "+config["workdir"]+"/video.mpg "+config["workdir"]+"/audio.ac3")
