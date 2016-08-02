import os, subprocess, hashlib, time, sys, gst
import logging
import transition, Annotate, KenBurns

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
    try:
        return map(int, commands.getoutput('identify -format "%w %h" '+img_file +" 2> /dev/null").split())
    except:
        print img_file
        raise
    #d = gst.parse_launch("filesrc location="+img_file+" ! decodebin2 name=decoder ! fakesink")
    #d.set_state(gst.STATE_PLAYING)
    #d.get_state() # blocks until state transition has finished
    #caps = d.get_by_name("decoder").src_pads().next().get_caps()[0]
    #return caps["width"], caps["height"]

def get_duration(filename):
    d = gst.parse_launch("filesrc location="+filename+" ! decodebin2 ! fakesink")
    d.set_state(gst.STATE_PLAYING)
    d.get_state() # blocks until state transition has finished
    duration = d.query_duration(gst.Format(gst.FORMAT_TIME))[0]
    d.set_state(gst.STATE_NULL)
    return duration

def dur2flt(dur):
    return dur / float(gst.SECOND)

def render_subtitle(element, elements):
    if hasattr(element, "subtitle") and element.config["subtitle_type"] == "render" and element.subtitle:
        subtitle = gst.element_factory_make("textoverlay")
        elements.append(subtitle)
        Annotate.add_subtitle(element, subtitle, element.subtitle, element.config)

def process_effects(element, duration, elements, custom_config={}):
    #if not(custom_config):
    #    caps = gst.element_factory_make("capsfilter")
    #    elements.append(caps)
    #    caps.set_property("caps", element.config.get_video_caps("AYUV", custom_config))
    #    elements.append(gst.element_factory_make("ffmpegcolorspace"))
    #    #elements.append(gst.element_factory_make("frei0r-filter-bw0r"))
    #    #elements.append(gst.element_factory_make("frei0r-filter-cartoon"))
    #    #elements.append(gst.element_factory_make("frei0r-filter-scale0tilt"))
    #    elements.append(gst.element_factory_make("agingtv"))
    #    elements.append(gst.element_factory_make("ffmpegcolorspace"))
    #    caps = gst.element_factory_make("capsfilter")
    #    elements.append(caps)
    #    caps.set_property("caps", element.config.get_video_caps("AYUV",custom_config))
    

    Annotate.add_annotations(element, duration, elements)
    render_subtitle(element, elements)
    caps = gst.element_factory_make("capsfilter")
    elements.append(caps)
    caps.set_property("caps", element.config.get_video_caps("AYUV", custom_config))
    for gst_element in elements:
        if gst_element.get_name().startswith("kenburns"):
            KenBurns.configure_kenburns(element, gst_element, duration)


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

    def get_bin(self, duration=None, custom_config={}):
        if duration is None:
            duration = self.duration

        self.width, self.height = get_dims(self.filename)

        bin = gst.Bin()
        elements = []
        for name in [ "filesrc", "decodebin2", "ffmpegcolorspace", "capsfilter", "imagefreeze", "kenburns", ]:
            elements.append(gst.element_factory_make(name))
            try:
                exec("%s = elements[-1]" % name)
            except:
                pass

        filesrc.set_property("location",  self.filename)
        capsfilter.set_property("caps", gst.Caps("video/x-raw-yuv,format=(fourcc)AYUV"))
        cap2 = gst.element_factory_make("capsfilter")
        elements.append(cap2)
        cap2.props.caps = self.config.get_video_caps("AYUV", custom_config)

        process_effects(self, duration, elements, custom_config)

        bin.add(*elements)
        filesrc.link(decodebin2)
        gst.element_link_many(*elements[2:])

        def on_pad(src_element, pad, data, sink_element):
            sinkpad = sink_element.get_compatible_pad(pad, pad.get_caps())
            pad.link(sinkpad)

        decodebin2.connect("new-decoded-pad", on_pad, ffmpegcolorspace)
        bin.add_pad(gst.GhostPad("src", elements[-1].get_pad("src")))
        return bin

