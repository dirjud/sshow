import os, subprocess, hashlib, time, sys, gst
import logging
import transition, Annotate

log = logging.getLogger(__name__)

def get_rgb(x):
    a = r = g = b = 0xFF
    
    if type(x) is str and x[0] == "#":
        r = int(x[1:3],16)
        g = int(x[3:5],16)
        b = int(x[5:7],16)
    return r,g,b

colorLU = { "black":"#000000", "white":"#FFFFFF", "red":"#FF0000", "green":"#00FF00", "blue":"#0000FF", "orange":"#F37022", "purple":"#FF00FF", "yellow":"#FFFF00", "cyan":"#00FFFF", "magenta":"#FF00FF" }

def get_color(x):
    if colorLU.has_key(x):
        x = colorLU[x]

    a = r = g = b = 0xFF
    
    if type(x) is str and x[0] == "#":
        r = int(x[1:3],16)
        g = int(x[3:5],16)
        b = int(x[5:7],16)
    else:
        raise Exception("Unknown color '%s'" % (str(x)))
    return (a << 24) | (r << 16) | (g << 8) | b

def get_dims(img_file):
    import commands
    return map(int, commands.getoutput('identify -format "%w %h" '+img_file).split())
    #d = gst.parse_launch("filesrc location="+img_file+" ! decodebin2 name=decoder ! fakesink")
    #d.set_state(gst.STATE_PLAYING)
    #d.get_state() # blocks until state transition has finished
    #caps = d.get_by_name("decoder").src_pads().next().get_caps()[0]
    #return caps["width"], caps["height"]

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
        self.controllers = []

    def initialize(self):
        pass

    def set_config(self, config):
        self.config = config

    def isa(self, type1):
        return issubclass(self.__class__, eval(type1))

    def __str__(self):
        return self.name

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
    extensions = ['jpg', 'png', 'jpeg', "bmp", "gif", ]
    def __init__(self, location, filename, duration, subtitle, effects):
        Element.__init__(self, location)
        self.name      = os.path.basename(filename)
        self.filename  = filename
        self.duration  = duration
        self.subtitle  = subtitle
        self.effects   = effects
        if(self.duration <= 0):
            self.duration = 5.0;

    def initialize(self):
        if not(os.path.exists(self.filename)):
            raise Exception("Image "+self.filename+" does not exist.")

    def __str__(self):
        x = "%s:%g:%s" % (encode(self.filename), dur2flt(self.duration), encode(self.subtitle))
        fx = ":".join([ "%s:%s" % (y.name,encode(y.param)) for y in self.effects ])
        if(fx):
            x += ":" + fx
        return x

    def get_bin(self, background, duration=None):
        if duration is None:
            duration = self.duration
        self.width, self.height = get_dims(self.filename)

        fx_names = [ x.name for x in self.effects ]

        bin = gst.Bin()
        elements = []
        for name in [ "filesrc", "decodebin2", "ffmpegcolorspace", "capsfilter", "imagefreeze", "kenburns", ]:
            elements.append(gst.element_factory_make(name))
            exec("%s = elements[-1]" % name)

        annotate = None
        if "annotate" in fx_names:
            annotate = gst.element_factory_make("textoverlay")
            elements.append(annotate)
            Annotate.parse_annotate_params(self, annotate, self.effects[fx_names.index("annotate")].param, duration)

        if self.config["subtitle_type"] == "render" and self.subtitle:
            subtitle = gst.element_factory_make("textoverlay")
            elements.append(subtitle)
            Annotate.add_subtitle(self, subtitle, self.subtitle, self.config)

        caps = gst.element_factory_make("capsfilter")
        elements.append(caps)

        filesrc.set_property("location",  self.filename)
        capsfilter.set_property("caps", gst.Caps("video/x-raw-yuv,format=(fourcc)AYUV"))
        caps.set_property("caps", self.config.get_video_caps("AYUV"))

        bin.add(*elements)
        filesrc.link(decodebin2)
        gst.element_link_many(*elements[2:])

        if 1:
            mixer  = gst.element_factory_make(self.config["videomixer"])
            bg_bin = background.get_bin()
            bin.add(mixer, bg_bin)
            bg_bin.link(mixer)
            elements[-1].link(mixer)
            elements.append(mixer)

        if("kenburns" in fx_names):
            i = fx_names.index("kenburns")
            param = self.effects[i].param
            zstart, pstart, zend, pend = map(str.strip, param.split(";"))
            zpos1, xpos1, ypos1 = self.parse_kb_params(zstart, pstart)
            zpos2, xpos2, ypos2 = self.parse_kb_params(zend,   pend)
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
            print zpos1, zpos2, xpos1, xpos2, ypos1, ypos2
            self.controllers.append(c)

        def on_pad(src_element, pad, data, sink_element):
            sinkpad = sink_element.get_compatible_pad(pad, pad.get_caps())
            pad.link(sinkpad)

        decodebin2.connect("new-decoded-pad", on_pad, ffmpegcolorspace)
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
    
        return (z, (xcenter-0.5)*2, (ycenter-0.5)*2)

