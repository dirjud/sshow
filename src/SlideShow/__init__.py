import Reader, Config
import gst
import logging, sys, os, subprocess
log = logging.getLogger(__name__)

def cmd(x):
    log.debug(x)
    p = subprocess.Popen(x, shell=True, stdout=subprocess.PIPE)
    return p.stdout.read()[:-1] # chop off final carriage return

def check_system():
    #checkforprog convert
    progver=cmd("convert -help | head -n 1 | awk '{ print $3 }'")
    log.debug("Found ImageMagick version " + progver)
    it=cmd("which convert 2> /dev/null")
    if not(it): # no convert
        raise Exception("ERROR:  no ImageMagick found for audio processing. You need to download and install ImageMagick. http://ImageMagick.sourceforge.net")
    
    # #checkforprog dvdauthor
    # progver=cmd("dvdauthor -h 2>&1 | head -n 1 | awk '{ print $3 }'")
    # log.debug("Found dvdauthor version " + progver)
    # it=cmd("which dvdauthor 2> /dev/null")
    # if not(it): # no dvdauthor
    #     raise Exception("ERROR:  no dvdauthor found for audio processing. You need to download and install dvdauthor. http://dvdauthor.sourceforge.net")

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
    framerate_denom = 1001
    config["framerate"] = framerate_numer / float(framerate_denom)

    height = config["dvd_height"]
    width = int(round(config["dvd_height"] * config["aspect_ratio_float"]))
    config["caps"] = gst.Caps("video/x-raw-yuv,width=%d,height=%d,framerate=(fraction)%d/%d,format=(fourcc)I420" % (width, height, framerate_numer, framerate_denom))
    config["width"]  = width
    config["height"] = height

    config["audio_caps"] = gst.Caps("audio/x-raw-int, endianness=(int)1234, signed=(boolean)true, width=(int)16, depth=(int)16, rate=(int)44100")

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

        element.link(prev_element, next_element)
        element.set_config(config)

        try:
            element.initialize()
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

    #print "Audio Duration:", audio_duration
    #print "Video Duration:", video_duration
    return dict(audio_duration=audio_duration, video_duration=video_duration, video_element_count=video_element_count)

def get_video_composition(elements, config):
    comp = gst.element_factory_make("gnlcomposition", "video_composition")

    start_time = 0
    priority = 1
    for element in elements:
        if isSlide(element):
            dur = element.duration

            prev_transition = find_prev_transition(element)
            if(prev_transition):
                dur += prev_transition.duration/2
                prev_dur = prev_transition.duration/2
            else:
                prev_dur = 0

            next_transition = find_next_transition(element)
            if(next_transition):
                dur += next_transition.duration/2

            src = gst.element_factory_make("gnlsource")
            src.add(element.get_bin(dur))
            src.props.start          = start_time - prev_dur
            src.props.duration       = dur
            src.props.media_start    = 0
            src.props.media_duration = dur
            src.props.priority       = priority
            comp.add(src)

            priority   += 1
            start_time += element.duration

        elif element.__class__ == Element.Transition:
            dur = element.duration

            op = gst.element_factory_make("gnloperation")
            op.add(element.get_bin())
            op.props.start          = start_time - dur/2
            op.props.duration       = dur
            op.props.media_start    = 0
            op.props.media_duration = dur
            op.props.priority        = 0
            comp.add(op)
            
    return comp, dict(duration=start_time)

def get_silence(config):
    #bin = gst.Bin()
    silence = gst.element_factory_make("audiotestsrc")
    silence.props.wave=4 # silence
    silence.props.volume=0.0
    #caps    = gst.element_factory_make("capsfilter")
    #caps.props.caps = gst.Caps(config["audio_caps"])
    #bin.add(silence, caps)
    #silence.link(caps)
    #bin.add_pad(gst.GhostPad("src", caps.get_pad("src")))
    #return bin
    return silence

def get_audio_composition(elements, config, video_info):
    comp = gst.element_factory_make("gnlcomposition", "audio_composition")
    #comp = video_info["composition"]

    start_time = 0
    priority   = 1
    done = False
    for element in elements:
        if element.__class__ == Element.Audio:
            dur = element.duration

            # pull the song back in time based on any fadein requests
            start_time = max(0, start_time-element.fadein)

            if(start_time + dur > video_info["duration"]):
                dur = video_info["duration"] - start_time
                done = True

            src = gst.element_factory_make("gnlsource")
            src.add(element.get_bin(dur))
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

    # fill any remaining time with silence
    if(start_time < video_info["duration"]):
        dur = video_info["duration"] - start_time
        print "creating ", dur, " silence at time ", start_time
        src = gst.element_factory_make("gnlsource")
        silence = get_silence(config)
        src.add(silence)
        src.props.start          = start_time
        src.props.duration       = dur
        src.props.media_start    = 0
        src.props.media_duration = dur
        src.props.priority       = priority
        comp.add(src)
        start_time += dur
        
    # Add an audio mixer to mix any fades
    op = gst.element_factory_make("gnloperation")
    op.add(gst.element_factory_make("adder"))
    op.props.start          = 0
    op.props.duration       = start_time
    op.props.media_start    = 0
    op.props.media_duration = start_time
    op.props.priority       = 0
    comp.add(op)
    
    return comp, dict(duration=start_time)

