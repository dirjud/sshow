import gst

def get_alpha_transition(element="alpha"):
    """Returns a bin that performs a transition between two input pads
    based on adding an alpha channel. You can specify the element of
    the second channel. Currently supported are "alpha" and
    "smptealpha" This bin adds an alpha channel to both streams,
    followed by a video mixer and an ffmpegcolorspace. The reason to
    put the alpha and final ffmpegcolorspace conversion in this bin
    is that are only applied during the crossfade and not all the
    time (saves some processing time).
    """
    bin = gst.Bin()
    alpha1 = gst.element_factory_make("alpha", "alpha1")
    alpha2 = gst.element_factory_make(element,  "alpha2")
    mixer  = gst.element_factory_make("videomixer")
    color  = gst.element_factory_make("ffmpegcolorspace")

    bin.add(alpha1, alpha2, mixer, color)
    alpha1.link(mixer)
    alpha2.link(mixer)
    mixer.link(color)

    bin.add_pad(gst.GhostPad("sink1", alpha1.get_pad("sink")))
    bin.add_pad(gst.GhostPad("sink2", alpha2.get_pad("sink")))
    bin.add_pad(gst.GhostPad("src",   color.get_pad("src")))

    # return the controller otherwise it will go out of scope and get
    # deleted before it is even applied
    return bin

def get_crossfade_bin(duration):
    bin = get_alpha_transition(element = "alpha")
    alpha = bin.get_by_name("alpha2")

    controller = gst.Controller(alpha, "alpha")
    controller.set_interpolation_mode("alpha", gst.INTERPOLATE_LINEAR)
    controller.set("alpha", 0, 0.0)
    controller.set("alpha", int(duration * gst.SECOND), 1.0)

    return bin, controller

def get_smpte_bin(duration, type=1):
    bin = get_alpha_transition(element = "smptealpha")
    alpha = bin.get_by_name("alpha2")

    controller = gst.Controller(alpha, "alpha")
    controller.set_interpolation_mode("alpha", gst.INTERPOLATE_LINEAR)
    controller.set("position", 0, 1.0)
    controller.set("position", int(duration * gst.SECOND), 0.0)

    return bin, controller

def get_gnloperation(element):
    # setup the gnloperation 
    op = gst.element_factory_make("gnloperation")
    op.add(element)
    op.set_property("priority", 0)
    return op



#def get_available_smpte():
#    try:
#        element = gst.element_factory_make("smtpealpha")
#    except gst.ElementNotFoundError:
#        return [], None
#
#    names = []
#    args  = []
#    for i in range(500):
#        try:
#            element.props.type = i
#        except
            
        