################################################################################
class Background(Element):
    names = ['background',]
    colors = colorLU.keys()

    def __init__(self, location, name, duration, subtitle, background, effects=[]):
        Element.__init__(self, location)
        self.name = name
        self.duration = duration
        self.subtitle = subtitle
        self.bg = background
        self.effects = effects

        if(self.bg == "" and self.duration <= 0): # blank bg means use the last one
            raise Exception("Cannot specify a 0 duration and no background file or color")
        if(self.bg and self.bg[0] != "#" and not(self.bg in Background.colors) and not(os.path.exists(self.bg))):
             raise Exception("Unknown background specified. Must be a file or color")

    def __str__(self):
        if self.bg.__class__ is Background:
            bg = ""
        else:
            bg = self.bg
        x = "%s:%g:%s:%s" % (self.name, dur2flt(self.duration), self.subtitle, bg)
        return x

    def set_prev_background(self, prev_background):
        if self.bg == "":
            self.bg = prev_background

    def get_bin(self, background=None, duration=None):
        if duration is None:
            duration = self.duration

        if self.bg.__class__ is Background:
            return self.bg.get_bin()
        elif(os.path.exists(self.bg)):
            return get_bg_image_bin(self)
        elif(self.bg in Background.colors):
            return self.get_bg_color_bin(colorLU[self.bg])
        elif(self.bg[0] == "#"):
            return self.get_bg_color_bin(self.bg)

    def get_bg_color_bin(self, bgcolor):
        elements=[]
        src  = gst.element_factory_make("videotestsrc")
        src.props.pattern = "white"
        src.props.foreground_color = get_color(bgcolor)
        elements.append(src)
        if self.config["subtitle_type"] == "render" and self.subtitle:
            subtitle = gst.element_factory_make("textoverlay")
            Annotate.add_subtitle(self, subtitle, self.subtitle, self.config)
            elements.append(subtitle)
        caps = gst.element_factory_make("capsfilter")
        caps.props.caps = self.config.get_video_caps("AYUV")
        elements.append(caps)
        bin = gst.Bin()
        bin.add(*elements)
        gst.element_link_many(*elements)
        bin.add_pad(gst.GhostPad("src", elements[-1].get_pad("src")))
        return bin        

