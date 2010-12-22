import os, subprocess, hashlib, time, sys
import logging
import KenBurns

log = logging.getLogger(__name__)

class Progress():
    def initialize(self, caption):
        self.caption = caption
        self.time0   = time.time()
    
    def update(self, i, N):
        n = 40
        p = 100 * i / N
        f = n * p / 100
        sys.stderr.write("  "+self.caption+": |" + "=" * f + ' ' * (n-f)+"| %3d%% (%d/%d)    \r" % (p,i,N))
    def done(self):
        sys.stderr.write("  "+self.caption+": Elapsed Time=%s seconds" % (time.time()-self.time0,))
        sys.stderr.write(" " * 30)
        sys.stderr.write("\n")


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
            

## make both a slideshow_background file and a title_background file
def get_dims(img_file):
    return map(int, cmd('identify -format "%w %h" '+img_file).split())

def crop_img(imgfile, extension, config):
    width,height = get_dims(imgfile)
    img_ratio = 100 * width / height
    #if [ "$do_autocrop_w" -eq 1 ]; then   
    #        # autocrop background image width (width too large)
    #        convert "${bg}" -filter $filtermethod \
    # 			-resize "$sq_to_dvd_pixels" \
    # 			-resize x"$dvd_height" \
    #        			-gravity center \
    # 			-crop "$dvd_width"x"$dvd_height"'+0!+0!' \
    # 			-type TrueColorMatte -depth 8 \
    # 			"$tmpdir"/slideshow_background.ppm
    #elif [ "$do_autocrop_h" -eq 1 ]; then
    #        # autocrop background image height (height too large)
    #        convert "${bg}" -filter $filtermethod \
    # 			-resize "$sq_to_dvd_pixels" \
    # 			-resize "$dvd_width"x \
    #        			-gravity center \
    # 			-crop "$dvd_width"x"$dvd_height"'+0!+0!' \
    # 			-type TrueColorMatte -depth 8 \
    # 			"$tmpdir"/slideshow_background.ppm
    #else
            #don't autorop

    convert = "convert "+imgfile+" -filter "+config["filtermethod"]+"	-resize "+config["sq_to_dvd_pixels"]+" -resize x"+str(config["dvd_height"])+" -bordercolor black -border "+str(config["dvd_width"])+"x240 -gravity center -crop "+str(config["dvd_width"])+"x"+str(config["dvd_height"])+"'+0!+0!' -type TrueColorMatte -depth 8 %s"
    return cmdif(imgfile, config["workdir"], extension, convert)


################################################################################
class Effect():
    def __init__(self, name, param):
        self.name = name
        self.param = param


################################################################################
class Element():
    def __init__(self, location):
        self.location = location
        self.frames_extended = 0

    def initialize(self, prev, next, config):
        self.next=next
        self.prev=prev

    def isa(self, type1):
        return issubclass(self.__class__, eval(type1))

    def _find_background(self):
        if issubclass(self.__class__, Background):
            return self
        elif(self.prev):
            return self.prev._find_background()
        else:
            raise Exception("Cannot find background")

    def __str__(self):
        return self.name