################################################################################
class Blank(Element):
    names = [ "blank" ]
    def __init__(self, location, name, duration, subtitle, effects):
        Element.__init__(self, location)
        self.name      = name
        self.duration  = duration
        self.subtitle  = subtitle
        self.effects   = effects
        if(self.duration <= 0):
            self.duration = 5.0;

    def __str__(self):
        x = "%s:%g:%s" % (self.name, dur2flt(self.duration), encode(self.subtitle))
        fx = ":".join([ "%s:%s" % (y.name,encode(y.param)) for y in self.effects ])
        if(fx):
            x += ":" + fx
        return x

    def get_bin(self, duration=None):
        bin = gst.Bin()
        elements = []
        for name in [ "videotestsrc", "capsfilter", ]:
            elements.append(gst.element_factory_make(name))
            exec("%s = elements[-1]" % name)

        videotestsrc.props.pattern = "black"
        videotestsrc.props.foreground_color = 0
        videotestsrc.props.background_color = 0
        capsfilter.set_property("caps", self.config.get_video_caps("AYUV"))
        #process_effects(self, duration, elements)

        bin.add(*elements)
        gst.element_link_many(*elements)
        bin.add_pad(gst.GhostPad("src", elements[-1].get_pad("src")))
        return bin



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
        self.image = None
        if(os.path.exists(self.bg)):
            self.image = Image(location, self.bg, duration, subtitle, effects)
        elif(self.bg[0] == "#"):
            if(len(self.bg) != 7):
                raise Exception("Unknown color '%s'" % self.bg)
        elif(self.bg in Background.colors):
            pass
        else:
            raise Exception("Background color/image '%s' is unkonwn." % self.bg)

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
        elif(self.image):
            self.image.set_config(self.config)
            bin = self.image.get_bin(duration, dict(border=0))
            return bin
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
        caps = gst.element_factory_make("capsfilter")
        caps.props.caps = self.config.get_video_caps("AYUV", dict(border=0))
        elements.append(caps)
        process_effects(self, self.duration, elements, dict(border=0))
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

    def get_bin(self, duration=None):
        if duration is None:
            duration = self.duration

        src = gst.element_factory_make("videotestsrc")
        src.props.pattern = "black"
        src.props.foreground_color = 0;
        src.props.background_color = 0;
        caps= gst.element_factory_make("capsfilter")
        caps.props.caps = self.config.get_video_caps("AYUV")
        elements = [src, caps]

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

        process_effects(self, duration, elements)

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

    def get_bin(self, start1):
        bin, ctrl = self.get_transition_bin(self.name, self.config, self.duration, start1)
        self.controllers.append(ctrl)
        return bin


################################################################################
class Audio(Element):
    extensions = [ 'ogg', 'mp3', 'wav', 'm4a', 'aac' ]

    def __init__(self, location, filename, settings, effects):
        Element.__init__(self, location)
        if filename != "silence" and not(os.path.exists(filename)):
            raise Exception("Audio file "+filename+" does not exist.")

        self.name     = os.path.basename(filename)
        self.filename = filename
        self.track = settings["track"]
        self.effects= effects
        self.settings = settings
        if self.settings.has_key("start"):
            self.start = int(self.settings["start"] * gst.SECOND)
        else:
            self.settings["start"] = 0
            self.start = 0

        if self.settings.has_key("duration"):
            self.duration = int(self.settings["duration"] * gst.SECOND)
        else:
            self.settings["duration"] = -1

        if self.settings.has_key("method"):
            self.method = self.settings["method"]
        else:
            self.method = "concatenate"
            self.settings["method"] = "concatenate"

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
        x = "%s:track=%s;start=%s;duration=%s;method=%s" % (self.name, self.track, self.settings["start"], self.settings["duration"], self.settings["method"])
        fx = ":".join([ "%s:%s" % (y.name,y.param) for y in self.effects ])
        if(fx):
            x += ":" + fx
        return x


    def initialize(self):
        try:
            if(self.duration < 0):
                self.duration = get_duration(self.filename) - self.start
        except:
            self.duration = get_duration(self.filename) - self.start

    def get_bin(self, duration=None):
        if self.filename == "silence":
            return Audio.get_silence_bin(self.config)

        bin = gst.Bin()
        elements = []
        for name in [ "filesrc", "decodebin2", "audioconvert", "audioresample", "capsfilter", "volume",  ]:
            elements.append(gst.element_factory_make(name, name))
            exec("%s = elements[-1]" % name)
    
        capsfilter.props.caps = self.config.get_audio_caps()
        caps2=gst.element_factory_make("capsfilter")
        caps2.props.caps = self.config.get_audio_caps()
        elements.append(caps2)
        filesrc.set_property("location",  self.filename)
        bin.add(*elements)
        filesrc.link(decodebin2)
        gst.element_link_many(*elements[2:])
        
        if(self.settings.has_key("volume")):
            vol = self.settings["volume"]
        else:
            vol = 1.0
        print "vol=",vol, " settings=",self.settings

        c = gst.Controller(volume, "volume")
        c.set_interpolation_mode("volume", gst.INTERPOLATE_LINEAR)
        if self.fadein:
            c.set("volume", self.start,    0.0)
            c.set("volume", self.start+self.fadein, vol)
        else:
            c.set("volume", 0, vol)
            
        if self.fadeout:
            c.set("volume", duration-self.fadeout, vol)
            c.set("volume", duration,      0.0)
        else:
            c.set("volume", duration, vol)
        self.controllers.append(c)
        
        def on_pad(src_element, pad, data, sink_element):
            sinkpad = sink_element.get_compatible_pad(pad, pad.get_caps())
            pad.link(sinkpad)

        decodebin2.connect("new-decoded-pad", on_pad, audioconvert)
        bin.add_pad(gst.GhostPad("src", elements[-1].get_pad("src")))
        return bin


