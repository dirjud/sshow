import logging, sys, os, subprocess
import gst
import Reader, Config
log = logging.getLogger(__name__)

def check_system():
    for element in [ "gnlcomposition", "kenburns", "videomixer", "textoverlay", "imagefreeze", "alpha", ]:
        if gst.element_factory_find(element) is None:
            raise Exception("Gstreamer element '%s' is not installed. Please install the appropriate gstreamer plugin and try again." % (element,))

        try:
            x = gst.element_factory_make("videotestsrc")
            x.props.foreground_color
        except AttributeError:
            raise Exception("Your gstreamer version is too old. Install version 0.10.31 or newer.")
            

check_system()

def cmd(x):
    log.debug(x)
    p = subprocess.Popen(x, shell=True, stdout=subprocess.PIPE)
    return p.stdout.read()[:-1] # chop off final carriage return

def read_elements(filename, config):
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
    return element.isa("Image") or element.isa("Title") or element.isa("TestVideo") or element.isa("Video") or element.isa("Blank")

def nextSlide(pos, elements):
    for element in elements[pos+1:]:
        if isSlide(element):
            return element
    raise Exception("No next slide")

def prevSlide(pos, elements):
    for element in reversed(elements[:pos]):
        if isSlide(element):
            return element
    raise Exception("No prev slide")

def find_prev_transition(pos, elements):
    """Walks the elements backward starting with element until it
    finds a transition or another slide. If it finds a transition, it
    returns the transition element. If it reaches the beginning or a
    slide, it returns None. This is useful for finding a transition
    between two slides (if one exists)."""
    if pos > 0:
        prev = elements[pos-1]
        if prev.isa("Transition"):
            return prev
        elif isSlide(prev):
            return None
        else:
            return find_prev_transition(pos-1, elements)
    else:
        return None

def find_next_transition(pos, elements):
    """Walks the elements forward starting with element until it
    finds a transition or another slide. If it finds a transition, it
    returns the transition element. If it reaches the end or a
    slide, it returns None. This is useful for finding a transition
    between two slides (if one exists)."""
    if pos+1 < len(elements):
        next = elements[pos+1]
        if next.isa("Transition"):
            return next
        elif isSlide(next):
            return None
        else:
            return find_next_transition(pos+1, elements)
    else:
        return None

def find_next_slide(pos, elements):
    """Walks the elements forward starting with element until it finds
    the next slide. If it finds a slide, it returns it. If it reaches
    the end or a transition, it returns None."""
    if pos+1 < len(elements):
        next = elements[pos+1]
        if isSlide(next):
            return next
        elif next.isa("Transition"):
            return None
        else:
            return find_next_slide(pos+1, elements)
    else:
        return None

def find_prev_transition(pos, elements):
    """Walks elements backward starting with pos until it
    finds a transition or another slide. If it finds a transition, it
    returns the transition element. If it reaches the beginning or a
    slide, it returns None. This is useful for finding a transition
    between two slides (if one exists)."""
    if pos > 0:
        prev = elements[pos-1]
        if prev.isa("Transition"):
            return prev
        elif isSlide(prev):
            return None
        else:
            return find_prev_transition(pos-1, elements)
    else:
        return None

def isNextTransition(pos, elements):
    for element in elements[pos+1:]:
        if isSlide(element):
            return False
        elif element.isa("Transition"):
            return True
    return False

