import os, subprocess, hashlib, time, sys, gst
import logging
import transition, Annotate

log = logging.getLogger(__name__)

unique = 0
def get_unique():
    global unique
    unique += 1
    return "%05d" % unique

def cmd(x):
    log.debug("cmd: " + x)
    p = subprocess.Popen(x, shell=True, stdout=subprocess.PIPE)
    return p.stdout.read()[:-1] # chop off final carriage return


def cmdif(src, outdir, extension, command):
    """runs the command based on 'src' file if necessary. Returns the
    filename of the generated file. The 'cmd' should contain a single
    %s that will be used as the substitution pattern of the output
    file. The output file name is generated as the sha1 of the
    'command' and then substituted into the command and run as
    necessary. 'src' is the file that is used to generate the output
    file. Its date is compared against the destination to see if it
    needs run.  Set 'src' to None if there is no source file."""

    sha1 = hashlib.sha1(command).hexdigest()
    if src is None:
        src_date = 0
    else:
        src_date = 0
        if type(src) in [list, tuple]:
            for s in src:
                src_date = max(os.path.getmtime(s), src_date)
        else:
            src_date = os.path.getmtime(src)
    dest = outdir + "/" + sha1 + "." + extension
    if(os.path.exists(dest)):
        dest_date = os.path.getmtime(dest)
        if(src_date < dest_date):
            log.debug("NOT RECREATING "+dest)
            log.debug(command)
            return dest
    cmd(command % dest)
    return dest
            
def get_rgb(x):
    a = r = g = b = 0xFF
    
    if type(x) is str and x[0] == "#":
        r = int(x[1:3],16)
        g = int(x[3:5],16)
        b = int(x[5:7],16)
    return r,g,b

def get_color(x):
    a = r = g = b = 0xFF
    
    if type(x) is str and x[0] == "#":
        r = int(x[1:3],16)
        g = int(x[3:5],16)
        b = int(x[5:7],16)
    else:
        raise Exception("Unknown color '%s'" % (str(x)))
    
    return (a << 24) | (r << 16) | (g << 8) | b
    #import struct
    #return int(struct.pack(">BBBB", a,r,g,b))

def get_dims(img_file):
    return map(int, cmd('identify -format "%w %h" '+img_file).split())

def get_duration(filename):
    d = gst.parse_launch("filesrc location="+filename+" ! decodebin2 ! fakesink")
    d.set_state(gst.STATE_PAUSED)
    d.get_state() # blocks until state transition has finished
    duration = d.query_duration(gst.Format(gst.FORMAT_TIME))[0]
    d.set_state(gst.STATE_NULL)
    return duration

def dur2flt(dur):
    return dur / float(gst.SECOND)

################################################################################
class Effect():
    def __init__(self, name, param):
        self.name = name
        self.param = param


################################################################################
class Element():
    def __init__(self, location):
        self.location = location

    def initialize(self):
        pass

    def link(self, prev, next):
        self.next=next
        self.prev=prev

    def set_config(self, config):
        self.config = config

    def isa(self, type1):
        return issubclass(self.__class__, eval(type1))

    def _find_background(self):
        if issubclass(self.__class__, Background):
            return self
        elif(self.prev):
            return self.prev._find_background()
        else:
            #raise Exception("Cannot find background")
            # no background found, so return default black one
            element = Background("generated", "background", 0, "", "#000000")
            element.create_slide(self.config)
            return element

    def __str__(self):
        return self.name

    def replace(self, element):
        element.next = self.next
        element.prev = self.prev
        if(self.prev):
            self.prev.next = element
        if(self.next):
            self.next.prev = element

    def insert_after(self, element):
        element.next = self.next
        element.prev = self
        if self.next:
            self.next.prev = element
        self.next = element

    def insert_before(self, element):
        element.prev = self.prev
        element.next = self
        if self.prev:
            self.prev.next = element
        self.prev = element

    def remove(self):
        if self.prev:
            self.prev.next = self.next
        if self.next:
            self.next.prev = self.prev


