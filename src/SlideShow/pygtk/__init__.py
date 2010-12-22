import os, logging
import SlideShow, Settings
import pygtk
pygtk.require("2.0")
import gtk, gobject

log = logging.getLogger(__name__)

class SlideShowApp(object):       
    def __init__(self, config=None):
        if config is None:
            self.config = SlideShow.Config()
        else:
            self.config = config
        
        builder = gtk.Builder()
        path =  "/".join(__file__.split("/")[:-1])
        builder.add_from_file(path + "/slideshow.glade")
        builder.connect_signals({"on_exit"   : self.on_exit,
                                 "on_new"    : self.on_new,
                                 "on_save"   : self.on_save,
                                 "on_open"   : self.on_open,
                                 "on_save_as": self.on_save_as,
                                 "on_cursor_changed": self.on_row_selected,
                                 "on_mouse"  : self.on_mouse,
                                 })
        self.window = builder.get_object("window_top")
        self.workbox = builder.get_object("workbox")
        self.imagearea = builder.get_object("imagearea")
        self.imagearea.connect("expose-event", self.imagearea_expose)
        self.imagearea.connect("button-press-event", self.imagearea_button_press)
        self.imagearea.connect("button-release-event", self.imagearea_button_release)
        self.imagearea.set_events(gtk.gdk.ALL_EVENTS_MASK)

        self.pipelist = gtk.ListStore(str, gobject.TYPE_PYOBJECT)
        pipeview = builder.get_object("treeview_pipeline")
        pipeview.set_model(self.pipelist)
        namecol = gtk.TreeViewColumn('Name')
        pipeview.append_column(namecol)
        cell = gtk.CellRendererText()
        cell.set_property("editable", True)
        #cell.set_property("activatable", True)
        cell.connect('edited', self.row_edited_cb)
        namecol.pack_start(cell, True)
        namecol.add_attribute(cell, 'text', 0)

        self.element = None
        self.settings = None
        if(self.config.has_key("input_txtfile")):
            self.load_pipeline(self.config["input_txtfile"])
        else:
            self.on_new()

        self.window.show()

    def on_mouse(self, widget, event):
        if self.settings:
            self.settings.on_mouse(widget, event)
        
    def imagearea_button_press(self, area, evt):
        if self.settings:
            self.settings.on_button_press(evt)

    def imagearea_button_release(self, area, evt):
        if self.settings:
            self.settings.on_button_release(evt)

    def imagearea_expose(self, area, event):
        self.on_paint()
        return True

    def on_row_selected(self, pipeview):
        path, col = pipeview.get_cursor()
        prev_element = self.element
        self.element = self.pipelist[path][1]
        self.selected_path = path

        if prev_element.__class__ != self.element.__class__:
            if self.settings:
                self.settings.remove()

            if(self.element.__class__ is SlideShow.Element.Image):
                self.settings = Settings.ImageSettings(self.workbox, self.imagearea, self.config, self)
            else:
                self.settings = None
            print "settings=",self.settings

        if(self.settings):
            self.settings.update(self.element)

        self.on_paint()



    def on_paint(self):
        if self.settings:
            self.settings.on_paint()
        else:
            # clear background
            d = self.imagearea.window
            wd, hd = d.get_size()
            d.draw_rectangle(d.new_gc(foreground=gtk.gdk.Color(),
                                      background=gtk.gdk.Color()),
                             True, 0, 0, wd, hd)


    def on_exit(self, evt=None):
        gtk.main_quit()
        
    def on_new(self, evt=None):
        self.pipelist.clear()
        try:
            del self.config["input_txtfile"]
        except:
            pass
        self.window.set_title("SlideShow: Untitled")
    
    def on_open(self, evt=None):
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
            filename = dlg.get_filename()
            log.debug("Opening "+filename)
        dlg.destroy()

        if filename:
            self.window.get_window().set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
            try:
                self.load_pipeline(filename)
            finally:
                self.window.get_window().set_cursor(None)

    def on_save(self, evt=None):
        f = open(self.config["input_txtfile"], "w")
        for row in self.pipelist:
            element = row[1]
            f.write(str(element)+"\n")
        f.close()
    
    def on_save_as(self, evt=None):
        dlg = gtk.FileChooserDialog(
            title="Save As", parent=self.window, 
            action=gtk.FILE_CHOOSER_ACTION_SAVE, 
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, 
                     gtk.STOCK_SAVE, gtk.RESPONSE_ACCEPT, ),
            backend=None)

        for pat,name in [("*.txt","*.txt"), ("*","All Files"), ]:
            filt = gtk.FileFilter()
            filt.add_pattern(pat)
            filt.set_name(name)
            dlg.add_filter(filt)

        response = dlg.run()
        filename=None
        if(response == gtk.RESPONSE_ACCEPT):
            filename = dlg.get_filename()
            log.debug("Opening "+filename)
        dlg.destroy()

        if filename:
            self.config["input_txtfile"] = os.path.abspath(filename)
            self.on_save()
            self.load_pipeline(self.config["input_txtfile"])


    def load_pipeline(self, filename):
        """Loads 'filename' as current pipeline"""

        self.pipeline = SlideShow.read_pipeline(filename, self.config)
        SlideShow.initialize_pipeline(self.pipeline, self.config)
        self.pipelist.clear()
        opts = self.config["input_txtfile_options"].keys()
        opts.sort()
        for opt in opts:
            val = self.config["input_txtfile_options"][opt]
            x = "%s=%s" % (opt, val)
            self.pipelist.append([x,x])
        for element in self.pipeline:
            self.pipelist.append([element, element])
        self.window.set_title("SlideShow: "+os.path.basename(self.config["input_txtfile"]))

    def row_edited_cb(self, cell, path, text, user_data=None):
        element = SlideShow.Reader.DVDSlideshow.get_element(text, str(path))
        self.pipelist[path] = [ element, element ]

    def element_updated(self):
        self.pipelist[self.selected_path] = [ self.element, self.element ]

