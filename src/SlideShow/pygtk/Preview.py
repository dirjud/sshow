import gtk, gobject, gst, time
import SlideShow

################################################################################
class Preview(object):
    def __init__(self):
        self.builder = builder = gtk.Builder()
        path =  "/".join(__file__.split("/")[:-1])
        self.builder.add_from_file(path + "/preview.glade")
        self.preview_window = self.builder.get_object("preview_window")
        self.top =  self.builder.get_object("preivew_top")
        self.top.connect("key_press_event", self.on_key_press)

        self.buttons = []
        for name in ["first", "previous", "play", "next", "last", "fullscreen", "volume" ]:
            button = self.builder.get_object("button_"+name)
            button.connect("clicked", eval("self.on_"+name+"_clicked"))
            exec("self."+name+"_button = button")
            self.buttons.append(button)
        self.preview_status = self.builder.get_object("preview_status")
        self.slider = self.builder.get_object("scale_position")
        self.slider.connect("change-value", self.on_slider)
        self.timer    = None
        self.pipeline = None
        self.backend  = None
        self.config   = None
        self.init()
    
    def set_size(self, width, height):
        self.preview_window.set_size_request(width, height)

    def init(self):
        self.EOS      = False
        self.duration = None

    def on_key_press(self, widget, event):
        key = gtk.gdk.keyval_name(event.keyval)
        print key
        if(key in ["space",]):
            self.on_play_clicked()
        elif(key.lower() == "f"):
            self.on_fullscreen_clicked()
        else:
            return True
        return False

    def on_slider(self, slider, evt, position):
        if evt == gtk.SCROLL_JUMP:
            self.EOS = False
            self.seek(position)
        elif evt == gtk.SCROLL_PAGE_FORWARD:
            self.on_next_clicked()
        elif evt == gtk.SCROLL_PAGE_BACKWARD:
            self.EOS = False
            self.on_previous_clicked()
        else:
            print position, self.slider.get_value()

    def on_fullscreen_clicked(self, *args):
        self.preview_window.fullscreen()

    def on_volume_clicked(self, *args):
        print args

    def on_first_clicked(self, *args):
        self.EOS = False
        self.seek(0)

    def on_previous_clicked(self, *args):
        self.EOS = False
        pos = self.query_position()
        self.seek(max(0,pos-10.0))

    def on_play_clicked(self, *args):
        if not(self.pipeline):
            return

        state = self.get_state()
        if(state == gst.STATE_PLAYING):
            self.pause()
        elif(self.EOS and state == gst.STATE_PAUSED):
            self.EOS = False
            self.seek(0)
            self.play()
        else:
            self.play()

    def on_next_clicked(self, *args):
        pos = self.query_position()
        self.seek(min(self.duration, pos+10.0))

    def on_last_clicked(self, *args):
        self.seek(self.duration)

    def get_top(self):
        return self.builder.get_object("preivew_top")

    def on_message(self, bus, message):
        t = message.type
	if t == gst.MESSAGE_EOS:
            self.EOS = True
            self.pipeline.set_state(gst.STATE_PAUSED)
            gobject.idle_add(self.update_gui_state)
	elif t == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
	    print "Error: %s" % err, debug
	    self.pipeline.set_state(gst.STATE_PAUSED)
            gobject.idle_add(self.update_gui_state)

    def on_sync_message(self, bus, message):
        #print "on_sync_message", message
	if message.structure is None:
            return
	message_name = message.structure.get_name()
	if message_name == "prepare-xwindow-id":
            imagesink = message.src
	    imagesink.set_property("force-aspect-ratio", True)
	    gtk.gdk.threads_enter()
	    imagesink.set_xwindow_id(self.preview_window.window.xid)
	    gtk.gdk.threads_leave()
            
    def set_frontend(self, frontend, config):
        self.stop()
        self.init()
        self.config   = config
        self.frontend = frontend
        if(self.frontend):
            self.backend  = SlideShow.get_preview_backend(self.config)
            self.pipeline = SlideShow.get_gst_pipeline(self.frontend, self.backend)
    
            bus = self.pipeline.get_bus()
            bus.add_signal_watch()
            bus.enable_sync_message_emission()
            bus.connect("message", self.on_message)
            bus.connect("sync-message::element", self.on_sync_message)
        else:
            self.backend  = None
            self.pipeline = None
            self.update_gui_state()

    def play(self, *args):
        self.pipeline.set_state(gst.STATE_PLAYING)
        if self.timer is None:
            self.timer = gobject.timeout_add(1000, self.update_gui_state)
        self.update_gui_state()

    def seek(self, position):
        pos = max(0, min(self.duration, position))
        self.pipeline.seek_simple(gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH, int(round(pos * gst.SECOND)))
        gobject.idle_add(self.update_gui_state)

    def pause(self, *args):
        self.pipeline.set_state(gst.STATE_PAUSED)
        self.update_gui_state()

    def update_gui_state(self):
        if not(self.pipeline):
            self.play_button.get_child().set_from_stock(gtk.STOCK_MEDIA_PLAY, gtk.ICON_SIZE_BUTTON)
            for button in self.buttons:
                button.set_sensitive(False) 
                self.slider.set_sensitive(False)
                self.update_time(0,0)
            return False 

        for button in self.buttons:
            button.set_sensitive(True) 
        self.slider.set_sensitive(True)

        state = self.get_state()
        if(state in [ gst.STATE_NULL,  gst.STATE_READY ]):
            self.pipeline.set_state(gst.STATE_PAUSED)
            state = self.get_state()
            if(state != gst.STATE_PAUSED):
                raise Exception("Cannot set pipeline to PAUSED state")
            
        if(state == gst.STATE_PLAYING):
            self.play_button.get_child().set_from_stock(gtk.STOCK_MEDIA_PAUSE, gtk.ICON_SIZE_BUTTON)
        else:
            self.play_button.get_child().set_from_stock(gtk.STOCK_MEDIA_PLAY, gtk.ICON_SIZE_BUTTON)
        
        if self.duration == None:
            try:
                self.duration = self.pipeline.query_duration(gst.FORMAT_TIME)[0]/float(gst.SECOND) - 1.0/self.config["framerate"]/2
                self.slider.set_range(0,self.duration)
            except gst.QueryError:
                log.warn("Can't query stream duration")

        self.update_time(self.query_position(), self.duration)
        
        if state == gst.STATE_PLAYING:
            # return TRUE when PLAYING so that the 1 second timer
            # continues to tick and update the state.
            return True
        else:
            self.timer = None
            return False
        return 

    def query_position(self):
        if self.pipeline:
            try:
                return self.pipeline.query_position(gst.FORMAT_TIME)[0]/float(gst.SECOND)
            except gst.QueryError:
                log.warn("Failed querying current position")
                return 0
        else:
            return 0

    def get_state(self):
        if self.pipeline:
            return self.pipeline.get_state()[1]
        else:
            return None


    def update_time(self, pos, duration):
        if not(duration):
            duration = 0;
        self.preview_status.set_text("%s/%s" % (self.fmt_dur(pos), self.fmt_dur(duration),))
        self.slider.set_value(pos)

    def fmt_dur(self, dur):
        hrs,secs=divmod(dur, 3600)
        min,secs=divmod(dur, 60)
        return "%02d:%02d:%02d" % (hrs, min, round(secs))
        
    def stop(self, *args):
        if self.pipeline:
            self.pipeline.set_state(gst.STATE_NULL)
            self.pipeline.get_state()
        

