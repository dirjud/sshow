import os, logging, threading, time
import SlideShow, Settings, Preview
import gtk, gobject, gst

log = logging.getLogger(__name__)

class SlideShowApp(object):       
    def __init__(self):
        logging.basicConfig(level=logging.WARN)
        self.builder = builder = gtk.Builder()
        path =  "/".join(__file__.split("/")[:-1])
        builder.add_from_file(path + "/slideshow.glade")

        sigs = {}
        for sig in ["on_exit", "on_new", "on_save", "on_open", "on_save_as", "on_cursor_changed", "on_uncomment", "on_comment_out", "on_element_delete", "on_new_image","on_new_transition", "on_new_background", "on_new_title", "on_new_music", "on_new_comment", "on_new_empty_line", "on_new_config", "on_build", ]:
            sigs[sig] = eval("self."+sig)

        builder.connect_signals(sigs)

        self.window = builder.get_object("window_top")
        self.workbox = builder.get_object("workbox")

        self.elelist = gtk.ListStore(str, gobject.TYPE_PYOBJECT)
        self.eleview = eleview = builder.get_object("treeview_pipeline")
        eleview.set_reorderable(True)
        selector = eleview.get_selection()
        selector.set_mode(gtk.SELECTION_MULTIPLE)
        eleview.set_model(self.elelist)
        eleview.connect("button-press-event", self.on_eleview_button_press)
        namecol = gtk.TreeViewColumn('Name')
        eleview.append_column(namecol)
        cell = gtk.CellRendererText()
        cell.set_property("editable", True)
        #cell.set_property("activatable", True)
        cell.connect('edited', self.row_edited_cb)
        namecol.pack_start(cell, True)
        namecol.add_attribute(cell, 'text', 0)

        self.element = None
        self.settings = None
        self.dirty = False

        self.eleview_popup = builder.get_object("pipeview_popup")

        self.preview = Preview.Preview()
        previewbox = self.builder.get_object("previewbox")
        previewbox.pack_start(self.preview.get_top())
        

        self.window.show()
        self.eleview.grab_focus()
        gobject.idle_add(self.on_first)

    def on_first(self):
        self.config = config = SlideShow.Config.Config()
        config.parse_argv()
        #SlideShow.check_system(config)
        
        if(self.config.has_key("input_txtfile")):
            self.load_elements(self.config["input_txtfile"])
        else:
            self.on_new()


    def on_build(self, *args):
        #dlg = self.builder.get_object("dialog_build")
        #dlg.show()
        progress = Progress(self.builder.get_object("progress_overall"),
                            self.builder.get_object("label_overall"),
                            self.builder.get_object("progress_task"),
                            self.builder.get_object("label_task"))
        build = Build(self.elelist[0][1], self.config, progress)
        print "starting build thread"
        build.start()
        build.join()
        #dlg.hide()

    def insert_element(self, element):
        if element:
            self.element.insert_before(element)
            iter = self.elelist.insert_before(self.elelist.get_iter(self.selected_path), [element, element])
            self.eleview.set_cursor(self.elelist.get_path(iter))

    def on_new_image(self, evt):
        self.insert_element(Settings.ImageSettings.create(self.window))
            
    def on_new_transition(self, evt):
        self.insert_element(Settings.TransitionSettings.create(self.window))

    def on_new_background(self, evt):
        self.insert_element(Settings.BackgroundSettings.create(self.window))

    def on_new_title(self, evt):
        self.insert_element(Settings.TitleSettings.create(self.window))

    def on_new_music(self, evt):
        pass

    def on_new_comment(self, evt):
        self.insert_element(SlideShow.Element.Comment("generated","#"))

    def on_new_empty_line(self, evt):
        self.insert_element(SlideShow.Element.EmptyLine("generated"))

    def on_new_config(self, evt):
        pass

    def on_comment_out(self, event):
        model, pathlist = self.eleview.get_selection().get_selected_rows()
        for path in pathlist:
            element = self.elelist[path][1]
            new_element = SlideShow.Element.Comment(element.location, "#"+str(element))
            self.elelist[path] = [ new_element, new_element ]
        self.on_cursor_changed(self.eleview)

    def on_uncomment(self, event):
        model, pathlist = self.eleview.get_selection().get_selected_rows()
        for path in pathlist:
            element = self.elelist[path][1]
            if(element.isa("Comment")):
                text = str(element)[1:]
                try:
                    new_element = SlideShow.Reader.DVDSlideshow.parse_line(text, self.config, element.location)
                    self.elelist[path] = [ new_element, new_element ]
                except:
                    pass
        self.on_cursor_changed(self.eleview)


    def on_element_delete(self, event):
        model, pathlist = self.eleview.get_selection().get_selected_rows()
        pathlist.reverse()
        for path in pathlist:
            element = self.elelist[path][1]
            self.elelist.remove(self.elelist.get_iter(path))
        self.select_none()

    def on_eleview_button_press(self, view, event):
        if event.button == 3:
            model, pathlist = self.eleview.get_selection().get_selected_rows()
            pthinfo = view.get_path_at_pos(int(event.x), int(event.y))
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                if path not in pathlist:
                    view.grab_focus()
                    view.set_cursor( path, col, 0)
            self.eleview_popup.popup(None,None,None, event.button, event.time)
            return True
        
    def select_none(self):
        self.selected_path = None
        if self.settings:
            self.settings.remove()
            self.settings = None

    def on_cursor_changed(self, eleview):
        path, col = eleview.get_cursor()
        prev_element = self.element
        self.element = self.elelist[path][1]
        self.selected_path = path

        if prev_element.__class__ != self.element.__class__:
            if self.settings:
                self.settings.remove()

            klass = None
            try:
                klass = eval("Settings." + str(self.element.__class__).split(".")[-1] + "Settings")
            except AttributeError:
                self.settings = None

            if klass:
                self.settings = klass(self.workbox, self.config, self.element_updated)

        if(self.settings):
            self.settings.update(self.element)
            self.settings.on_paint()

    def on_exit(self, evt=None):
        self.preview.stop()
        gtk.main_quit()
        
    def on_new(self, evt=None):
        self.elelist.clear()
        try:
            del self.config["input_txtfile"]
        except:
            pass
        self.window.set_title("SlideShow: Untitled")
        self.dirty = False
    
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
                self.config = config = SlideShow.Config.Config()
                config.parse_argv()
                config["input_txtfile"] = filename
                self.load_elements(filename)
                self.dirty=False
            finally:
                self.window.get_window().set_cursor(None)

    def on_save(self, evt=None):
        f = open(self.config["input_txtfile"], "w")
        for row in self.elelist:
            element = row[1]
            f.write(str(element)+"\n")
        f.close()
        self.dirty = False
    
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
            self.load_elements(self.config["input_txtfile"])

    def load_elements(self, filename):
        """Loads 'filename' as current pipeline"""
        elements = SlideShow.read_elements(filename, self.config)
        info = SlideShow.initialize_elements(elements, self.config)
        self.info = info
        self.elelist.clear()
        for element in elements:
            self.elelist.append([element, element])
        self.window.set_title("SlideShow: "+os.path.basename(self.config["input_txtfile"]))
        self.dirty = False
        self.update_preview()


    def remove_element(self, element):
        if SlideShow.isSlide(element):
            self.info["video_duration"] -= element.duration

    def add_element(self, element):
        if SlideShow.isSlide(element):
            self.info["video_duration"] += element.duration

    def row_edited_cb(self, cell, path, text, user_data=None):
        prevelement = self.elelist[path][1]
        newelement = SlideShow.Reader.DVDSlideshow.parse_line(text, self.config, prevelement.location)
        self.remove_element(prevelement)
        self.add_element(newelement)

        self.elelist[path] = [ newelement, newelement ]
        self.on_cursor_changed(self.eleview)
        self.dirty = True

    def element_updated(self):
        self.elelist[self.selected_path] = [ self.element, self.element ]
        self.dirty = True

    def get_elements(self):
        elements = []
        prev = None
        for txt, element in self.elelist:
            elements.append(element)
            element.next = None
            element.prev = prev
            if prev:
                prev.next = element
            prev = element
        return elements

    def update_preview(self):
        frontend,info = SlideShow.get_frontend(self.get_elements(), self.config)
        self.preview.set_frontend(frontend, info, self.config)
        self.preview.pause()
