import Element, gst
import logging, re
log = logging.getLogger(__name__)

class FileLocation():
    def __init__(self, filename, linenum, line):
        self.filename = filename
        self.linenum = linenum
        self.line    = line.replace("\n","")

    def __str__(self):
        return "%s (line %d)" % (self.filename, self.linenum)


class DVDSlideshow():
    def __init__(self, filename):
        self.filename = filename

    def get_pipeline(self, config):
        pipeline = []
        DVDSlideshow.parse_input_file(self.filename, pipeline, config)
        return pipeline

    @staticmethod
    def escape(lines, escapes):
        # replace escaped characters
        for i,e in enumerate(escapes): # replace escapes w/ special ascii
            if type(lines) is str:
                lines = lines.replace("\\"+e, chr(i+1))
            else:
                for j, line in enumerate(fields):
                    lines[j] = line.replace("\\"+e, chr(i+1))
        return lines

    @staticmethod
    def unescape(lines, escapes):
        for i, e in enumerate(escapes): #restore escaped chars
            if type(lines) is str:
                lines = lines.replace(chr(i+1), e)
            else:
                for j, line in enumerate(lines):
                    lines[j] = line.replace(chr(i+1), e)
        return lines
    
        
    @staticmethod
    def parse_input_file(filename, pipeline, config):
        log.info("Parsing file " + filename)
        f = open(filename, "r")
        
        config["input_txtfile_options"] = {}
    
        linenum = 0
        for line in f:
            linenum += 1 
            location = FileLocation(filename, linenum, line)
            
            if line.startswith("include"):
                DVDSlideshow.parse_input_file(DVDSlideshow.parse_key_value(line)[1], pipeline, config)
                continue

            try:
                pipeline.append(DVDSlideshow.parse_line(line, config, location))
            except Exception, e:
                raise
                raise Exception("%s: %s" % (location, str(e)))
        f.close()

    @staticmethod
    def parse_line(rawline, config, location):
        line = rawline.strip()
        
        if not(line):     # check if this is an empty line
            return Element.EmptyLine(location)
        
        if line[0] == "#":  # grab whole line comments as special elements
            return Element.Comment(location, line)

        # Remove trailing comments, but first we need to protect
        # colors of the form #123456 from getting commented out
        line = re.sub(r"(#" + r"[\dA-Fa-f]"*6 + r")", r"\\\g<0>", line) 

        # protect any \# characters from being interpreted as a comment
        line = DVDSlideshow.escape(line, ["#"])

        line = line.split("#", 1)[0] # remove comments

        # Restore escaped # characters
        line = DVDSlideshow.unescape(line, ["#"])

        #if DVDSlideshow.check_theme(line, config):
        #    continue
        
        conf = DVDSlideshow.check_var(line, config, location)
        if conf:
            return conf

        return DVDSlideshow.get_element(line, location)


    @staticmethod
    def parse_key_value(line):
        k,v = map(str.strip, line.split("=",1))
        try:
            v = eval(v)
        except:
            pass
        return k, v
        
    @staticmethod
    def read_theme(filename, config):
        raise Exception("theme not supported yet")

    @staticmethod
    def check_theme(line, config):
        if line.startswith("theme"):
            filename = DVDSlideshow.parse_key_value(line)[1]
            DVDSlideshow.read_theme(filename, config)
            return True
        else:
            return False

    @staticmethod
    def check_var(line, config, location):
        for var in config.vars:
            if(line.replace(" ","").startswith(var+"=")):
                key,val = DVDSlideshow.parse_key_value(line)
                config.set_var(key, val)
                if(key == "transition"):
                    config.set_var(key, DVDSlideshow.get_element(val, location))
                return Element.Config(location,key, val)

    @staticmethod
    def get_element(line, location):
        line = DVDSlideshow.escape(line, ["\\",":"])

        try:
            # split at the first : to allow for different parsing depending
            # on what type of element this is
            element, params = line.split(":", 1) 
        except ValueError: 
            # if there is no colon, still see if we can get something out of
            # default parameters
            element = line
            params  = ""

        # now get the extension
        extension = element.split(".")[-1].lower()
    
        fields = params.split(":") # split parameters into fields

        # restore any escaped characters back
        fields = DVDSlideshow.unescape(fields, ["\\",":"])

        
        if extension in Element.Image.extensions:
            return DVDSlideshow.getImage(location, element, fields)
        elif extension in Element.Video.extensions:
            return DVDSlideshow.getVideo(location, element, fields)
        elif element in Element.Silence.names:
            return DVDSlideshow.getSilence(location, element, fields)
        elif element in Element.Blank.names:
            return DVDSlideshow.getBlank(location, element, fields)
        elif element in Element.Chapter.names:
            return DVDSlideshow.getChapter(location, element, fields)
        elif element in Element.TestVideo.names:
            return DVDSlideshow.getTestVideo(location, element, fields)
        elif extension in Element.Audio.extensions:
            return DVDSlideshow.getAudio(location, element, fields)
        elif element in Element.Transition.names:
            return DVDSlideshow.getTransition(location, element, fields)
        elif element in Element.Title.names:
            return DVDSlideshow.getTitle(location, element, fields)
        elif element in Element.Background.names:
            return DVDSlideshow.getBackground(location, element, fields)
        else:
            raise Exception("Unknown element %s" % (element,))
    

    @staticmethod
    def pop(fields):
        if(fields):
            return fields.pop(0)
        else:
            return ""

    @staticmethod
    def parse_duration(duration, allow_zero=False):
        if duration == "":
            dur = 0
        else:
            try:
                dur = float(duration)
            except:
                raise Exception("Cannot convert duration '%s' to float" % duration)
        if (dur==0) and not(allow_zero):
            raise Exception("Error: duration of zero requested.")
        return int(round(dur * gst.SECOND))

    @staticmethod
    def parse_effects(fields):
        effects = []
        while fields:
            effects.append(Element.Effect(DVDSlideshow.pop(fields), DVDSlideshow.pop(fields)))
        return effects
        
    
    @staticmethod
    def getBackground(location, name, fields):
        duration = DVDSlideshow.parse_duration(DVDSlideshow.pop(fields), allow_zero=True)
        subtitle = DVDSlideshow.pop(fields)
        background = DVDSlideshow.pop(fields)
        effects = DVDSlideshow.parse_effects(fields)
        return Element.Background(location, name, duration, subtitle, background, effects)

    @staticmethod
    def getBlank(location, name, fields):
        duration = DVDSlideshow.parse_duration(DVDSlideshow.pop(fields), allow_zero=True)
        subtitle = DVDSlideshow.pop(fields)
        effects = DVDSlideshow.parse_effects(fields)
        return Element.Blank(location, name, duration, subtitle, effects)
    
    @staticmethod
    def getImage(location, filename, fields):
        duration = DVDSlideshow.parse_duration(DVDSlideshow.pop(fields),allow_zero=True)
        subtitle = DVDSlideshow.pop(fields)
        effects = DVDSlideshow.parse_effects(fields)
        return Element.Image(location, filename, duration, subtitle, effects)

    @staticmethod
    def getVideo(location, filename, fields):
        duration = DVDSlideshow.parse_duration(DVDSlideshow.pop(fields),allow_zero=True)
        subtitle = DVDSlideshow.pop(fields)
        settings = DVDSlideshow.parse_key_values(DVDSlideshow.pop(fields))
        effects = DVDSlideshow.parse_effects(fields)
        return Element.Video(location, filename, duration, subtitle, settings, effects)

    @staticmethod
    def getTitle(location, name, fields):
        duration = DVDSlideshow.parse_duration(DVDSlideshow.pop(fields))
        title1 = DVDSlideshow.pop(fields)
        title2 = DVDSlideshow.pop(fields)
        effects = DVDSlideshow.parse_effects(fields)
        return Element.Title(location, name, duration, title1, title2, effects)

    @staticmethod
    def getTransition(location, name, fields):
        d = DVDSlideshow.pop(fields)
        duration = DVDSlideshow.parse_duration(d)
        effects = DVDSlideshow.parse_effects(fields)
        return Element.Transition(location, name, duration)

    @staticmethod
    def parse_track(track):
        if(track == ""):
            settings = dict(track = 1)
        else:
            try:
                settings = dict(track = int(track))
            except:
                settings = DVDSlideshow.parse_key_values(track)
        return settings

    @staticmethod
    def getAudio(location, filename, fields):
        settings = DVDSlideshow.parse_track(DVDSlideshow.pop(fields))
        effects  = []
        while fields:
            name = DVDSlideshow.pop(fields)
            if(name):
                effects.append(Element.Effect(name, eval(DVDSlideshow.pop(fields))))
            
        return Element.Audio(location, filename, settings, effects)

    @staticmethod
    def getSilence(location, name, fields):
        settings = DVDSlideshow.parse_track(DVDSlideshow.pop(fields))
        effects  = []
        while fields:
            name = DVDSlideshow.pop(fields)
            if(name):
                effects.append(Element.Effect(name, eval(DVDSlideshow.pop(fields))))
        #track = DVDSlideshow.parse_track(DVDSlideshow.pop(fields))
        return Element.Silence(location, name, settings, effects)

    @staticmethod
    def getChapter(location, name, fields):
        return Element.Chapter(location)

    @staticmethod
    def getTestVideo(location, name, fields):
        duration = DVDSlideshow.parse_duration(DVDSlideshow.pop(fields),allow_zero=True)
        subtitle = DVDSlideshow.pop(fields)
        keyvals = DVDSlideshow.parse_key_values(DVDSlideshow.pop(fields))
        pattern = keyvals.get("pattern", "")
        effects = DVDSlideshow.parse_effects(fields)
        return Element.TestVideo(location, name, duration, subtitle, pattern, effects)

    @staticmethod
    def parse_key_values(field):
        kvdict = {}
        kvs = map(str.strip, field.split(";"))
        for kv in kvs:
            if kv:
                key, value = map(str.strip, kv.split("=",1))
                try:
                    kvdict[key] = int(value)
                except ValueError:
                    try:
                        kvdict[key] = float(value)
                    except ValueError:
                        kvdict[key] = value
                    
        return kvdict