################################################################################
class PreviewApp(object):
    def __init__(self):

        self.builder = builder = gtk.Builder()
        path =  "/".join(__file__.split("/")[:-1])
        self.builder.add_from_file(path + "/preview_app.glade")

        self.window = window = self.builder.get_object("window1")
        window.set_title("Slide Show Preview")
        window.connect("destroy", self.on_exit) 
        builder.connect_signals({"on_open"    : self.on_open,
                                 "on_refresh" : self.on_refresh,
                                 "on_exit"    : self.on_exit,
                                 })

        appbox = self.builder.get_object("appbox")
        window.show()
        self.preview = Preview()
        
        appbox.pack_start(self.preview.get_top())
        self.preview.get_top().grab_focus()

        gobject.idle_add(self.on_init)
        #window.set_default_size(config["width"], config["height"])

    def load(self, filename=None):
        self.preview.stop()
        self.config, elements, self.frontend = SlideShow.get_config_to_frontend(filename)
        if self.config.has_key("input_txtfile"):
            self.input_txtfile = self.config["input_txtfile"]
        self.preview.set_frontend(self.frontend, self.config)

        self.preview.set_size(self.config["width"], self.config["height"])
        self.window.resize(*self.builder.get_object("topbox").size_request())
        self.preview.set_size(-1,-1)

    def on_exit(self, *args):
        self.preview.stop()
        gtk.main_quit()
        
    def on_open(self, *args):
        dlg = gtk.FileChooserDialog(
            title="Open", parent=self.window, 
            action=gtk.FILE_CHOOSER_ACTION_OPEN, 
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                     gtk.STOCK_OPEN, gtk.RESPONSE_ACCEPT,),
            backend=None)

        for pat,name in [("*.txt","*.txt"), ("*","All Files"), ]:
            filt = gtk.FileFilter()
            filt.add_pattern(pat)
            filt.set_name(name)
            dlg.add_filter(filt)
        #dlg.select-multiple = False

        response = dlg.run()
        filename=None
        if(response == gtk.RESPONSE_ACCEPT):
            self.input_txtfile = dlg.get_filename()
            self.load(self.input_txtfile)
            gobject.idle_add(self.preview.play)
        dlg.destroy()

    def on_refresh(self, *args):
        pos = self.preview.query_position()
        pos = max(0, pos-5.) # rewind a little as a convenience
        state = self.preview.get_state()
        self.preview.pause()
        self.load(self.input_txtfile)
        if state == gst.STATE_PLAYING:
            gobject.idle_add(self.preview.play)
        else:
            gobject.idle_add(self.preview.pause)
        gobject.idle_add(self.preview.seek, pos)
            
    
    def on_init(self, *args):
        self.load()
        if self.frontend:
            gobject.idle_add(self.preview.play)