def initialize_elements(elements, config):

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


    
    framerate_numer = 30000 #int(round(config["framerate"] * 100))
    framerate_denom = 1000 # 1001
    config["framerate"] = framerate_numer / float(framerate_denom)
    config["framerate_numer"] = framerate_numer
    config["framerate_denom"] = framerate_denom


    height = config["dvd_height"]
    width = int(round(config["dvd_height"] * config["aspect_ratio_float"]))
    config["width"]  = width
    config["height"] = height

    config["audio_caps"] = "audio/x-raw-int, endianness=(int)1234, signed=(boolean)true, width=(int)16, depth=(int)16, rate=(int)44100, channels=2"

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


    audio_index = {}
    audio_duration = 0
    video_duration = 0
    prev_element = None
    video_element_count  = 0
    for pos, element in enumerate(elements):
        if element.isa("Audio"):
            try:
                audio_index[element.track] += 1
            except KeyError:
                audio_index[element.track] = 0
            element.index = audio_index[element.track]
            
        try:
            next_element = elements[pos+1]
        except:
            next_element = None

        try:
            element.set_config(config)
            element.initialize()
        except Exception, e:
            #raise
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
                    nextSlide(pos, elements)
                except:
                    raise Exception("no next slide found to fadein to!")
                if isNextTransition(pos, elements):
                    raise Exception("Cannot fadein to another transition!")
            elif element.isa("Transition") and not(element.name in [ 'fadein', 'fadeout' ]):
                try:
                    next_slide = nextSlide(pos, elements)
                except:
                    raise Exception("No next slide to "+element.name+" to!")
                try:
                    prev_slide = prevSlide(pos, elements)
                except:
                    raise Exception("No previous slide to "+element.name+" to!")
                if isNextTransition(pos, elements):
                    raise Exception("Cannot use transition "+element.name+" to another transition!")
            elif element.isa("Transition") and element.name == 'fadeout':
                try:
                    prevSlide(pos, elements)
                except:
                    raise Exception("no prevision slide to fadeout from!")
                if isNextTransition(pos, elements):
                    raise Exception("Cannot fadeout to another transition")
    
        except Exception, e:
            raise
            raise Exception("%s: %s" % (element.location, str(e)))

    return dict(audio_duration=audio_duration, video_duration=video_duration, video_element_count=video_element_count)

def print_gnlcomp(comp):
    for element in comp.elements():
        print " start=%3.3g dur=%3.3g %s" % (Element.dur2flt(element.props.start), Element.dur2flt(element.props.duration), element.get_name())

def add_transition(element, comp, start_time, offset1, config):
    dur = element.duration
    
    op = gst.element_factory_make("gnloperation", config.get_unique(element.name))
    op.add(element.get_bin(offset1))
    op.props.start          = start_time - dur/2
    op.props.duration       = dur
    op.props.media_start    = 0
    op.props.media_duration = dur
    op.props.priority       = 0
    comp.add(op)