def encode(x):
    return x.replace(":","\:")

################################################################################
class Comment(Element):
    def __init__(self, location, comment):
        Element.__init__(self, location)
        self.comment = comment
        self.name = "comment"
    def __str__(self):
        return self.comment

################################################################################
class EmptyLine(Element):
    def __init__(self, location):
        Element.__init__(self, location)
        self.name="emptyline"
    def __str__(self):
        return ""

################################################################################
class Config(Element):
    def __init__(self, location, name, val):
        Element.__init__(self, location)
        self.name = name
        self.val  = val
    def __str__(self):
        return "%s=%s" % (self.name, self.val)

################################################################################
class Image(Element):
    extensions = ['jpg', 'png', 'jpeg' ]
    def __init__(self, location, filename, extension, duration, subtitle, effects):
        Element.__init__(self, location)
        self.name      = os.path.basename(filename).replace("."+extension,"")
        self.filename  = filename
        self.extension = extension
        self.duration  = duration
        self.subtitle  = subtitle
        self.effects   = effects
        if(self.duration <= 0):
            self.duration = 5.0;

    def initialize(self):
        if not(os.path.exists(self.filename)):
            raise Exception("Image "+self.filename+" does not exist.")
        self.width, self.height = get_dims(self.filename)

    def __str__(self):
        x = "%s:%g:%s" % (encode(self.filename), dur2flt(self.duration), encode(self.subtitle))
        fx = ":".join([ "%s:%s" % (y.name,encode(y.param)) for y in self.effects ])
        if(fx):
            x += ":" + fx
        return x

    def get_bin(self, duration=None):
        if duration is None:
            duration = self.duration
        fx_names = [ x.name for x in self.effects ]

        bin = gst.Bin()
        elements = []
        for name in [ "filesrc", "decodebin2", "ffmpegcolorspace", "imagefreeze", "kenburns", "ffmpegcolorspace", "capsfilter",  ]:
            elements.append(gst.element_factory_make(name))
            exec("%s = elements[-1]" % name)
    
        annotate = None
        if "annotate" in fx_names:
            annotate = gst.element_factory_make("textoverlay")
            elements.append(annotate)
            Annotate.parse_annotate_params(self, annotate, self.effects[fx_names.index("annotate")].param, duration)
            
        filesrc.set_property("location",  self.filename)
        kenburns.set_property("duration", duration)
        capsfilter.set_property("caps", self.config["video_caps"])
    
        bin.add(*elements)
        filesrc.link(decodebin2)
        gst.element_link_many(*elements[2:])

        if("kenburns" in fx_names):
            i = fx_names.index("kenburns")
            param = self.effects[i].param
            zstart, pstart, zend, pend = map(str.strip, param.split(";"))
            zoom1, xcenter1, ycenter1 = self.parse_kb_params(zstart, pstart)
            zoom2, xcenter2, ycenter2 = self.parse_kb_params(zend,   pend)
            kenburns.props.zoom1    = zoom1
            kenburns.props.zoom2    = zoom2 
            kenburns.props.xcenter1 = xcenter1
            kenburns.props.ycenter1 = ycenter1
            kenburns.props.xcenter2 = xcenter2
            kenburns.props.ycenter2 = ycenter2
        else:
            kenburns.props.zoom1    = 1.0
            kenburns.props.xcenter1 = 0.5
            kenburns.props.ycenter1 = 0.5
            kenburns.props.zoom2    = 1.0
            kenburns.props.xcenter2 = 0.5
            kenburns.props.ycenter2 = 0.5

        def on_pad(src_element, pad, data, sink_element):
            sinkpad = sink_element.get_compatible_pad(pad, pad.get_caps())
            pad.link(sinkpad)

        decodebin2.connect("new-decoded-pad", on_pad, elements[2])
        bin.add_pad(gst.GhostPad("src", elements[-1].get_pad("src")))
        return bin


    def parse_kb_params(self, zoom, pos):
        img_ratio = self.width / float(self.height)
        vid_ratio = self.config["aspect_ratio_float"]

        if(img_ratio > vid_ratio):
            src_width = self.width
            src_height = int(round(src_width / vid_ratio))
        else:
            src_height = self.height
            src_width = int(round(src_height * vid_ratio))

        if zoom == "imagewidth":
            z = self.width / float(src_width)
        elif zoom == "imageheight":
            z = self.height / float(src_height)
        elif(zoom.endswith("%")):
            z = eval(zoom.replace("%",""))/100.
        else:
            raise Exception("Unknown kenburns zoom parameter '%s'" % (zoom, ))

        if pos[:3] in ["top", "bot", "lef", "rig", "mid"]:
            if pos.find("bottom") > -1:
                yc = (src_height - self.height)/2. - (src_height  * z)/2 + self.height
            elif pos.find("top") > -1:
                yc = (src_height - self.height)/2. + (src_height  * z)/2
            else:
                yc = src_height / 2.
            
            if pos.find("left") > -1:
                xc = (src_width - self.width)/2. + (src_width  * z)/2
            elif pos.find("right") > -1:
                xc = (src_width - self.width)/2. - (src_width  * z)/2 + self.width
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
    
        return (z, xcenter, ycenter)

