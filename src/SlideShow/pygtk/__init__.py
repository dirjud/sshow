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
        
        self.builder = builder = gtk.Builder()
        path =  "/".join(__file__.split("/")[:-1])
        builder.add_from_file(path + "/slideshow.glade")
        
        sigs = {}
        for sig in ["on_exit", "on_new", "on_save", "on_open", "on_save_as", "on_cursor_changed", "on_uncomment", "on_comment_out", "on_element_delete", "on_new_image","on_new_transition", "on_new_background", "on_new_title", "on_new_music", "on_new_comment", "on_new_empty_line", "on_new_config", ]:
            sigs[sig] = eval("self."+sig)

        builder.connect_signals(sigs)

        self.window = builder.get_object("window_top")
        self.workbox = builder.get_object("workbox")

        self.pipelist = gtk.ListStore(str, gobject.TYPE_PYOBJECT)
        self.pipeview = pipeview = builder.get_object("treeview_pipeline")
        pipeview.set_reorderable(True)
        selector = pipeview.get_selection()
        selector.set_mode(gtk.SELECTION_MULTIPLE)
        pipeview.set_model(self.pipelist)
        pipeview.connect("button-press-event", self.on_pipeview_button_press)
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

        self.pipeview_popup = builder.get_object("pipeview_popup")
        self.window.show()

    def on_new_image(self, evt):
        dlg = self.builder.get_object("new_image_dlg")
        dlg.set_modal(True)
        settings = Settings.ImageSettings(self.builder.get_object("new_image_workbox"), self.config)
        settings.create()
        response = dlg.run()
        print response
        dlg.hide()


    def on_new_transition(self, evt):
        pass
    def on_new_background(self, evt):
        pass
    def on_new_title(self, evt):
        pass
    def on_new_music(self, evt):
        pass
    def on_new_comment(self, evt):
        pass
    def on_new_empty_line(self, evt):
        pass
    def on_new_config(self, evt):
        pass

    def on_comment_out(self, event):
        model, pathlist = self.pipeview.get_selection().get_selected_rows()
        for path in pathlist:
            element = self.pipelist[path][1]
            new_element = SlideShow.Element.Comment(element.location, "#"+str(element))
            self.pipelist[path] = [ new_element, new_element ]
        self.on_cursor_changed(self.pipeview)

    def on_uncomment(self, event):
        model, pathlist = self.pipeview.get_selection().get_selected_rows()
        for path in pathlist:
            element = self.pipelist[path][1]
            if(element.isa("Comment")):
                text = str(element)[1:]
                try:
                    new_element = SlideShow.Reader.DVDSlideshow.parse_line(text, self.config, element.location)
                    self.pipelist[path] = [ new_element, new_element ]
                except:
                    pass
        self.on_cursor_changed(self.pipeview)


    def on_element_delete(self, event):
        model, pathlist = self.pipeview.get_selection().get_selected_rows()
        pathlist.reverse()
        for path in pathlist:
            self.pipelist.remove(self.pipelist.get_iter(path))
        self.select_none()

    def on_element_insert_before(self, event):
        print "insert_before"

    def on_element_insert_after(self, event):
        print "insert_after"

    def on_pipeview_button_press(self, view, event):
        if event.button == 3:
            model, pathlist = self.pipeview.get_selection().get_selected_rows()
            pthinfo = view.get_path_at_pos(int(event.x), int(event.y))
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                if path not in pathlist:
                    view.grab_focus()
                    view.set_cursor( path, col, 0)
                

            self.pipeview_popup.popup(None, None, None, event.button, event.time)
            return True
        
    def select_none(self):
        self.selected_path = None
        if self.settings:
            self.settings.remove()
            self.settings = None
        self.on_paint()

    def on_cursor_changed(self, pipeview):
        path, col = pipeview.get_cursor()
        prev_element = self.element
        self.element = self.pipelist[path][1]
        self.selected_path = path

        if prev_element.__class__ != self.element.__class__:
            if self.settings:
                self.settings.remove()

            if(self.element.__class__ is SlideShow.Element.Image):
                self.settings = Settings.ImageSettings(self.workbox, self.config, self.element_updated)
            else:
                self.settings = None
            print "settings=",self.settings

        if(self.settings):
            self.settings.update(self.element)

        self.on_paint()



    def on_paint(self):
        if self.settings:
            self.settings.on_paint()


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
        for element in self.pipeline:
            self.pipelist.append([element, element])
        self.window.set_title("SlideShow: "+os.path.basename(self.config["input_txtfile"]))

    def row_edited_cb(self, cell, path, text, user_data=None):
        element = SlideShow.Reader.DVDSlideshow.parse_line(text, self.config, str(path))
        self.pipelist[path] = [ element, element ]
        self.on_cursor_changed(self.pipeview)

    def element_updated(self):
        self.pipelist[self.selected_path] = [ self.element, self.element ]