def get_frontend(elements, config):
    video_comp, video_info = get_video_composition(elements, config)
    audio_comp, audio_info = get_audio_composition(elements, config, video_info)
    #print "video_info", video_info
    #print "audio_info", audio_info

    video_caps = gst.element_factory_make("capsfilter")
    audio_caps = gst.element_factory_make("capsfilter")
    video_caps.props.caps = gst.Caps(config["caps"])
    audio_caps.props.caps = gst.Caps(config["audio_caps"])

    frontend = gst.Bin("frontend")
    frontend.add(video_comp, audio_comp, video_caps, audio_caps)

    def on_pad(comp, pad, caps):
        capspad = caps.get_compatible_pad(pad, pad.get_caps())
        if capspad:
            pad.link(capspad)
        else:
            print "pad caps", str(pad.get_caps())
            raise Exception("Cannot find capabilible pads")
    video_comp.connect("pad-added", on_pad, video_caps)
    audio_comp.connect("pad-added", on_pad, audio_caps)
    frontend.add_pad(gst.GhostPad("video_src", video_caps.get_pad("src")))
    frontend.add_pad(gst.GhostPad("audio_src", audio_caps.get_pad("src")))
    return frontend


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
    
    backend = gst.Bin("backend")
    
    video_caps  = gst.element_factory_make("capsfilter")
    video_ident = gst.element_factory_make("identity")
    video_ident.props.single_segment = 1
    if 1:
        video_enc = gst.element_factory_make("ffenc_mpeg4", "encoder")
        video_enc.props.bitrate = config["video_bitrate"] * 1000
        mux = gst.element_factory_make("mp4mux", "mux")
    elif 1:
        video_enc = gst.element_factory_make("x264enc",    "video_enc")
        video_enc.props.bitrate = config["video_bitrate"]
        mux = gst.element_factory_make("mp4mux", "mux")
    else:
        video_enc = gst.element_factory_make("mpeg2enc",    "video_enc")
        video_enc.props.format = 8
        video_enc.props.bitrate = config["video_bitrate"]
        mux = gst.element_factory_make("mplex", "mux")

    audio_caps  = gst.element_factory_make("capsfilter")
    audio_ident = gst.element_factory_make("identity")
    audio_ident.props.single_segment = 1
    audio_enc = gst.element_factory_make("lamemp3enc", "audio_enc")

    sink      = gst.element_factory_make("filesink", "sink")
    sink.set_property("location", config["outdir"]+"/"+config["slideshow_name"]+".mp4")

    backend.add(video_caps, video_ident, video_enc, audio_caps, audio_ident, audio_enc, mux, sink)
    gst.element_link_many(video_caps, video_ident, video_enc, mux)
    gst.element_link_many(audio_caps, audio_ident, audio_enc, mux)
    mux.link(sink)
    backend.add_pad(gst.GhostPad("video_sink", video_caps.get_pad("sink")))
    backend.add_pad(gst.GhostPad("audio_sink", audio_caps.get_pad("sink")))
    return backend

def get_preview_backend(config):
    backend = gst.Bin("backend")
    video_queue = gst.element_factory_make("queue")
    audio_volume = gst.element_factory_make("volume","volume")
    audio_queue = gst.element_factory_make("queue")
    video_sink  = gst.element_factory_make("autovideosink")
    audio_sink  = gst.element_factory_make("autoaudiosink")

    backend.add(video_queue, audio_volume, audio_queue, video_sink, audio_sink)
    video_queue.link(video_sink)
    audio_volume.link(audio_queue)
    audio_queue.link(audio_sink)
    backend.add_pad(gst.GhostPad("video_sink", video_queue.get_pad("sink")))
    backend.add_pad(gst.GhostPad("audio_sink", audio_volume.get_pad("sink")))
    return backend

def get_gst_pipeline(frontend, backend):
    pipeline = gst.Pipeline()
    pipeline.add(frontend, backend)
    frontend.get_pad("video_src").link(backend.get_pad("video_sink"))
    frontend.get_pad("audio_src").link(backend.get_pad("audio_sink"))
    return pipeline

def start(pipeline, eos_cb, err_cb):
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    def on_message(bus, message):
        t = message.type
	if t == gst.MESSAGE_EOS:
            eos_cb()
	elif t == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            err_cb(err, debug)
    bus.connect("message", on_message)
    pipeline.set_state(gst.STATE_PLAYING)
    pipeline.get_state() # wait for it to transition

def stop(pipeline):
    pipeline.set_state(gst.STATE_NULL)
    pipeline.get_state() # wait for it to transition


def get_config_to_frontend(input_txtfile=None):
    check_system()
    config = Config.Config()
    config.parse_argv()
        
    if input_txtfile: # override 
        config["input_txtfile"] = input_txtfile

    if not(config.has_key("input_txtfile")):
        return config, None, None
        
    elements = read_elements(config["input_txtfile"], config)
    initialize_pipeline(elements, config)
    frontend = get_frontend(elements, config)

    return config, elements, frontend

def get_state(pipeline):
    return pipeline.get_state()[1]

def query_duration(pipeline):
    return pipeline.query_duration(gst.FORMAT_TIME)[0]/float(gst.SECOND)

def query_position(pipeline):
    dur = pipeline.query_position(gst.FORMAT_TIME)[0]
    return dur/float(gst.SECOND)

def fmt_dur(t):
    hrs,secs=divmod(t, 3600)
    mins,secs=divmod(secs, 60)
    return "%02d:%02d:%02d" % (int(hrs), int(mins), int(round(secs)))
