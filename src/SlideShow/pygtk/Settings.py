import os, logging
import SlideShow
import pygtk
pygtk.require("2.0")
import gtk, gobject, gst

log = logging.getLogger(__name__)

class Settings(object):
    def __init__(self, box, config, element_updated):
        self.box = box
        self.config = config
        self.element_updated = element_updated

    def remove(self):
        self.box.remove(self.top)
    
    def update(self, element):
        self.element=element
        self.sync_from_element_to_gui()

    def on_paint(self):
        pass

###############################################################################
class BackgroundSettings(Settings):
    @staticmethod
    def create(parent):
        return SlideShow.Element.Background("generated", "background", 0, "", "#000000")

    def __init__(self, box, config, element_updated):
        Settings.__init__(self, box, config, element_updated)

        builder = gtk.Builder()
        path = "/".join(__file__.split("/")[:-1])
        builder.add_from_file(path+"/backgroundsettings.glade")

        sigs = {}
        for sig in ["on_duration", "on_colorsel_ok", "on_colorsel_cancel"]:
            sigs[sig] = eval("self."+sig)

        builder.connect_signals(sigs)
        
        self.top      = builder.get_object("topbox")
        self.duration = builder.get_object("entry_duration")
        self.colorsel = builder.get_object("colorsel")
        
        self.box.pack_start(self.top, expand=True, fill=True, padding=2)

        self.element    = None

    def sync_from_element_to_gui(self):
        self.duration.set_text(str(self.element.duration/float(gst.SECOND)))
        if self.element.bg:
            color = gtk.gdk.Color(self.element.bg)
            self.colorsel.set_previous_color(color)
            self.colorsel.set_current_color(color)

    def on_duration(self, *args):
        try:
            dur = float(self.duration.get_text())
            self.element.duration = int(dur * gst.SECOND)
            self.element_updated()
        except:
            self.duration.set_text(str(self.element.duration/1000.))

    def on_colorsel_ok(self, *args):
        color = self.colorsel.get_current_color()
        self.colorsel.set_previous_color(color)
        bg = "#%02x%02x%02x" % (color.red/256, color.green/256, color.blue/256)
        self.element.bg = bg
        self.element_updated()

    def on_colorsel_cancel(self, *args):
        self.colorsel.set_current_color(gtk.gdk.Color(self.element.bg))

###############################################################################
class TitleSettings(Settings):
    @staticmethod
    def create(parent):
        return SlideShow.Element.Title("generated", "title", 5000, "Put Text Here", "")

    def __init__(self, box, config, element_updated):
        Settings.__init__(self, box, config, element_updated)

        builder = gtk.Builder()
        path = "/".join(__file__.split("/")[:-1])
        builder.add_from_file(path+"/titlesettings.glade")

        sigs = {}
        for sig in ["on_duration", "on_title", "on_subtitle"]:
            sigs[sig] = eval("self."+sig)

        builder.connect_signals(sigs)
        
        self.top      = builder.get_object("topbox")
        self.duration = builder.get_object("entry_duration")
        self.title    = builder.get_object("entry_title")
        self.subtitle = builder.get_object("entry_title2")
        self.imagearea= builder.get_object("imagearea")

        self.imagearea.set_events(gtk.gdk.ALL_EVENTS_MASK)
        self.imagearea.connect("expose-event", self.imagearea_expose)
        
        self.box.pack_start(self.top, expand=True, fill=True, padding=2)

        self.element    = None
        self.curimg     = None

    def sync_from_element_to_gui(self):
        self.duration.set_text(str(self.element.duration/1000.))
        self.title.set_text(self.element.title1)
        self.subtitle.set_text(self.element.title2)
        self.element.create_slide(self.config)
        self.on_paint()

    def on_duration(self, *args):
        try:
            dur = float(self.duration.get_text())
            self.element.duration = int(dur * 1000)
            self.element_updated()
        except:
            self.duration.set_text(str(self.element.duration/1000.))

    def on_title(self, *args):
        self.element.title1 = self.title.get_text()
        self.element_updated()
        self.element.create_slide(self.config)
        self.on_paint()

    def on_subtitle(self, *args):
        self.element.title2 = self.subtitle.get_text()
        self.element_updated()
        self.element.create_slide(self.config)
        self.on_paint()

    def imagearea_expose(self, area, event):
        self.on_paint()
        return True

    def on_paint(self):
        d = self.imagearea.window
        wd, hd = d.get_size()
        ratiod = wd / float(hd)

        # clear background first
        d.draw_rectangle(d.new_gc(foreground=gtk.gdk.Color(),
                                  background=gtk.gdk.Color()),
                         True, 0, 0, wd, hd)
        
        if(wd == 1 and hd == 1):
            return

        # draw image
        if (self.element and hasattr(self.element, "filename")):
            if(self.curimg != self.element.filename):
                # this is a new image
                self.curimg = self.element.filename
                self.pixbuf_orig = orig = gtk.gdk.pixbuf_new_from_file(self.element.filename)
                dirty = True
            else:
                orig = self.pixbuf_orig
                dirty = False

            wo = orig.get_width(); ho = orig.get_height();
            ratioo = wo / float(ho)
            
            N = 9
            if(ratioo > ratiod):
                wp = wd*N/10
                hp = wp * ho / wo
            else:
                hp = hd*N/10
                wp = hp * wo / ho

            if dirty or not(self.pixbuf) or wp != self.pixbuf.get_width() or hp != self.pixbuf.get_height():
                self.pixbuf = orig.scale_simple(wp, hp, gtk.gdk.INTERP_BILINEAR)

            offx = (wd-wp)/2
            offy = (hd-hp)/2
            d.draw_pixbuf(None, self.pixbuf, 0, 0, offx, offy)