################################################################################
class Image(Element):
    extensions = ['jpg', 'png', 'jpeg' ]
    def __init__(self, location, filename, extension, duration, subtitle, effects):
        Element.__init__(self, location)
        if not(os.path.exists(filename)):
            raise Exception("Image "+filename+" does not exist.")

        self.name      = os.path.basename(filename).replace("."+extension,"")
        self.filename  = filename
        self.extension = extension
        self.duration  = duration
        self.subtitle  = subtitle
        self.effects   = effects
        self.filename_orig = self.filename
        self.effects_orig  = list(effects)
        if(self.duration == 0):
            self.duration = 5000;

    def __str__(self):
        x = "%s:%s:%s" % (self.filename_orig, self.duration/1000, self.subtitle)
        fx = ":".join([ "%s:%s" % (y.name,y.param) for y in self.effects_orig ])
        if(fx):
            x += ":" + fx
        return x

    def update_filename(self, filename):
        self.filename_orig = filename
        self.filename = filename
        self.extension = filename.split(".")[-1]

    def get_images(self, N, config):
        fx = [e.name for e in self.effects]
        if("kenburns" in fx):
            param = self.effects[fx.index("kenburns")].param
            return KenBurns.kenburns(config, param, self.filename, N,Progress())
        else:
            self.create_slide(config)
            return [ (self.filename, N), ]

    def create_slide(self, config):
        # create_slide $file $outfile $transparent
        # does autocropping and compositing over background if required
        bg = self._find_background()

        postprocess = ""
	# postprocessing options:
	# add sepia, black_and_white, old, etc...
	if config["image_postprocess"] == 'shadow' and config["border"] > 0:
            postprocess='( +clone  -background black  -shadow 80x3+5+5 ) +swap -background none -mosaic'

        convert = ("convert -size "+str(config["frame_width"])+"x"+str(config["frame_height"])+" "+self.filename+" -filter "+config["filtermethod"]+" -resize "+config["sq_to_dvd_pixels"]+ " -resize "+str(config["frame_width"])+"x"+str(config["frame_height"]) + " -type TrueColorMatte -depth 8 "+ config["sharpen"] +" "+postprocess+" miff:- | composite -compose src-over -gravity center -type TrueColorMatte -depth 8 - "+bg.filename).replace("%","%%") + " %s"
        self.extension = "ppm"
        self.filename  = cmdif(self.filename, config["workdir"], self.extension, convert)

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
        x = "%s:%s:%s:%s" % (self.name, self.duration/1000, self.subtitle, self.bg)
        return x

    def create_slide(self, config):
        self.extension="ppm"

        if self.bg == "":
            prev_bg = self.prev._find_background()
            self.filename = prev_bg.filename
            self.extension= prev_bg.extension
        elif os.path.exists(self.bg): # if effect is a background file
            self.filename = crop_img(self.bg, self.extension, config)
        else: ## use plain black background with no picture
            convert = "convert -size "+str(config["dvd_width"])+'x'+str(config["dvd_height"])+" xc:"+self.bg+" -type TrueColorMatte -depth 8 %s"
            self.filename = cmdif(None, config["workdir"], self.extension, convert)


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
        return "%s:%s:%s:%s" % (self.name, self.duration/1000, self.title1, self.title2)

    def create_slide(self, config):
        self.extension = "ppm"
        bg = self._find_background()
        fsize = config["title_font_size"]
        fcolor = config["title_font_color"]

	if config["low_quality"] or config["vcd"] or config["output_format"] in ['flv', 'swf', 'mp4', 'mpg']:
            fsize = fsize * config["dvd_height"] / 480
            
	## if background is black & font color is black, change font to white
        if bg.bg == "black" and fcolor == 'black':
            fcolor='white'

        convert = ("convert -size %dx%d xc:transparent -fill '%s' -pointsize %s -gravity Center -font %s -annotate 0 '%s' -type TrueColorMatte -depth 9 miff:- | composite -compose src-over -type TrueColorMatte -depth 8 - %s" % (config["dvd_width"], config["dvd_height"], fcolor, fsize, config["title_font"], self.title1, bg.filename)).replace("%", "%%") + " %s"
        self.filename = cmdif(None, config["workdir"], self.extension, convert)