def get_video_bin(elements, config):
    comp   = gst.element_factory_make("gnlcomposition", "composition")
    bgcomp = gst.element_factory_make("gnlcomposition", "background")
    
    # we will also create the syncronization information necessary to build
    # the audio tracks.
    audio_info = {} # each track will get its own list of audio elements

    start_time = 0
    priority   = 1
    slide_times = []
    chapter_times = []
    prev_transition = None
    slide_dur = 0
    bgsrc = background = None

    def add_bgsrc(bgsrc):
        if bgsrc:
            bg_priority = bgsrc.props.priority + 1
        else:
            bg_priority = 1
        bgsrc = gst.element_factory_make("gnlsource", config.get_unique(background.bg))
        bgsrc.add(background.get_bin())
        bgsrc.props.start = start_time
        bgsrc.props.media_start = 0
        bgsrc.props.priority = bg_priority
        bgcomp.add(bgsrc)
        return bgsrc

    def set_bgdur(bgsrc):
        dur = start_time - bgsrc.props.start 
        # if the background element has a duration, then loop it as
        # necessary to fill in the time.
        while background.duration and dur > background.duration:
            bgsrc.props.duration       = background.duration
            bgsrc.props.media_duration = background.duration
            start = bgsrc.props.start
            bgsrc = add_bgsrc(bgsrc)
            bgsrc.props.start = start + background.duration 
            dur = start_time - bgsrc.props.start
        bgsrc.props.duration       = dur
        bgsrc.props.media_duration = dur
        return bgsrc

    for pos, element in enumerate(elements):
        try:
            if element.__class__ == Element.Background:
                if bgsrc: # the duration on the last background
                    bgsrc = set_bgdur(bgsrc)
                background = element
                element.set_prev_background(background)
                bgsrc = add_bgsrc(bgsrc)

            elif isSlide(element):
                slide_times.append(start_time)
                dur = element.duration
    
                if(prev_transition):
                    dur += prev_transition.duration/2
                    prev_dur = prev_transition.duration/2
                else:
                    prev_dur = 0
    
                next_transition = find_next_transition(pos, elements)

                # if no next transition but a default transition is provided
                # and there is another slide to transition to, then insert
                # the default.
                if not(next_transition) and config["transition"] and find_next_slide(pos, elements):
                    next_transition = config["transition"]
                    next_transition.set_config(config)
                    add_transition(next_transition, comp, start_time+element.duration, dur-next_transition.duration/2, config)
                    
                if(next_transition):
                    offset1 = dur
                    dur += next_transition.duration/2
                    
                prev_transition = next_transition
    
                src = gst.element_factory_make("gnlsource", config.get_unique(element.name))
                src.add(element.get_bin(dur))
                src.props.start          = start_time - prev_dur
                src.props.duration       = dur
                src.props.media_start    = 0
                src.props.media_duration = dur
                src.props.priority       = priority
                comp.add(src)
    
                priority   += 1
                slide_dur = dur
                start_time += element.duration
    
            elif element.isa("Transition"):
                add_transition(element, comp, start_time, slide_dur-element.duration, config)
    
            elif element.isa("Audio"):
                dur   = element.duration
                track = element.track
    
                if not(audio_info.has_key(track)):
                    audio_info[track] = dict(elements=[], starts=[], durations=[])
                    
                audio_info[track]["elements"].append(element)
                audio_info[track]["starts"].append(start_time)
                audio_info[track]["durations"].append(dur)
            
            elif element.isa("Chapter"):
                chapter_times.append(start_time)

        except Exception, e:
            raise
            raise Exception("%s: %s" % (element.location, str(e)))

    video_dur = start_time

    if bgsrc: # the duration on the last background
        bgsrc = set_bgdur(bgsrc)
    else:
        raise Exception("FIX ME: no background specified")
        
    bin = gst.Bin()
    cap1 = gst.element_factory_make("capsfilter")
    cap2 = gst.element_factory_make("capsfilter")
    ident1 = gst.element_factory_make("identity")
    ident2 = gst.element_factory_make("identity")
    ident1.props.single_segment = 1
    ident2.props.single_segment = 1
    mqueue= gst.element_factory_make("multiqueue")
    mqueue.props.max_size_time = 1 * gst.SECOND
    mqueue.props.max_size_bytes   = 0
    mqueue.props.max_size_buffers = 0
    mixer = gst.element_factory_make(config["videomixer"])
    mixer.props.background = "black"
    color = gst.element_factory_make("ffmpegcolorspace")
    caps = gst.element_factory_make("capsfilter")
    cap1.props.caps = config.get_video_caps("AYUV")
    cap2.props.caps = config.get_video_caps("AYUV")
    caps.props.caps = config.get_video_caps("I420")
    bin.add(bgcomp, comp, ident1, ident2, cap1, cap2, mqueue, mixer, color, caps)
    gst.element_link_many(cap1, ident1, mqueue, mixer, color, caps)
    gst.element_link_many(cap2, ident2, mqueue, mixer)

    bin.add_pad(gst.GhostPad("src", caps.get_pad("src")))
    def on_pad(comp, pad, element):
        capspad = element.get_pad("sink")
        pad.link(capspad)
    bgcomp.connect("pad-added", on_pad, cap1)
    comp.connect("pad-added",   on_pad, cap2)

    print "Video Composition:"
    print_gnlcomp(comp)

    print "Background Composition:"
    print_gnlcomp(bgcomp)

    return bin, dict(duration=video_dur, composition=comp, bin=bin, audio_info=audio_info, slide_times=slide_times, chapter_times=chapter_times)