###############################################################################
class TransitionSettings(Settings):

    @staticmethod
    def create(parent):
        return SlideShow.Element.Transition("generated", "crossfade", 1000)

    def __init__(self, box, config, element_updated):
        Settings.__init__(self, box, config, element_updated)
        self.top = gtk.Table(2,2)

        self.transition = gtk.combo_box_new_text()
        self.transitions = SlideShow.Element.Transition.names
        for t in self.transitions:
            self.transition.append_text(t)

        self.duration   = gtk.Entry()

        self.box.pack_start(self.top, expand=False, fill=True, padding=2)

        label = gtk.Label("Transition:")
        self.top.attach(label, 0,1,0,1, xoptions=gtk.FILL, yoptions=gtk.FILL)
        label.show()
        self.top.attach(self.transition, 1,2,0,1, xoptions=gtk.FILL, yoptions=gtk.FILL)

        label = gtk.Label("Duration:")
        self.top.attach(label, 0,1,1,2, xoptions=gtk.FILL, yoptions=gtk.FILL)
        label.show()
        self.top.attach(self.duration, 1,2,1,2,xoptions=gtk.FILL, yoptions=gtk.FILL)

        self.top.show()
        self.transition.show()
        self.duration.show()

        self.element    = None

        self.duration.connect("activate", self.on_duration)
        self.duration.connect("focus-out-event", self.on_duration)
        self.transition.connect("changed", self.on_transition)

    def sync_from_element_to_gui(self):
        self.duration.set_text(str(self.element.duration/1000.))
        i = self.transitions.index(self.element.name)
        self.transition.set_active(i)

    def on_duration(self, *args):
        try:
            dur = float(self.duration.get_text())
            self.element.duration = int(dur * 1000)
            self.element_updated()
        except:
            self.duration.set_text(str(self.element.duration/1000.))

    def on_transition(self, *args):
        if self.transition.get_active() != self.transitions.index(self.element.name):
            self.element.name = self.transitions[self.transition.get_active()]
            self.element_updated()

