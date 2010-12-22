import os, logging
import SlideShow
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
                                 })
        self.window = builder.get_object("window_top")
        self.workbox = builder.get_object("workbox")
        self.imagearea = builder.get_object("imagearea")
        self.imagearea.connect("expose-event", self.imagearea_expose)

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
        
    def imagearea_expose(self, area, event):
        self.on_paint()
        return True

    def on_row_selected(self, pipeview):
        path, col = pipeview.get_cursor()
        prev_element = self.element
        self.element = self.pipelist[path][1]

        if prev_element.__class__ != self.element.__class__:
            if self.settings:
                self.settings.remove()

            if(self.element.__class__ is SlideShow.Element.Image):
                self.settings = ImageSettings(self.workbox, self.imagearea, self.config)
            else:
                self.settings = None
            print "settings=",self.settings

        if(self.settings):
            self.settings.update(self.element)

        self.on_paint()


    def on_paint(self):
        # clear background
        d = self.imagearea.window
        wd, hd = d.get_size()
        d.draw_rectangle(d.new_gc(foreground=gtk.gdk.Color(),
                                  background=gtk.gdk.Color()),
                         True, 0, 0, wd, hd)
        if self.settings:
            self.settings.on_paint()


    def on_exit(self, evt=None):
        print "EXIT"
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
            element = row[0]
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


