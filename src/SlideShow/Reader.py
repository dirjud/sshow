import Element
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
    def parse_input_file(filename, pipeline, config):
        log.info("Parsing file " + filename)
        f = open(filename, "r")
        
        config["input_txtfile_options"] = {}
    
        linenum = 0
        for line in f:
            linenum += 1 
            location = FileLocation(filename, linenum, line)
            
            line = re.sub(r"(#" + r"[\dA-Fa-f]"*6 + r")", r"\\\g<0>", line) # protect colors from getting commented out

            if line.startswith("include"):
                DVDSlideshow.parse_input_file(DVDSlideshow.parse_key_value(line)[1], pipeline, config)
                continue

            try:
                pipeline.append(DVDSlideshow.parse_line(line, config, location))
            except Exception, e:
                raise
                #raise Exception("%s: %s" % (location, str(e)))
        f.close()

    @staticmethod
    def parse_line(rawline, config, location):
        line = rawline.strip()
        
        if not(line):     # check if this is an empty line
            return Element.EmptyLine(location)
        
        if line[0] == "#":  # remove comments
            return Element.Comment(location, line)

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
            if(line.startswith(var)):
                key,val = DVDSlideshow.parse_key_value(line)
                config.set_var(key, val)
                return Element.Config(location,key, val)

    @staticmethod
    def get_element(line, location):
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

        ## this is a hack to escape background colors that start with #
        #if element == "background":
        #    fields = map(str.strip, params.split(":"))
        #    if(len(fields)>=3) and fields[2] and fields[2][0] == "#":
        #        fields[2] = "\\"+fields[2]
        #    params = ":".join(fields)

        # replace escaped characters
        escapes = ["\\", "#", ":"]
        for i,e in enumerate(escapes): # replace escaped characters w/ special ascii
            params = params.replace("\\"+e, chr(i+1))
        else:
            params = params.split("#", 1)[0] # remove comments
    
        fields = params.split(":") # split parameters into fields
    
        for i, e in enumerate(escapes): # restore escaped chars (no longer escaped)
            for j, field in enumerate(fields):
                fields[j] = field.replace(chr(i+1), e)
    
        if extension in Element.Image.extensions:
            return DVDSlideshow.getImage(location, element, extension, fields)
        elif extension in Element.Audio.extensions:
            return DVDSlideshow.getAudio(location, element, extension, fields)
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
            dur_ms = 0
        else:
            try:
                dur_ms = int(round(float(duration)*1000))
            except:
                raise Exception("Cannot convert duration '%s' to float" % duration)
        if (dur_ms==0) and not(allow_zero):
            raise Exception("Error: duration of zero requested.")
        return dur_ms

    @staticmethod
    def getBackground(location, name, fields):
        duration = DVDSlideshow.parse_duration(DVDSlideshow.pop(fields), allow_zero=True)
        subtitle = DVDSlideshow.pop(fields)
        background = DVDSlideshow.pop(fields)
        return Element.Background(location, name, duration, subtitle, background)

    
    @staticmethod
    def getImage(location, filename, extension, fields):
        duration = DVDSlideshow.parse_duration(DVDSlideshow.pop(fields),allow_zero=True)
        subtitle = DVDSlideshow.pop(fields)
        effects = []
        while fields:
            effects.append(Element.Effect(DVDSlideshow.pop(fields), DVDSlideshow.pop(fields)))

        return Element.Image(location, filename, extension, duration, subtitle, effects)
    
    @staticmethod
    def getTitle(location, name, fields):
        duration = DVDSlideshow.parse_duration(DVDSlideshow.pop(fields))
        title1 = DVDSlideshow.pop(fields)
        title2 = DVDSlideshow.pop(fields)
        return Element.Title(location, name, duration, title1, title2)

    @staticmethod
    def getTransition(location, name, fields):
        d = DVDSlideshow.pop(fields)
        duration = DVDSlideshow.parse_duration(d)
        return Element.Transition(location, name, duration)

    @staticmethod
    def getAudio(location, filename, extension, fields):
        track = DVDSlideshow.pop(fields)
        if(track == ""):
            track = 1
        else:
            try:
                track = int(track)
            except:
                raise Exception("Track is not an integer")

        effects = []
        while fields:
            name = DVDSlideshow.pop(fields)
            if(name):
                effects.append(Element.Effect(name, eval(DVDSlideshow.pop(fields))))
            
        return Element.Audio(location, filename, extension, track, effects)