################################################################################
class Transition(Element):
    names = ['fadein', 'fadeout', 'crossfade', 'wipe' ]

    def __init__(self, location, name, duration):
        Element.__init__(self, location)
        if not(name in Transition.names):
            raise Exception("Unknown transition %s" % name)
        if duration <= 0:
            raise Exception("Transition duration must be a positive number.")
        self.name = name
        self.duration = duration

    def __str__(self):
        return "%s:%s" % (self.name, self.duration/1000)

    def compose(self, imgs0, imgs1, config):
        N = int(config["framerate"] * self.duration / 1000.)

        if len(imgs0) == 0:
            imgs0 = [ self._find_background().filename, N ]
        if len(imgs1) == 0:
            raise Exception("Internal Error: Length of imgs1 sequence is zero")

        # unwrap each sequence into a list of files
        unwrap0 = []
        unwrap1 = []

        for img in imgs0:
            for i in range(img[1]):
                unwrap0.append(img[0])
        for img in imgs1:
            for i in range(img[1]):
                unwrap1.append(img[0])

        if len(unwrap0) != N or len(unwrap1) != N:
            raise Exception("Internal Error Generating Transition. Number of overlapping frames in transition is not equal to %d." % N)

        imgs = []
        progress = Progress()
        progress.initialize(self.name)
        for i, (img0, img1) in enumerate(zip(unwrap0, unwrap1)):
            progress.update(i,N)
            imgs.append((eval("self."+self.name+"(img0, img1, i, N, config)"), 1))
        progress.done()
        return imgs
    
    def crossfade(self, img0, img1, i, N, config):
        compose = ("composite -blend %s %s %s" % (i*100/N, img1, img0,)) + " %s"
        return cmdif([img0,img1], config["workdir"], "ppm", compose)


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

        if self.extension == 'ogg':
            self.check_installed("oggdec", "The vorbis-tools package must be installed to use .ogg audio files.")
        elif self.extension == 'mp3':
            self.check_installed("lame", "The lame package must be installed to use .mp3 audio files.")
        elif self.extension in ['m4a','aac' ]:
            self.check_installed("faad", "The faad package must be installed to use .m4a or .aac audio files.")

        if(self.track > 2):
            raise Exception("ERROR: Only 2 audio tracks supported at this time.  Fix this audio file track number!")
        if(self.track < 1):
            raise Exception("ERROR: Must specify positive and non-zero track number.  Fix this audio file track number!")

        for effect in self.effects:
            if not(effect.name in ["fadein","fadeout"]):
                       raise Exception("ERROR: %s unknown audio effect. 'fadein' and 'fadeout' are only valid effects")
        self.filename_orig = self.filename
        self.effects_orig  = list(effects)

    def __str__(self):
        x = "%s:%s" % (self.filename_orig, self.track)
        fx = ":".join([ "%s:%s" % (y.name,y.param) for y in self.effects_orig ])
        if(fx):
            x += ":" + fx
        return x
        x = "%s:%s" % (self.filename_orig, self.track)


    def check_installed(self, prog, msg):
        it=cmd("which "+prog+" 2> /dev/null")
        if not(it):
            raise Exception("ERROR: '"+prog+"' not found in path." + msg)

    def initialize(self, prev, next, config):
        Element.initialize(self, prev, next, config)
        self.transcode(config)
        self.stats()

        dur = self.duration / 1000.
        fxlen = 0
        for effect in self.effects:
            if effect.param > dur:
                raise Exception("%s time of %s seconds is longer than audio clip duration of %s seconds" % (effect.name, effect.param, dur,))
            fxlen += effect.param
        if(fxlen > dur):
            raise Exception("fadein and fadeout total duration is %s seconds, which is longer than the audio clip of %s seconds." % (fxlen, dur,))

    def stats(self):
        log.info("Getting info on %s" % self.filename)
        txt = cmd("sox "+self.filename+" -n stat 2>&1")
        if txt.find("FAIL") >= 0:
            raise Exception("sox is not compiled with support for %s. '%s'" % (self.extension, txt))
        for line in txt.split("\n"):
            key, val = map(str.strip, line.split(":", 1))
            self.stats = {}
            if(key.lower().startswith("length")):
                self.duration = int(float(val)*1000)
            self.stats[key] = val
            log.debug(" %s : %s" % (key, val,))

    def transcode(self, config):
        if self.extension == "mp3":
            log.info("decoding mp3 audio file %s... be patient..." % self.filename)
            self.extension = "wav"
            ffmpeg = "ffmpeg -i "+self.filename+" -y -vn -ab "+str(config["audio_bitrate"])+"k -f wav -ar "+str(config["audio_sample_rate"])+" -ac 2 %s >> "+config["ffmpeg_out"]+" 2>&1"
            self.filename = cmdif(self.filename, config["workdir"], self.extension, ffmpeg)