###############################################################################
class ImageSettings(Settings):

    @staticmethod
    def create(parent):
        filename = ImageSettings.get_filename(parent)
        if filename:
            extension = filename.split(".")[-1]
            element = SlideShow.Element.Image("generated", filename, extension, 5000, "", [])
            return element

    def __init__(self, box, config, element_updated):
        self.box = box
        self.curimg = None
        self.config = config
        self.element_updated = element_updated
            
        builder = gtk.Builder()
        path = "/".join(__file__.split("/")[:-1])
        builder.add_from_file(path+"/imagesettings.glade")

        sigs = {}
        for sig in ["on_duration", "on_subtitle", "on_filename", "on_fx_delete", "on_fx_new_kenburns", "on_fx_new_crop", "on_fx_new_annotation", "on_filename_clicked", "on_fxview_button_press" ]:
            sigs[sig] = eval("self."+sig)

        builder.connect_signals(sigs)
        
        self.top      = builder.get_object("topbox")
        self.filename = builder.get_object("entry_filename")
        self.duration = builder.get_object("entry_duration")
        self.subtitle = builder.get_object("entry_subtitle")
        self.fxview   = builder.get_object("fxview")
        self.imagearea= builder.get_object("imagearea")
        self.fxpopup  = builder.get_object("fxpopup")
        # setup image display area
        self.imagearea.set_events(gtk.gdk.ALL_EVENTS_MASK)
        self.imagearea.connect("expose-event", self.imagearea_expose)
        self.imagearea.connect("button-press-event", self.on_button_press)
        self.imagearea.connect("button-release-event", self.on_button_release)
        self.imagearea.connect("motion-notify-event", self.on_mouse)

        # setup effects list view
        self.fxstore  = gtk.ListStore(str,str)
        self.fxview.set_model(self.fxstore)
        namecol = gtk.TreeViewColumn("Effect")
        self.fxview.append_column(namecol)
        cell = gtk.CellRendererText()
        cell.set_property("editable", False)
        namecol.pack_start(cell, True)
        namecol.add_attribute(cell, "text", 0)

        paramcol = gtk.TreeViewColumn("Params")
        self.fxview.append_column(paramcol)
        cell = gtk.CellRendererText()
        cell.set_property("editable", True)
        cell.connect('edited', self.on_fx_param_edited)
        paramcol.pack_start(cell, True)
        paramcol.add_attribute(cell, 'text', 1)
        

        self.box.pack_start(self.top)

        self.kb1move    = self.kb1scale = self.kb2scale = self.kb2move = []
        self.dragging   = False
        self.drag_state = None
        self.element    = None

    def imagearea_expose(self, area, event):
        self.on_paint()
        return True

    def on_duration(self, *args):
        try:
            dur = float(self.duration.get_text())
            self.element.duration = int(dur * 1000)
            self.element_updated()
        except:
            self.duration.set_text(str(self.element.duration/1000.))

    def on_subtitle(self, *args):
        self.element.subtitle = self.subtitle.get_text()
        self.element_updated()

    def on_filename(self, *args):
        filename = self.filename.get_text()
        if(filename != self.element.filename):
            if os.path.exists(filename):
                self.element.update_filename(filename)
                self.on_paint()
                self.element_updated()
            else:
                self.filename.set_text(self.element.filename)

    @staticmethod
    def get_filename(parent):
        dlg = gtk.FileChooserDialog(
            title="Open", parent=parent,
            action=gtk.FILE_CHOOSER_ACTION_OPEN, 
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                     gtk.STOCK_OPEN, gtk.RESPONSE_ACCEPT,),
            backend=None)

        response = dlg.run()
        filename=None
        if(response == gtk.RESPONSE_ACCEPT):
            filename = dlg.get_filename()
        dlg.destroy()
        return filename

    def on_filename_clicked(self, *args):
        filename = ImageSettings.get_filename(self.imagearea.get_toplevel())
        if filename:
            self.filename.set_text(filename)
            self.element.update_filename(filename)
            self.on_paint()
        
    def sync_from_element_to_gui(self):
        self.filename.set_text(self.element.filename)
        self.duration.set_text(str(self.element.duration/1000.))
        self.subtitle.set_text(self.element.subtitle)
        self.fxstore.clear()
        for fx in self.element.effects:
            self.fxstore.append([fx.name, fx.param])
        
    def on_fx_delete(self, evt):
        model, iter = self.fxview.get_selection().get_selected()
        if iter:
            i = model.get_path(iter)[0]
            self.element.effects.pop(i)
            model.remove(iter)
            self.element_updated()
            self.on_paint()

    def on_fx_param_edited(self, cell, path, param, user_data=None):
        fx = self.element.effects[int(path)]
        fx.param = param
        self.fxstore[path] = [ fx.name, fx.param ]
        self.element_updated()
        self.on_paint()

    def insert_fx(self, fx):
        self.element.effects.append(fx)
        self.fxstore.append([fx.name, fx.param])
        self.element_updated()
        self.on_paint()

    def on_fx_new_kenburns(self, evt):
        if "kenburns" in [ fx.name for fx in self.element.effects ]:
            return
        fx = SlideShow.Element.Effect("kenburns", "60%;40%,40%;85%;50%,50%")
        self.insert_fx(fx)

    def on_fx_new_crop(self, evt):
        pass

    def on_fx_new_annotation(self, evt):
        fx = SlideShow.Element.Effect("annotate","text=Change Me;font=Helvetica-Bold;pointsize=8%;position=50%,90%;fill=white;stroke=black")
        self.insert_fx(fx)

    def on_fxview_button_press(self, view, event):
        if event.button == 3:
            pthinfo = view.get_path_at_pos(int(event.x), int(event.y))
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                view.grab_focus()
                view.set_cursor( path, col, 0)
            self.fxpopup.popup(None,None,None, event.button, event.time)
            return True

    def on_paint(self):
        d = self.imagearea.window
        wd, hd = d.get_size()
        ratiod = wd / float(hd)

        self.kb1move = self.kb1scale = self.kb2scale = self.kb2move = []

        # clear background first
        d.draw_rectangle(d.new_gc(foreground=gtk.gdk.Color(),
                                  background=gtk.gdk.Color()),
                         True, 0, 0, wd, hd)
        
        if(wd == 1 and hd == 1):
            return

        # draw image
        if (self.element and hasattr(self.element, "filename")):
            if(self.curimg != self.element.filename):
                # this is a new image
                self.curimg = self.element.filename
                print "reading ", self.element.filename
                self.pixbuf_orig = orig = gtk.gdk.pixbuf_new_from_file(self.element.filename)
                dirty = True
            else:
                orig = self.pixbuf_orig
                dirty = False

            wo = orig.get_width(); ho = orig.get_height();
            ratioo = wo / float(ho)
            
            N = 8
            if(ratioo > ratiod):
                wp = wd*N/10
                hp = wp * ho / wo
            else:
                hp = hd*N/10
                wp = hp * wo / ho

            if dirty or not(self.pixbuf) or wp != self.pixbuf.get_width() or hp != self.pixbuf.get_height():
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

                def drawbox(xb, yb, wb, hb, which):
                    d.draw_rectangle(
                        d.new_gc(function=gtk.gdk.XOR, foreground=gtk.gdk.Color(0x7FFF,0x7FFF, 0x7FFF)),
                        False, xb, yb, wb, hb)

                    if not(hasattr(self, "pixbuf_one")):
                        path = "/".join(__file__.split("/")[:-1])
                        self.pixbuf_one = gtk.gdk.pixbuf_new_from_file(path+"/one.png")
                        self.pixbuf_two = gtk.gdk.pixbuf_new_from_file(path+"/two.png")
                    if(which == 1):
                        pixbuf = self.pixbuf_one
                    else:
                        pixbuf = self.pixbuf_two

                    wi = pixbuf.get_width()
                    hi = pixbuf.get_height()
                    d.draw_pixbuf(None, pixbuf, 0, 0, xb,       yb)
                    d.draw_pixbuf(None, pixbuf, 0, 0, xb+wb-wi, yb)
                    d.draw_pixbuf(None, pixbuf, 0, 0, xb+wb-wi, yb+hb-hi)
                    d.draw_pixbuf(None, pixbuf, 0, 0, xb,       yb+hb-hi)
                    scale = [ ( xb,       yb,       xb+wi, yb+hi ),
                              ( xb+wb-wi, yb,       xb+wb, yb+hi ),
                              ( xb+wb-wi, yb+hb-hi, xb+wb, yb+hb ),
                              ( xb      , yb+hb-hi, xb+wi, yb+hb ),
                              ]
                    move = ( xb,       yb,       xb+wb, yb+hb )
                    if(which == 1):
                        self.kb1scale = scale
                        self.kb1move  = move
                    else:
                        self.kb2scale = scale
                        self.kb2move  = move

                def get_size(zoom):
                    if zoom == "imagewidth":
                        z = wp*100./wp1
                    elif zoom == "imageheight":
                        z = hp*100./hp1
                    else:
                        z = eval(zoom.replace("%",""))
                    wb = int(round(z*wp1/100.))
                    hb = int(round(z*hp1/100.))
                    return (wb, hb)

                def get_pos(pos, wb, hb):
                    if pos == "bottomright":
                        xb = offx+wp-wb
                        yb = offy+hp-hb
                    elif pos == "topleft":
                        xb = offx
                        yb = offy
                    elif pos == "topright":
                        xb = offx+wp-wb
                        yb = off
                    elif pos == "bottomleft":
                        xb = offx
                        yb = offy+hp-hb
                    elif pos == "bottom":
                        xb = offx + (wp-wb)/2
                        yb = offy + hp-hb
                    elif pos == "top":
                        xb = offx + (wp-wb)/2
                        yb = offy
                    elif pos == "left":
                        xb = offx
                        yb = offy + (hp-hb)/2
                    elif pos == "right":
                        xb = offx + wp-wb
                        yb = offy + (hp-hb)/2
                    elif pos == "middle":
                        xb = offx + (wp-wb)/2
                        yb = offy + (hp-hb)/2
                    else:
                        xbp,ybp = map(str.strip, pos.split(","))
                        xb = (eval(xbp.replace("%",""))-50)*wp1/100. + (wd - wb)/2.
                        yb = (eval(ybp.replace("%",""))-50)*hp1/100. + (hd - hb)/2.
                    return (xb, yb)

                for which in range(1,3):
                    wb,hb = get_size(fields[2*which-2])
                    xb,yb = get_pos(fields[2*which-1], wb, hb)

                    if self.dragging and self.drag_state and self.drag_state[0] == which:
                        xb1 = xb
                        yb1 = yb
                        wb1 = wb
                        hb1 = hb
                        if(self.drag_state[1] == "move"):
                            xb1 = xb + self.drag_delta[0]
                            yb1 = yb + self.drag_delta[1]
                        elif(self.drag_state[1] == "scale"):
                            if(self.drag_state[2] == 3): #bottom left
                                wb1 = max(32, wb - self.drag_delta[0])
                                xb1 = xb + wb - wb1
                                hb1 = int(round(wb1/self.config["aspect_ratio_float"]))
                            elif(self.drag_state[2] == 2): # bottom right
                                wb1 = max(32, wb + self.drag_delta[0])
                                hb1 = int(round(wb1/self.config["aspect_ratio_float"]))
                            elif(self.drag_state[2] == 1): # top right
                                hb1 = max(32, hb - self.drag_delta[1])
                                yb1 = yb + hb - hb1
                                wb1 = int(round(hb1*self.config["aspect_ratio_float"]))
                            elif(self.drag_state[2] == 0): # top left
                                hb1 = max(32, hb - self.drag_delta[1])
                                yb1 = yb + hb - hb1
                                wb1 = int(round(hb1*self.config["aspect_ratio_float"]))
                                xb1 = xb+wb-wb1
                        xb = xb1
                        yb = yb1
                        wb = wb1
                        hb = hb1

                        def flt2str(x):
                            return str(int(round(x)))
                            #return "%3.2f" % x

                        self.drag_state.append(
                            (flt2str(((100.*wb/wp1)))+"%", 
                             flt2str((((xb-(wd-wb)/2.)*100/wp1+50)))+"%,"+
                             flt2str((((yb-(hd-hb)/2.)*100/hp1+50)))+"%"))

                    drawbox(int(round(xb)), int(round(yb)), int(round(wb)), int(round(hb)), which)

    def kbupdate(self):
        zoom, pos = self.drag_state[-1]
        fxs = [x.name for x in self.element.effects]
        ikb = fxs.index("kenburns")
        params = map(str.strip, self.element.effects[ikb].param.split(";"))

        if(self.drag_state[0] == 1):
            params[0] = zoom
            params[1] = pos
        else:
            params[2] = zoom
            params[3] = pos
        fx = self.element.effects[ikb]
        fx.param = ";".join(params)
        self.element_updated()
        self.fxstore[ikb,] = [fx.name, fx.param]

    def on_mouse(self, widget, evt):
        def inside(x,y,rect):
            return x>=rect[0] and x<=rect[2] and y>=rect[1] and y<=rect[3]

        def check_scale(x,y, scale,which):
            for i,rect in enumerate(scale):
                if inside(x,y,rect):
                    if i==3:
                        cur = gtk.gdk.BOTTOM_LEFT_CORNER
                    elif i==2:
                        cur = gtk.gdk.BOTTOM_RIGHT_CORNER
                    elif i==1:
                        cur = gtk.gdk.TOP_RIGHT_CORNER
                    else:
                        cur = gtk.gdk.TOP_LEFT_CORNER

                    self.imagearea.window.set_cursor(gtk.gdk.Cursor(cur))
                    self.drag_state = [which, "scale", i]
                    return True

        def check_move(x,y, move, which):
            if move and inside(x,y,move):
                self.imagearea.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.FLEUR))
                self.drag_state = [which, "move"]
                return True

        if self.dragging:
            self.drag_delta = (evt.x-self.drag_xy0[0], evt.y-self.drag_xy0[1])
            self.on_paint()
        else:
            if check_scale(evt.x, evt.y, self.kb1scale, 1):
                return True
    
            if check_scale(evt.x, evt.y, self.kb2scale, 2):
                return True
    
            if check_move(evt.x, evt.y, self.kb1move, 1):
                return True
    
            if check_move(evt.x, evt.y, self.kb2move, 2):
                return True
            
            self.drag_state = None
            self.imagearea.window.set_cursor(None)


    def on_button_press(self, widget, evt):
        if(evt.button==1):
            self.dragging = True
            self.drag_xy0 = (evt.x, evt.y)

    def on_button_release(self, widget, evt):
        if(evt.button==1):
            if self.drag_state and type(self.drag_state[-1]) is tuple:
                self.kbupdate()
            self.dragging = False
            self.on_paint()