def get_audio_bin(elements, config, info):
    """This will return a gstreamer bin with the requested audio compositions.
    You must have run the get_video_bin() function first as it will setup
    the appropriate timing flags necessary to generate the audio. The 'info'
    parameter is the dictionary returned by get_video_bin() and contains
    the information necessary to process the audio tracks. This will produce
    a bin with as many audio sink pads as tracks requested."""

    audio_info = info["audio_info"]
    audio = gst.Bin("audio_tracks")

    tracks = audio_info.keys()
    tracks.sort()
    info["num_audio_tracks"] = 0
    if len(tracks) == 0:
        audio_info = { 1 : dict( elements=[Element.Silence("generated", "silence", 1, config=config)], starts=[0], durations=[-1] ) }
        tracks = [1]

    for track in tracks:
        elements  = audio_info[track]["elements"]
        starts    = audio_info[track]["starts"]
        durations = audio_info[track]["durations"]

        # Add silence to the beginning if the first audio element does not
        # start at time 0.
        if(starts[0] != 0):
            elements.insert(0, Element.Silence("generated","silence",track, config=config))
            durations.insert(0, starts[0])
            starts.insert(0, 0)

        # Now start playing out the pipeline so we can do the following:
        # 1. Concatenate elements with the same starting time.
        # 2. Calculate the duration of any filler segments (e.g. silence)
        # 3. Clip any elements that are too long.
        # 4. Fill the end of the track with silence if necessary
        elements2 = [  ]
        starts2   = [  ]
        durations2= [  ]

        reached_end_of_video = False
        for pos in range(len(elements)):
            # calculate the position of the next segment
            pos_next = None # None means the next is the end of the pipeline
            for pos2 in range(pos+1, len(elements)):
                if starts[pos2] == starts[pos]: 
                    continue #skip any that will be concat'd to this one
                else:
                    pos_next = pos2
                    break

            # concatenate elements with the same starting time by calculating
            # the 'start' time, which is the adjusted start time
            if (pos == 0) or (starts[pos] != starts[pos-1]):
                # this is the easy case when the audio element is synced
                # directly to a video element
                start = starts[pos] 
            else: 
                # this is the harder case where the audio element needs
                # sycn'd to the end of the previous audio element
                if(durations[pos-1] == -1):
                    # Drop this audio element as it is a filler placed
                    # after a filler.  Only the first filler lives when two
                    # fillers are placed in a row.
                    continue 

                # If we made it here, this audio element needs time
                # shifted (concatened to the end of the previous
                # element), so put its 'start' time at the end of the
                # previous audio element minus any fadeout time on the
                # previous element.
                start = starts[pos-1] + durations[pos-1] - elements[pos-1].fadeout

                # Now make sure this starting time is valid. It is invalid
                # if it is longer than the video sequence or if starts past
                # the next audio element that is sync'd to a video element.
                if pos_next is None:
                    if start > info["duration"]:
                        continue # Drop b/c it starts after the end of video.
                else:
                    if start > starts[pos_next]:
                        continue # Drop b/c it starts after next audio element

            # now let's calculate the correct duration if this is a
            # filler element (e.g. silence). The duration of a filler
            # is either either the end of the video or the start of
            # the next audio.
            if durations[pos] == -1:
                if pos_next is None: 
                    duration = info["duration"] - start
                else:
                    duration = starts[pos_next] - start
            else:
                duration = durations[pos]

            # now let's clip the duration if it is too long
            if pos_next is None:
                if start + duration > info["duration"]:
                    duration = info["duration"] - start
            else:
                if start + duration > info["duration"]:
                    duration = info["duration"] - start
                    reached_end_of_video = True
                
                if start + duration > starts[pos_next]:
                    duration = starts[pos_next] - start

            # now add the element to final audio list
            elements2.append(elements[pos])
            starts2.append(start)
            durations2.append(duration)

            if reached_end_of_video:
                break

            # add silence as filler if necessary
            extra = 0
            if(pos_next is None and pos+1 == len(elements)):
                extra = info["duration"] - start - duration
            elif(pos + 1 == pos_next):
                extra = min(info["duration"] - start - duration,
                            starts[pos_next] - start - duration)
            if extra > 0:
                elements2.append(Element.Silence("generated", "silence", track, config=config))
                starts2.append(start + duration)
                durations2.append(extra)
        
        # now let's build the gnlcomposition for this audio track
        comp = gst.element_factory_make("gnlcomposition")
        priority = 1
        for pos, element in enumerate(elements2):
            dur   = durations2[pos]
            start = starts2[pos]

            src = gst.element_factory_make("gnlsource", config.get_unique(element.name))
            src.add(element.get_bin(dur))
            src.props.start          = start
            src.props.duration       = dur
            src.props.media_start    = 0
            src.props.media_duration = dur
            src.props.priority       = priority
            comp.add(src)
            priority   += 1
    
        # add an audio adder to sum all overlapping tracks
        op = gst.element_factory_make("gnloperation", config.get_unique("audio_adder_track"+str(track)))
        op.add(gst.element_factory_make("adder"))
        op.props.start          = 0
        op.props.duration       = info["duration"]
        op.props.media_start    = 0
        op.props.media_duration = info["duration"]
        op.props.priority       = 0
        comp.add(op)
        bin=gst.Bin()
        bin.add(comp)

        print "Audio Track", track
        print_gnlcomp(comp)
        
        bin = gst.Bin()
        caps  = gst.element_factory_make("capsfilter")
        caps.props.caps = config.get_audio_caps()
        bin.add(comp, caps)
        bin.add_pad(gst.GhostPad("src", caps.get_pad("src")))

        def on_pad(comp, pad, element):
            capspad = element.get_compatible_pad(pad, pad.get_caps())
            pad.link(capspad)
        comp.connect("pad-added", on_pad, caps)
        audio.add(bin)
        audio.add_pad(gst.GhostPad("track"+str(track), bin.get_pad("src")))
        info["num_audio_tracks"] += 1

    return audio