################################################################################
class Title(Element):
    names = ["title", "titlebar"]
    def __init__(self, location, name, duration, title1, title2, effects):
        Element.__init__(self, location)
        self.name = name
        self.duration = duration
        self.title1 = title1
        self.title2 = title2
        self.effects = effects
        if not(self.title1):
            raise Exception("No title text found.")

    def __str__(self):
        return "%s:%g:%s:%s" % (self.name, dur2flt(self.duration), self.title1, self.title2)

    def get_bin(self, background, duration=None):
        if duration is None:
            duration = self.duration

        elements = [ background.get_bin() ]
        if self.name == "titlebar":
            if self.title1:
                textoverlay = gst.element_factory_make("textoverlay")
                Annotate.add_title(self, textoverlay, self.title1, "top_title", self.config)
                elements.append(textoverlay)
            if self.title2:
                textoverlay = gst.element_factory_make("textoverlay")
                Annotate.add_title(self, textoverlay, self.title2, "bottom_title", self.config)
                elements.append(textoverlay)
        else:
            textoverlay = gst.element_factory_make("textoverlay")
            Annotate.add_title(self, textoverlay, self.title1, "title", self.config)
            elements.append(textoverlay)

        caps        = gst.element_factory_make("capsfilter")
        caps.set_property("caps", self.config.get_video_caps("AYUV"))
        elements.append(caps)
        bin = gst.Bin()
        bin.add(*elements)
        gst.element_link_many(*elements)
        bin.add_pad(gst.GhostPad("src", elements[-1].get_pad("src")))
        return bin
        

################################################################################
class Transition(Element):
    names   = ['fadein', 'fadeout', 'crossfade', 'wipe', ] + transition.smptes + transition.kenburns

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
        elif name in ["wipe"] + transition.smptes:
            self.get_transition_bin = transition.get_smpte_bin
        elif name in transition.kenburns:
            self.get_transition_bin = transition.get_kenburns_bin

    def __str__(self):
        return "%s:%g" % (self.name, dur2flt(self.duration))

    def get_bin(self):
        bin, ctrl = self.get_transition_bin(self.name, self.config, self.duration)
        self.controllers.append(ctrl)
        return bin


################################################################################
class Audio(Element):
    extensions = [ 'ogg', 'mp3', 'wav', 'm4a', 'aac' ]

    def __init__(self, location, filename, track, effects):
        Element.__init__(self, location)
        if not(os.path.exists(filename)):
            raise Exception("Audio file "+filename+" does not exist.")

        self.name     = os.path.basename(filename)
        self.filename = filename
        self.track = track
        self.effects= effects

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
        if self.filename == "silence":
            return Audio.get_silence_bin(self.config)

        bin = gst.Bin()
        elements = []
        for name in [ "filesrc", "decodebin2", "audioconvert", "volume", "capsfilter",  ]:
            elements.append(gst.element_factory_make(name, name))
            exec("%s = elements[-1]" % name)
    
        capsfilter.props.caps = self.config.get_audio_caps()
        filesrc.set_property("location",  self.filename)
        bin.add(*elements)
        filesrc.link(decodebin2)
        audioconvert.link(volume)
        volume.link(capsfilter)
        
        c = gst.Controller(volume, "volume")
        c.set_interpolation_mode("volume", gst.INTERPOLATE_LINEAR)
        if self.fadein:
            c.set("volume", 0,    0.0)
            c.set("volume", self.fadein, 1.0)
        else:
            c.set("volume", 0, 1.0)
            
        if self.fadeout:
            c.set("volume", duration-self.fadeout, 1.0)
            c.set("volume", duration,      0.0)
        else:
            c.set("volume", duration, 1.0)
        self.controllers.append(c)
        
        def on_pad(src_element, pad, data, sink_element):
            sinkpad = sink_element.get_compatible_pad(pad, pad.get_caps())
            pad.link(sinkpad)

        decodebin2.connect("new-decoded-pad", on_pad, audioconvert)
        bin.add_pad(gst.GhostPad("src", capsfilter.get_pad("src")))
        return bin