################################################################################
class Background(Image):
    names = ['background',]
    colors = ['black','white','red','green','blue','orange','purple','yellow', 'cyan', 'magenta']

    def __init__(self, location, name, duration, subtitle, background):
        Element.__init__(self, location)
        self.name = name
        self.duration = duration
        self.subtitle = subtitle
        self.bg = background
        self.effects = []

        if(self.bg == "" and self.duration <= 0): # blank bg means use the last one
            raise Exception("Cannot specify a 0 duration and no background file or color")
        if(self.bg and self.bg[0] != "#" and not(self.bg in Background.colors) and not(os.path.exists(self.bg))):
             raise Exception("Unknown background specified. Must be a file or color")

    def __str__(self):
        x = "%s:%g:%s:%s" % (self.name, dur2flt(self.duration), self.subtitle, self.bg)
        return x

    def initialize(self):
        if self.bg == "":
            prev_bg = self.prev._find_background()
            self.filename = prev_bg.filename
            self.extension= prev_bg.extension
            self.width = prev_bg.width
            self.height= prev_bg.height

        #elif os.path.exists(self.bg): # if effect is a background file
        #    self.filename = crop_img(self.bg, self.extension, self.config)
        else: ## use plain black background with no picture
            r,g,b = get_rgb(self.bg)
            self.filename = self.config["workdir"]+"/%02x%02x%02x.ppm" % (r,g,b)
            self.extension="ppm"
            print r,g,b,self.filename
            self.width = self.config["width"]
            self.height= self.config["height"]
            f = open(self.filename, "w")
            f.write("P6\n%d %d\n255\n" % (self.width, self.height))
            import struct
            f.write( struct.pack("BBB", r,g,b) * (self.width*self.height))
            f.close()
            #convert = "convert -size "+str(self.width)+'x'+str(self.height)+" xc:"+self.bg+" -type TrueColorMatte -depth 8 %s"
            #self.filename = cmdif(None, self.config["workdir"], self.extension, convert)

#    def get_bin(self):
        