class Silence(Audio):
    names = [ 'silence' ]

    def __init__(self, location, name, settings, effects, config=None):
        Audio.__init__(self, location, name, settings, effects)
        self.name = name
        self.config=config

    def __str__(self):
        x = "%s:track=%s;duration=%s" % (self.name, self.track, self.settings["duration"])
        return x

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
        caps = gst.element_factory_make("capsfilter")
        caps.props.caps = self.config.get_video_caps("AYUV")
        elements.append(caps)
        process_effects(self, duration, elements)
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
    extensions = [ "avi", "mp4", "mpg", "vob", "mts" ]

    def __init__(self, location, filename, duration, subtitle, settings, effects):
        Element.__init__(self, location)
        self.name     = os.path.basename(filename)
        self.filename = filename
        self.duration = duration
        self.subtitle = subtitle
        self.effects  = effects
        self.settings = settings
        if(self.settings.has_key("start")):
            self.start = int(self.settings["start"] * gst.SECOND)
        else:
            self.start = 0
        
    def initialize(self):
        if not(self.duration):
            try:
                self.duration = get_duration(self.filename)
            except:
                log.warn("Cannot get duration of video file %s. You must manually specify the duration." % self.filename)
                self.duration = 5 * gst.SECOND

    def get_bin(self, background=None, duration=None):
        if duration is None:
            duration = self.duration

        self.width = self.config["width"]
        self.height = self.config["height"]
        elements = []
        bin = gst.Bin()
        capnum = 1
        for name in [ "filesrc", "decodebin2", "videorate", "capsfilter", "ffmpegcolorspace", "capsfilter", "kenburns", "capsfilter",  ]:
            elements.append(gst.element_factory_make(name))
            if name == "capsfilter":
                exec( "cap"+str(capnum)+"=elements[-1]")
                capnum += 1
            else:
                exec( name + "=elements[-1]")
        
        cap1.props.caps = gst.Caps("video/x-raw-yuv,framerate=(fraction)%d/%d" % (self.config["framerate_numer"], self.config["framerate_denom"]))
        cap2.props.caps = gst.Caps("video/x-raw-yuv,format=(fourcc)AYUV")
        cap3.props.caps = self.config.get_video_caps("AYUV")
        filesrc.props.location = self.filename
        process_effects(self, duration, elements)
        bin.add(*elements)
        gst.element_link_many(*elements[2:])
        filesrc.link(decodebin2)
        
        def on_pad(src_element, pad, data, sink_element):
            print pad
            sinkpad = sink_element.get_compatible_pad(pad, pad.get_caps())
            if sinkpad:
                pad.link(sinkpad)

        decodebin2.connect("new-decoded-pad", on_pad, elements[2])

        bin.add_pad(gst.GhostPad("src", elements[-1].get_pad("src")))
        #bin.add_pad(gst.GhostPad("audio_src", audio_elements[-1].get_pad("src")))
        return bin

        #src1 = gst.element_factory_make("gnlsource")
        #src1.add(bin)
        #src1.set_property("start",          0)
        #src1.set_property("duration",       duration)
        #src1.set_property("media-start",    self.start)
        #src1.set_property("media-duration", duration)
        ##src1.set_property("priority",       priority)
        #
        #src1.add_pad(gst.GhostPad("src", elements[-1].get_pad("src")))
        #return src1