class Silence(Audio):
    names = [ 'silence' ]

    def __init__(self, location, name, track, duration=-1, config=None):
        Element.__init__(self, location)
        self.name = name
        self.track = track
        self.fadein  = 0
        self.fadeout = 0
        self.effects = []
        self.duration = duration
        self.config=config

    def __str__(self):
        return "%s:%s" % (self.name, self.track,)

    def initialize(self):
        pass

    def get_bin(self, duration=None):
        bin = gst.Bin()
        silence = gst.element_factory_make("audiotestsrc")
        silence.props.wave=4 # silence
        silence.props.volume=0.0
        convert = gst.element_factory_make("audioconvert")
        caps    = gst.element_factory_make("capsfilter")
        caps.props.caps = self.config.get_audio_caps()
        bin.add(silence, convert, caps)
        silence.link(convert)
        convert.link(caps)
        bin.add_pad(gst.GhostPad("video_src", caps.get_pad("src")))
        return bin

class TestVideo(Element):
    names = [ "testvideo", ]
    def __init__(self, location, name, duration, subtitle, pattern, effects=[]):
        Element.__init__(self, location)
        self.name = name
        self.duration = duration
        self.pattern = pattern
        self.subtitle = subtitle
        self.effects = effects
        
    def get_bin(self, background=None, duration=None):
        if duration is None:
            duration = self.duration

        elements = []
        bin = gst.Bin()
        src = gst.element_factory_make("videotestsrc")
        if self.pattern:
            try:
                src.props.pattern = self.pattern
            except:
                raise Exception("Error setting specified test pattern.")
        elements.append(src)
        if self.config["subtitle_type"] == "render" and self.subtitle:
            subtitle = gst.element_factory_make("textoverlay")
            elements.append(subtitle)
            Annotate.add_subtitle(self, subtitle, self.subtitle, self.config)
        caps = gst.element_factory_make("capsfilter")
        caps.props.caps = self.config.get_video_caps("AYUV")
        elements.append(caps)
        bin.add(*elements)
        gst.element_link_many(*elements)
        bin.add_pad(gst.GhostPad("src", elements[-1].get_pad("src")))
        return bin

class Chapter(Element):
    names = [ "chapter", ]
    def __init__(self, location):
        Element.__init__(self, location)

    def __str__(self):
        return "chapter"
    
class Video(Element):
    extensions = [ "avi", "mp4", "mpg", "vob" ]

    def __init__(self, location, filename, duration, subtitle, effects):
        Element.__init__(self, location)
        self.name     = os.path.basename(filename)
        self.filename = filename
        self.duration = duration
        self.subtitle = subtitle
        self.effects  = effects
        
    def initialize(self):
        self.duration = get_duration(self.filename)

    def get_bin(self, background=None, duration=None):
        if duration is None:
            duration = self.duration

        elements = []
        bin = gst.Bin()
        capnum = 1
        for name in [ "filesrc", "decodebin2", "videorate", "capsfilter", "ffmpegcolorspace", "capsfilter", "videoscale", "capsfilter",  ]:
            elements.append(gst.element_factory_make(name))
            if name == "capsfilter":
                exec( "cap"+str(capnum)+"=elements[-1]")
                capnum += 1
            else:
                exec( name + "=elements[-1]")
        
        cap1.props.caps = gst.Caps("video/x-raw-yuv,framerate=(fraction)%d/%d" % (self.config["framerate_numer"], self.config["framerate_denom"]))
        cap2.props.caps = gst.Caps("video/x-raw-yuv,format=(fourcc)AYUV")
        cap3.props.caps = self.config.get_video_caps("AYUV")
        videoscale.props.add_borders = True
        filesrc.props.location = self.filename

        bin.add(*elements)
        gst.element_link_many(*elements[2:])
        filesrc.link(decodebin2)
        
        def on_pad(src_element, pad, data, sink_element):
            sinkpad = sink_element.get_compatible_pad(pad, pad.get_caps())
            if sinkpad:
                pad.link(sinkpad)

        decodebin2.connect("new-decoded-pad", on_pad, elements[2])

        bin.add_pad(gst.GhostPad("src", elements[-1].get_pad("src")))
        return bin




#    elif image[-1] == 'musictitle':