#  			fi
#  		elif [ "$suffix" == "m4a" ] || [ "$suffix" == "aac" ] ; then
#  #			myecho "[dvd-slideshow] decoding mp4 audio... be patient."
#  			if [ "$audiosmp" -eq 1 ] ; then
#  				faad -o "$tmpdir/audio$track"_"$audio_index_padded.wav" "$file" &
#  			else
#  				faad -o "$tmpdir/audio$track"_"$audio_index_padded.wav" "$file" 
#  			fi
#  		elif [ "$suffix" == "ogg" ] ; then
#  #			myecho "[dvd-slideshow] decoding ogg audio... be patient."
#  			if [ "$audiosmp" -eq 1 ] ; then
#  				oggdec --quiet -o "$tmpdir/audio$track"_"$audio_index_padded.wav" "${file}" &
#  			else
#  				oggdec --quiet -o "$tmpdir/audio$track"_"$audio_index_padded.wav" "${file}"
#  			fi
#  		elif [ "$suffix" == "wav" ] ; then
#  #			myecho "[dvd-slideshow] processing wav audio... we will splice it later."
#  			cp "${file}" "$tmpdir/audio$track"_"$audio_index_padded.wav"
#  		elif [ "$file" == 'silence' ]; then
#  			if [ "$audiosmp" -eq 1 ] ; then
#  				sox -t raw -s -2 -c 2 -r $audio_sample_rate /dev/zero -t wav -c 2 -r $audio_sample_rate "$tmpdir/audio$track"_"$audio_index_padded.wav" trim 0 1 &
#  			else
#  				sox -t raw -s -2 -c 2 -r $audio_sample_rate /dev/zero -t wav -c 2 -r $audio_sample_rate "$tmpdir/audio$track"_"$audio_index_padded.wav" trim 0 1
#  			fi
        else:
            raise Exception("Unknown audio file format.")


    def trim(self, duration, config):

        if self.extension == "raw":
            header = "-2 -e signed -c 2 -r " + config["audio_sample_rate"]
        else:
            header = ""
        sox = "sox %s %s %s %%s trim 0 %s" % (header, self.filename, header, duration/1000.)
        self.filename = cmdif(self.filename, config["workdir"], self.extension, sox)
        self.duration = duration

    def apply_fx(self, config):

        # I found some "popping" in the audio for some tracks.
        # it turns out that this is caused by audio going
        # too low or too high and getting clipped.
        # reducing the volume a little should help.
        volume="0.95"
        sox = "sox -v %s %s -2 -e signed -c 2 -r %s %%s" % (volume, self.filename, config["audio_sample_rate"])
        if(self.effects):
            fx = [ x.name for x in self.effects]
            if("fadein" in fx):
                sox += " fade t %s" % self.effects[fx.index("fadein")].param
            else:
                sox += " fade t 0"

            if("fadeout" in fx):
                sox += " %s %s" % (self.duration/1000., self.effects[fx.index("fadeout")].param)

        self.filename = cmdif(self.filename, config["workdir"], self.extension, sox)
        self.extension = "raw"
        

class Silence(Audio):
    def __init__(self, location, duration, track=1):
        Element.__init__(self, location)
        self.duration = duration
        self.track = track

    def initialize(self, prev, next, config):
        Element.initialize(self, prev, next, config)
        self.extension = "raw"

        sox = "sox -t raw -e signed -2 -c 2 -r "+str(config["audio_sample_rate"])+" /dev/zero -2 -s -c 2 -r "+str(config["audio_sample_rate"])+ " %s trim 0 "+ str(self.duration/1000.)
        self.filename = cmdif(None, config["workdir"], self.extension, sox)

    def apply_fx(self, config):
        pass
    
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