def get_frontend(elements, config):
    video_bin, info = get_video_bin(elements, config)
    audio_bin = get_audio_bin(elements, config, info)
    
    frontend = gst.Bin("frontend")
    frontend.add(video_bin, audio_bin)

    frontend.add_pad(gst.GhostPad("video_src", video_bin.get_pad("src")))
    for pad in audio_bin.pads():
        frontend.add_pad(gst.GhostPad(pad.get_name(), pad))
    return frontend, info

def get_encoder_backend(config, num_audio_tracks):

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
    
    backend = gst.Bin("backend")
    video_caps = gst.element_factory_make("capsfilter")
    video_caps.props.caps = config.get_video_caps("I420")
    video_scale = gst.element_factory_make("videoscale")
    video_caps2 = gst.element_factory_make("capsfilter")

    if 1:
        video_caps2.props.caps = config.get_video_caps("I420")
        video_enc = gst.element_factory_make("ffenc_mpeg4", "encoder")
        video_enc.props.bitrate = config["video_bitrate"] * 1000 * 4
        mux = gst.element_factory_make("mp4mux", "mux")
        extension = "mp4"
        config["ac3"] = False # this mux can't handle ac3
    elif 0:
        video_caps2.props.caps = config.get_video_caps("I420")
        video_enc = gst.element_factory_make("x264enc",    "video_enc")
        video_enc.props.bitrate = config["video_bitrate"]
        mux = gst.element_factory_make("mp4mux", "mux")
        extension = "mp4"
    elif 0:
        video_caps2.props.caps = config.get_video_caps("I420", width=720, height=480)
        video_enc = gst.element_factory_make("ffenc_mpeg2video", "video_enc")
        video_enc.props.bitrate = config["video_bitrate"] * 1000
        mux = gst.element_factory_make("mplex", "mux")
        mux.props.format = 8
        mux.props.mux_bitrate = 9500
        mux.props.vbr = True
        extension = "vob"
    else:
        video_caps2.props.caps = config.get_video_caps("I420", width=720, height=480)
        video_enc = gst.element_factory_make("mpeg2enc",    "video_enc")
        video_enc.props.format = 8 # dvd mpeg-2 for dvdauthor
        video_enc.props.bitrate = config["video_bitrate"]
        mux = gst.element_factory_make("mplex", "mux")
        mux.props.format = 8
        extension = "vob"

    config["outfile"] = config["outdir"]+"/"+config["slideshow_name"]+"."+extension

    mqueue = gst.element_factory_make("multiqueue")
    sink   = gst.element_factory_make("filesink", "sink")
    sink.set_property("location", config["outfile"])

    backend.add(video_caps, video_scale, video_caps2, video_enc, mqueue, mux, sink)
    gst.element_link_many(video_caps, video_scale, video_caps2, video_enc, mqueue, mux, sink)
    backend.add_pad(gst.GhostPad("video_sink", video_caps.get_pad("sink")))

    for i in range(num_audio_tracks):
        audio_ident = gst.element_factory_make("identity")
        audio_ident.props.single_segment = 1
        if config["ac3"]:
            audio_enc = gst.element_factory_make("ffenc_ac3")
        else:
            audio_enc = gst.element_factory_make("lamemp3enc")
        elements = [ audio_ident, audio_enc,  ]
        backend.add(*elements)
        gst.element_link_many(*elements)
        elements[-1].link(mqueue)
        mqueue.link(mux)
        backend.add_pad(gst.GhostPad("audio_sink%d"%i, audio_ident.get_pad("sink")))
    return backend