################################################################################
class Title(Image):
    names = ["title", "titlebar"]
    def __init__(self, location, name, duration, title1, title2):
        Element.__init__(self, location)
        self.name = name
        self.duration = duration
        self.title1 = title1
        self.title2 = title2
        self.effects = []
        if not(self.title1):
            raise Exception("No title text found.")

    def __str__(self):
        return "%s:%g:%s:%s" % (self.name, dur2flt(self.duration), self.title1, self.title2)

    def initialize(self):
        self.extension = "png"
        bg = self._find_background()
        fsize = self.config["title_font_size"]
        fcolor = self.config["title_font_color"]

	if self.config["low_quality"] or self.config["vcd"] or self.config["output_format"] in ['flv', 'swf', 'mp4', 'mpg']:
            fsize = fsize * self.config["dvd_height"] / 480
            
	## if background is black & font color is black, change font to white
        if bg.bg == "black" and fcolor == 'black':
            fcolor='white'
        
        self.width = self.config["width"]*1
        self.height= self.config["height"]*1

        convert = ("convert -size %dx%d xc:transparent -fill '%s' -pointsize %s -gravity Center -font %s -annotate 0 '%s' -type TrueColorMatte -depth 9 miff:- | composite -compose src-over -type TrueColorMatte -depth 8 - %s" % (self.width, self.height, fcolor, fsize, self.config["title_font"], self.title1.replace("'","'\"'\"'"), bg.filename)).replace("%", "%%") + " %s"
        
        self.filename = cmdif(bg.filename, self.config["workdir"], self.extension, convert)

################################################################################
class Transition(Element):
    names   = ['fadein', 'fadeout', 'crossfade', 'wipe']

    def __init__(self, location, name, duration):
        Element.__init__(self, location)
        if not(name in Transition.names):
            raise Exception("Unknown transition %s" % name)
        if duration <= 0:
            raise Exception("Transition duration must be a positive number.")
        self.name     = name
        self.duration = duration

        if name in ['fadein', 'fadeout', 'crossfade']:
            self.get_transition_bin = transition.get_crossfade_bin
        if name in ["wipe"]:
            self.get_transition_bin = transition.get_smpte_bin

    def __str__(self):
        return "%s:%g" % (self.name, dur2flt(self.duration))

    def get_bin(self):
        bin, self.controller = self.get_transition_bin(self.config, self.duration)
        return bin


################################################################################
class Audio(Element):
    extensions = [ 'ogg', 'mp3', 'wav', 'silence', 'm4a', 'aac' ]

    def __init__(self, location, filename, extension, track, effects):
        Element.__init__(self, location)
        if not(os.path.exists(filename)):
            raise Exception("Audio file "+filename+" does not exist.")

        self.name     = os.path.basename(filename).replace("."+extension,"")
        self.filename = filename
        self.extension = extension
        self.track = track
        self.effects= effects

        if(self.track > 2):
            raise Exception("ERROR: Only 2 audio tracks supported at this time.  Fix this audio file track number!")
        if(self.track < 1):
            raise Exception("ERROR: Must specify positive and non-zero track number.  Fix this audio file track number!")

        self.fadein  = 0
        self.fadeout = 0

        for effect in self.effects:
            if not(effect.name in ["fadein","fadeout"]):
                       raise Exception("ERROR: %s unknown audio effect. 'fadein' and 'fadeout' are only valid effects")
            dur =  int(round(gst.SECOND * float(effect.param)))
            exec("self."+effect.name+" = dur")

    def __str__(self):
        x = "%s:%s" % (self.filename, self.track)
        fx = ":".join([ "%s:%s" % (y.name,y.param) for y in self.effects ])
        if(fx):
            x += ":" + fx
        return x
        x = "%s:%s" % (self.filename, self.track)

    def initialize(self):
        self.duration = get_duration(self.filename)

    def get_bin(self, duration=None):
        bin = gst.Bin()
        elements = []
        for name in [ "filesrc", "decodebin2", "audioconvert", "volume", "capsfilter",  ]:
            elements.append(gst.element_factory_make(name, name))
            exec("%s = elements[-1]" % name)
    
        capsfilter.props.caps = self.config["audio_caps"]
        filesrc.set_property("location",  self.filename)
        bin.add(*elements)
        filesrc.link(decodebin2)
        audioconvert.link(volume)
        volume.link(capsfilter)
        
        self.volume_controller = gst.Controller(volume, "volume")
        self.volume_controller.set_interpolation_mode("volume", gst.INTERPOLATE_LINEAR)
        if self.fadein:
            self.volume_controller.set("volume", 0,    0.0)
            self.volume_controller.set("volume", self.fadein, 1.0)
        else:
            self.volume_controller.set("volume", 0, 1.0)
            
        if self.fadeout:
            self.volume_controller.set("volume", duration-self.fadeout, 1.0)
            self.volume_controller.set("volume", duration,      0.0)
        else:
            self.volume_controller.set("volume", duration, 1.0)

        def on_pad(src_element, pad, data, sink_element):
            sinkpad = sink_element.get_compatible_pad(pad, pad.get_caps())
            pad.link(sinkpad)

        decodebin2.connect("new-decoded-pad", on_pad, audioconvert)
        bin.add_pad(gst.GhostPad("src", capsfilter.get_pad("src")))
        return bin

    
    
