import gst, gobject, Element
import logging
log = logging.getLogger(__name__)

def normalize_font_size(size, config):
    return int(size/480.*config["height"]*2)/10.

def add_title(self, element, text, which, config):
    if which == "title":
        color = config["title_font_color"]
        size  = normalize_font_size(config["title_font_size"], config)
        xpos  = 0.5
        ypos  = 0.5
        justification = "center"
    elif which == "top_title":
        color = config["toptitle_font_color"]
        size  = normalize_font_size(config["toptitle_font_size"], config)
        xpos  = config["toptitle_text_location_x"]
        ypos  = config["toptitle_text_location_y"]
        justification = config["toptitle_text_justification"]
    elif which == "bottom_title":
        color = config["bottomtitle_font_color"]
        size  = normalize_font_size(config["bottomtitle_font_size"], config)
        xpos  = config["bottomtitle_text_location_x"]
        ypos  = config["bottomtitle_text_location_y"]
        justification = config["bottomtitle_text_justification"]

    param = "text=%s;ypos=%s;xpos=%s;color=%s;justification=%s;size=%s" % (text, ypos, xpos, color, justification, size)
    log.debug(param)
    parse_annotate_params(self, element, param)


def add_subtitle(self, element, text, config):
    color = config["subtitle_color"]
    location = config["subtitle_location"]
    size = normalize_font_size(config["subtitle_font_size"], config)
    param = "text=%s;valign=%s;color=%s;size=%s" % (text, location, color, size)
    log.debug(param)
    parse_annotate_params(self, element, param)



def parse_annotate_params(self, element, params, duration=0):
    # valid params:
    #  text= ;
    #  halign=<left|center|right>
    #  valign=<top|bottom|baseline>
    #  size=X%;                     (as percent of total image)
    #  color=color;                 ('black', 'white', 'orange','0x556633')
    #  font=font;                   
    #  fontstyle=fontstle (space separated list of varient, weight, stretch, or gravity;                   
    #  vertical=<0|1>               (display text vertically)
    #  justification=<0-left|1-right|2-center>

    props = dict(text = "Fill me in", 
                 shaded_background=False,
                 duration=0, # 0 means the duration of the entire slide
                 start=0,    # start time to turn on the annotation
                 )

    # first initialize props based on config dictionary (global defaults)
    for key in [ "annotate_size", "annotate_font", "annotate_color", "annotate_halign", "annotate_valign", "annotate_vertical", "annotate_justification", "annotate_fontstyle" ]:
        props[key.replace("annotate_","")] = self.config[key]

    params = map(str.strip, params.strip().split(";"))
    for param in params:
        if param:
            key,val = param.split("=",1)
            props[key] = val

    if props.has_key("size"):
        props["size"] = round(self.config["height"] * eval(props["size"].replace("%","")) / 10.)/10.

    font = "%s %s %gpx" % (props["font"], props["fontstyle"], props["size"],)
    props["text"] = props["text"].replace("\\n", "\n")

    def set_prop(element, prop, value):
        try:
            element.set_property(prop, value)
        except TypeError:
            log.warn("Annotation: Cannot set property %s to %s because gstreamer-plugins-base is too old. Update to enable this feature." % (prop, value))

    set_prop(element, "text",              props["text"])
    set_prop(element, "shaded-background", int(props["shaded_background"]))
    set_prop(element, "halignment", props["halign"])
    set_prop(element, "valignment", props["valign"])
    set_prop(element, "color",      Element.get_color(props["color"]))
    try:
        ctlr = gst.Controller(element, "silent", "xpos", "ypos", "color")
    except RuntimeError:
        log.warn("Annotation: Your gstreamer-plugins-base library is too old to support dynamic annotation such as xpos2, ypos2, start, duration. Update your gstreamer library to enable this feature.")
        ctlr = None

        
    if props.has_key("xpos") or props.has_key("ypos"):
        supported_props = [x.name for x in gobject.list_properties(element)]
        if "xpos" not in supported_props:
            log.warn("Annotation: you selected xpos and ypos in your annimation, but your version of gstreamer-plugins-base does not support it.")
        else:
            set_prop(element, "xpos", float(props.get("xpos", 0.5)))
            set_prop(element, "ypos", float(props.get("ypos", 0.5)))
            set_prop(element, "halignment", "position")
            set_prop(element, "valignment", "position")
            
            def create_pos_controller(cont, prop, start, stop, dur):
                if not(cont): return
                cont.set_interpolation_mode(prop, gst.INTERPOLATE_LINEAR)
                cont.set(prop, 0,   start)
                cont.set(prop, dur, stop)

            if props.has_key("xpos2"):
                create_pos_controller(ctlr, "xpos", element.props.xpos, float(props["xpos2"]), duration)
            if props.has_key("ypos2"):
                create_pos_controller(ctlr, "ypos", element.props.ypos, float(props["ypos2"]), duration)

    set_prop(element, "vertical-render", int(props["vertical"]))
    set_prop(element, "font-desc",       font)
    set_prop(element, "auto-resize",     False)
    set_prop(element, "line-alignment",  props["justification"])

    if (props["duration"] or props["start"]) and ctlr:
        dur   = int(round(float(props["duration"]) * gst.SECOND))
        start = int(round(float(props["start"]) * gst.SECOND))
    
        ctlr.set_interpolation_mode("silent", gst.INTERPOLATE_NONE)
        
        if start > 0:
            ctlr.set("silent", 0,     1)
            ctlr.set("silent", start, 0)
        else:
            ctlr.set("silent", 0,     0)
        if dur > 0:
            ctlr.set("silent", start+dur,   1)

    # save off a reference to the controller so that it does not pop
    # off the the stack and dissapear.
    self.controllers.append(ctlr)