def get_preview_backend(config, num_audio_tracks):
    backend = gst.Bin("backend")
    #audio_volume = gst.element_factory_make("volume","volume")

    video_caps = gst.element_factory_make("capsfilter")
    video_caps.props.caps = config.get_video_caps("I420")
    mqueue = gst.element_factory_make("multiqueue")
    mqueue.props.max_size_time = 10 * gst.SECOND
    mqueue.props.max_size_bytes   = 0
    mqueue.props.max_size_buffers = 0
    video_sink  = gst.element_factory_make("autovideosink")
    audio_sel = gst.element_factory_make("input-selector")
    audio_sink  = gst.element_factory_make("autoaudiosink")
    backend.add(video_caps, mqueue, video_sink, audio_sel, audio_sink)
    gst.element_link_many(video_caps, mqueue, video_sink)
    gst.element_link_many(audio_sel, mqueue, audio_sink)

    audio_caps = []
    for i in range(num_audio_tracks):
        caps = gst.element_factory_make("capsfilter")
        audio_caps.append(caps)
        caps.props.caps = config.get_audio_caps()
        backend.add(caps)
        caps.link(audio_sel)

    backend.add_pad(gst.GhostPad("video_sink", video_caps.get_pad("sink")))
    for i,sink in enumerate(audio_caps):
        backend.add_pad(gst.GhostPad("audio_sink%d" % (i,), sink.get_pad("sink")))

    return backend

def get_gst_pipeline(frontend, backend):
    pipeline = gst.Pipeline()
    pipeline.add(frontend, backend)
    i = 0
    for pad in frontend.pads():
        if pad.get_name() == "video_src":
            pad.link(backend.get_pad("video_sink"))
        else:
            pad.link(backend.get_pad("audio_sink%d"%i))
            i += 1
    return pipeline

def start(pipeline, eos_cb, err_cb):
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.enable_sync_message_emission()
    def on_message(bus, message, eos_cb, err_cb):
        t = message.type
	if t == gst.MESSAGE_EOS:
            print "EOS"
            eos_cb()
	elif t == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            print "error=", err
            print "debug=", debug
            pipeline.send_event(gst.event_new_eos())
            #err_cb(err, debug)
    bus.connect("message", on_message, eos_cb, err_cb)
    pipeline.set_state(gst.STATE_PLAYING)
    pipeline.get_state() # wait for it to transition

def stop(pipeline):
    pipeline.set_state(gst.STATE_NULL)
    pipeline.get_state() # wait for it to transition


def get_config_to_frontend(input_txtfile=None):
    config = Config.Config()
    config.parse_argv()
        
    if input_txtfile: # override 
        config["input_txtfile"] = input_txtfile

    if not(config.has_key("input_txtfile")):
        return config, None, None
        
    elements = read_elements(config["input_txtfile"], config)
    initialize_elements(elements, config)
    frontend, info = get_frontend(elements, config)

    return config, elements, frontend, info

def get_state(pipeline):
    return pipeline.get_state()[1]

def query_duration(pipeline):
    return pipeline.query_duration(gst.FORMAT_TIME)[0]/float(gst.SECOND)

def query_position(pipeline):
    dur = pipeline.query_position(gst.FORMAT_TIME)[0]
    return dur/float(gst.SECOND)

def fmt_dur(t, show_ms=False):
    hrs,secs=divmod(t, 3600.)
    mins,secs=divmod(secs, 60.)
    if(show_ms):
        return "%02d:%02d:%02d.%03d" % (int(hrs), int(mins), int(secs), int((secs-int(secs))*1000))
    else:
        return "%02d:%02d:%02d" % (int(hrs), int(mins), int(round(secs)))

def reduce_chapters_to(chapter_times, limit):
    import math
    N = len(chapter_times)
    skip = int(math.ceil(len(chapter_times)/float(limit)))
    return chapter_times[::skip]

def dump_xml(info, config):
    f = open(config["outdir"]+"/"+config["slideshow_name"]+".xml", "w")

    if info["chapter_times"]:
        times = list(info["chapter_times"])
    else:
        times = list(info["slide_times"])
    if(times[0] != 0):
        times.insert(0, 0)

    times = reduce_chapters_to(times, limit=99)
    for i, time in enumerate(times):
        times[i] = fmt_dur(time/float(gst.SECOND), show_ms=True)

    f.write('\t<vob chapters="'+ ','.join(times)+'" file="%s" />\n' % config["outfile"])
    f.write('\t<!-- pal="%d" -->\n' % config["pal"])
    f.write('\t<!-- button="%s" -->\n' % "")
    f.write('\t<!-- title="%s" -->\n' % config["slideshow_name"])
    f.close()