class ImageSettings(object):
    def __init__(self, box, imagearea, config):
        self.box = box
        self.imagearea = imagearea
        self.curimg = None
        self.config = config
        table = self.top = gtk.Table(rows=3,columns=3, homogeneous=False)

        for i,name in enumerate(["Filename", "Duration", "Subtitle"]):
            label = gtk.Label(name+":")
            label.set_property("justify", gtk.JUSTIFY_RIGHT)
            table.attach(label, 0, 1, i, i+1, xoptions=0)
            label.show()

        hbox = gtk.HBox()
        self.filename = gtk.Entry()
        self.filename.connect("activate",        self.on_filename)
        self.filename.connect("focus-out-event", self.on_filename)
        hbox.pack_start(self.filename)
        self.filename.show()
        filename_button = gtk.Button("...")
        hbox.pack_start(filename_button, False)
        filename_button.connect("clicked", self.on_filename_button)
        filename_button.show()
        table.attach(hbox, 1, 2, 0, 1)
        hbox.show()
        
        self.duration = gtk.Entry()
        self.duration.connect("activate",        self.on_duration)
        self.duration.connect("focus-out-event", self.on_duration)
        table.attach(self.duration, 1,2,1,2)
        self.duration.show()

        self.subtitle = gtk.Entry()
        self.subtitle.connect("activate",        self.on_subtitle)
        self.subtitle.connect("focus-out-event", self.on_subtitle)
        table.attach(self.subtitle, 1,2,2,3)
        self.subtitle.show()

        self.fxstore = gtk.ListStore(str,str)
        
        self.fxview = gtk.TreeView(self.fxstore)
        namecol = gtk.TreeViewColumn("Effect")
        self.fxview.append_column(namecol)
        cell = gtk.CellRendererCombo()
        cell.set_property("has-entry", False)
        fxs = gtk.ListStore(str)
        fxs.append(["kenburns",])
        fxs.append(["overlay",])
        cell.set_property("editable", True)
        cell.set_property("model", fxs)
        cell.set_property("text-column", 0)
        #cell.connect('changed', self.on_fx)
        namecol.pack_start(cell, True)
        namecol.add_attribute(cell, "text", 0)

        paramcol = gtk.TreeViewColumn("Params")
        self.fxview.append_column(paramcol)
        cell = gtk.CellRendererText()
        cell.set_property("editable", True)
        #cell.connect('edited', self.on_fx_param)
        paramcol.pack_start(cell, True)
        paramcol.add_attribute(cell, 'text', 1)
        
        table.attach(self.fxview, 2,3,0,3)
        self.fxview.show()

        box.pack_start(self.top, expand=False, fill=True, padding=0)
        self.top.show()
    
    def on_duration(self, *args):
        try:
            dur = float(self.duration.get_text())
            self.element.duration = int(dur * 1000)
        except:
            self.duration.set_text(str(self.element.duration/1000.))

    def on_subtitle(self, *args):
        self.element.subtitle = self.subtitle.get_text()

    def on_filename(self, *args):
        filename = self.filename.get_text()
        if(filename != self.element.filename_orig):
            if os.path.exists(filename):
                self.element.update_filename(filename)
                self.on_paint()
            else:
                self.filename.set_text(self.element.filename_orig)

    def on_filename_button(self, *args):
        dlg = gtk.FileChooserDialog(
            title="Open", parent=self.imagearea.get_toplevel(),
            action=gtk.FILE_CHOOSER_ACTION_OPEN, 
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                     gtk.STOCK_OPEN, gtk.RESPONSE_ACCEPT,),
            backend=None)

        response = dlg.run()
        filename=None
        if(response == gtk.RESPONSE_ACCEPT):
            filename = dlg.get_filename()
            log.debug("Opening "+filename)
        dlg.destroy()

        if filename:
            self.filename.set_text(filename)
            self.element.update_filename(filename)
            self.on_paint()
        
    def remove(self):
        self.box.remove(self.top)

    def update(self, element):
        self.element=element
        self.filename.set_text(self.element.filename_orig)
        self.duration.set_text(str(self.element.duration/1000.))
        self.subtitle.set_text(self.element.subtitle)
        self.fxstore.clear()
        for fx in self.element.effects:
            self.fxstore.append([fx.name, fx.param])


    def on_paint(self):
        d = self.imagearea.window
        wd, hd = d.get_size()
        ratiod = wd / float(hd)

        # draw image
        if (self.element and hasattr(self.element, "filename")):
            if(self.curimg != self.element.filename):
                # this is a new image
                self.curimg = self.element.filename
                print "reading ", self.element.filename
                self.pixbuf_orig = orig = gtk.gdk.pixbuf_new_from_file(self.element.filename)
            else:
                orig = self.pixbuf_orig

            wo = orig.get_width(); ho = orig.get_height();
            ratioo = wo / float(ho)
            
            N = 8
            if(ratioo > ratiod):
                wp = wd*N/10
                hp = wp * ho / wo
            else:
                hp = hd*N/10
                wp = hp * wo / ho
            self.pixbuf = orig.scale_simple(wp, hp, gtk.gdk.INTERP_BILINEAR)

            offx = (wd-wp)/2
            offy = (hd-hp)/2
            d.draw_pixbuf(None, self.pixbuf, 0, 0, offx, offy)

            # draw kenburns areas if effect is in the list
            fxs = [x.name for x in self.element.effects]
            if("kenburns" in fxs):
                params = self.element.effects[fxs.index("kenburns")].param
                fields = map(str.strip, params.split(";"))

                outratio = self.config["aspect_ratio_float"]
                inratio  = wp/float(hp)
                if(inratio > outratio):
                    wp1 = wp
                    hp1 = int(hp * inratio / outratio)
                    offx1 = offx - wp1/2
                    offy1 = offy - (hp1-hp)/2 - hp1/2
                else:
                    wp1 = int(wp * outratio / inratio)
                    hp1 = hp
                    offx1 = offx - (wp1-wp)/2 - wp1/2
                    offy1 = offy - hp1/2

                def img2scr(fields):
                    if fields[0] == "imagewidth":
                        fields[0] = str(wp*100./wp1)+"%"
                        print fields[0]
                    elif fields[0] == "imageheight":
                        fields[0] = str(hp*100./hp1)+"%"
                        print fields[0]
                    wb = int(round(eval(fields[0].replace("%",""))*wp1/100.))
                    hb = int(round(eval(fields[0].replace("%",""))*hp1/100.))

                    if fields[1] == "bottomright":
                        xb = offx+wp-wb
                        yb = offy+hp-hb
                    elif fields[1] == "topleft":
                        xb = offx
                        yb = offy
                    elif fields[1] == "topright":
                        xb = offx+wp-wb
                        yb = off
                    elif fields[1] == "bottomleft":
                        xb = offx
                        yb = offy+hp-hb
                    elif fields[1] == "bottom":
                        xb = offx + (wp-wb)/2
                        yb = offy + hp-hb
                    elif fields[1] == "top":
                        xb = offx + (wp-wb)/2
                        yb = offy
                    elif fields[1] == "left":
                        xb = offx
                        yb = offy + (hp-hb)/2
                    elif fields[1] == "right":
                        xb = offx + wp-wb
                        yb = offy + (hp-hb)/2
                    elif fields[1] == "middle":
                        xb = offx + (wp-wb)/2
                        yb = offy + (hp-hb)/2
                    else:
                        xbp,ybp = map(str.strip, fields[1].split(","))
                        xb = (int(xbp.replace("%",""))-50)*wp1/100 + (wd - wb)/2
                        yb = (int(ybp.replace("%",""))-50)*hp1/100 + (hd - hb)/2
                    d.draw_rectangle(d.new_gc(function=gtk.gdk.INVERT),
                                     False, xb, yb, wb, hb)

                img2scr(fields[:2])
                img2scr(fields[2:])