#        elif image[-1] == 'musictitle':
#            types.append("musictitle")
#            ensure_not_zero_duration(duration[-1])
#            duration_ms = int(duration[-1]*1000)
#            total_video_length += duration_ms
#    #    elif [ "`echo $file | tr -d \[:blank:\]`" == 'chapter' ] ; then   # CHAPTER
#    #		image_file[$i]=0 ; audio_file[$i]=0 ; avi_file[$i]=0
#    #		duration[$i]=0;
#    #		duration_ms=`seconds2ms ${duration[$i]}`
#    ##		total_video_length="$(( $total_video_length + $duration_ms ))"
#        elif filetype[-1] == 'avi':
#            types.append("video")
#            ### need to get the length of the video here and set the duration
#            ### so the audio is the correct length!
#            checkforprog("tcprobe")
#    		#if [ -n "${duration[$i]}" ] ; then
#    		#	# user specified something in duration field:
#    		#	if [ "${duration[$i]}" == 'noaudio' ] ; then
#    		#		# do not use audio contained in video
#    		#		audio_track[$i]='noaudio'
#    		#	else
#    		#		audio_track[$i]='audio'
#    		#	fi
#    		#fi
#    		#effect1[$i]=`echo "${thisline}" | cut -s -d: -f3 | awk -F' #' '{print $1}'`  
#    		#effect1_params[$i]=`echo "${thisline}" | cut -s -d: -f4 | awk -F' #' '{print $1}' | tr -d \[:blank:\]`
#    		#effect2[$i]=`echo "${thisline}" | cut -s -d: -f5 | awk -F' #' '{print $1}'`
#    		#effect2_params[$i]=`echo "${thisline}" | cut -s -d: -f6 | awk -F' #' '{print $1}' | tr -d \[:blank:\]`
#            	#video_length=`tcprobe -i "${image[$i]}" 2> /dev/null | grep 'duration=' | awk -F'duration=' '{print $2}'`
#    		#it=`hms2seconds "$video_length"`
#    		#duration_ms=`seconds2ms $it`
#    		#duration[$i]="`hms2seconds $video_length`"
#    		#total_video_length="$(( $total_video_length + $duration_ms ))"
#    		#echo ""
#            	#myecho "[dvd-slideshow] Found AVI video ${image[$i]} length=$video_length duration=${duration[$i]}"
#    		#myechon "[dvd-slideshow] "
#    		### optionally copy images to new directory for backup onto dvd:
#    		#newname=`echo "${slideshow_name}" | sed -e 's/ /_/g'`
#    		#if [ "$copy" -eq 1 ] ; then
#    		#	mkdir -p "$outdir/$newname"_pics
#    		#fi
#    		#if [ "$copy" -eq 1 ] ; then
#    		#	cp -af "${image[$i]}" "$outdir/$newname"_pics
#    		#fi
#    		#moviefiles=$(( $moviefiles + 1 ))
#        else:
#            duration_ms = int(duration[-1]*1000)
#            total_video_length += duration_ms
#    
