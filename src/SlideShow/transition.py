import gst, random

def get_alpha_transition(config, element="alpha"):
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
    mixer  = gst.element_factory_make(config["videomixer"])
    mixer.props.background = "transparent"
    #color  = gst.element_factory_make("ffmpegcolorspace")
    caps   = gst.element_factory_make("capsfilter")
    caps.props.caps = config.get_video_caps("AYUV")

    bin.add(alpha1, alpha2, mixer, caps)
    alpha1.get_pad("src").link(mixer.get_pad("sink_0"))
    alpha2.get_pad("src").link(mixer.get_pad("sink_1"))
    mixer.link(caps)
    #color.link(caps)

    bin.add_pad(gst.GhostPad("sink1", alpha1.get_pad("sink")))
    bin.add_pad(gst.GhostPad("sink2", alpha2.get_pad("sink")))
    bin.add_pad(gst.GhostPad("src",   caps.get_pad("src")))

    # return the controller otherwise it will go out of scope and get
    # deleted before it is even applied
    return bin

def get_crossfade_bin(name, config, duration, start1):
    bin = get_alpha_transition(config, element = "alpha")
    alpha = bin.get_by_name("alpha2")

    controller = gst.Controller(alpha, "alpha")
    controller.set_interpolation_mode("alpha", gst.INTERPOLATE_LINEAR)
    controller.set("alpha", 0, 0.0)
    controller.set("alpha", duration, 1.0)

    return bin, controller

def get_smpte_bin(name, config, duration, start1):
    if(name == "wipe"):
        name = "bar-wipe-lr"

    bin = get_alpha_transition(config, element = "smptealpha")
    alpha = bin.get_by_name("alpha2")
    alpha.props.type = name

    controller = gst.Controller(alpha, "position")
    controller.set_interpolation_mode("position", gst.INTERPOLATE_LINEAR)
    controller.set("position", 0, 1.0)
    controller.set("position", duration, 0.0)

    return bin, controller

smptes = [
    "bar-wipe-lr",
    "bar-wipe-tb",
    "box-wipe-tl",
    "box-wipe-tr",
    "box-wipe-br",
    "box-wipe-bl",
    "four-box-wipe-ci",
    "four-box-wipe-co",
    "barndoor-v",
    "barndoor-h",
    "box-wipe-tc",
    "box-wipe-rc",
    "box-wipe-bc",
    "box-wipe-lc",
    "diagonal-tl",
    "diagonal-tr",
    "bowtie-v",
    "bowtie-h",
    "barndoor-dbl",
    "barndoor-dtl",
    "misc-diagonal-dbd",
    "misc-diagonal-dd",
    "vee-d",
    "vee-l",
    "vee-u",
    "vee-r",
    "barnvee-d",
    "barnvee-l",
    "barnvee-u",
    "barnvee-r",
    "iris-rect",
    "clock-cw12",
    "clock-cw3",
    "clock-cw6",
    "clock-cw9",
    "pinwheel-tbv",
    "pinwheel-tbh",
    "pinwheel-fb",
    "fan-ct",
    "fan-cr",
    "doublefan-fov",
    "doublefan-foh",
    "singlesweep-cwt",
    "singlesweep-cwr",
    "singlesweep-cwb",
    "singlesweep-cwl",
    "doublesweep-pv",
    "doublesweep-pd",
    "doublesweep-ov",
    "doublesweep-oh",
    "fan-t",
    "fan-r",
    "fan-b",
    "fan-l",
    "doublefan-fiv",
    "doublefan-fih",
    "singlesweep-cwtl",
    "singlesweep-cwbl",
    "singlesweep-cwbr",
    "singlesweep-cwtr",
    "doublesweep-pdtl",
    "doublesweep-pdbl",
    "saloondoor-t",
    "saloondoor-l",
    "saloondoor-b",
    "saloondoor-r",
    "windshield-r",
    "windshield-u",
    "windshield-v",
    "windshield-h",
    ]

kenburns = [
    "swap-lr", "swap-rl", "swap-tb", "swap-bt", "swap-random", "border-train-lr", "border-train-rl", "border-train-tb", "border-train-bt", "border-train-random", "train-lr", "train-rl", "train-tb", "train-bt", "train-random", "reel-lr", "reel-rl", "reel-tb", "reel-bt", "reel-random", "turn-over-lr", "turn-over-rl",   "turn-over-tb", "turn-over-bt", "turn-over-random", 
]
def get_kenburns_bin(name, config, duration, start1):
    bin = gst.Bin()
    kb1 = gst.element_factory_make("kenburns")
    kb2 = gst.element_factory_make("kenburns")
    mixer  = gst.element_factory_make(config["videomixer"])
    mixer.props.background = "transparent"
    caps   = gst.element_factory_make("capsfilter")
    caps.props.caps = config.get_video_caps("AYUV")
    bin.add(kb1, kb2, mixer, caps)
    kb1.get_pad("src").link(mixer.get_pad("sink_0"))
    kb2.get_pad("src").link(mixer.get_pad("sink_1"))
    mixer.link(caps)
    bin.add_pad(gst.GhostPad("sink1", kb1.get_pad("sink")))
    bin.add_pad(gst.GhostPad("sink2", kb2.get_pad("sink")))
    bin.add_pad(gst.GhostPad("src",   caps.get_pad("src")))

    if name.startswith("swap"):
        c1 = gst.Controller(kb1, "zpos", "xpos", "ypos")
        c1.set_interpolation_mode("zpos", gst.INTERPOLATE_LINEAR)
        c1.set_interpolation_mode("xpos", gst.INTERPOLATE_LINEAR)
        c1.set_interpolation_mode("ypos", gst.INTERPOLATE_LINEAR)
        c1.set("zpos", start1,          1.0)
        c1.set("xpos", start1,          0.0)
        c1.set("ypos", start1,          0.0)
        c1.set("zpos", start1+duration,  3.0)
    
        c2 = gst.Controller(kb2, "zpos", "xpos", "ypos")
        c2.set_interpolation_mode("zpos",    gst.INTERPOLATE_LINEAR)
        c2.set_interpolation_mode("xpos", gst.INTERPOLATE_LINEAR)
        c2.set_interpolation_mode("ypos", gst.INTERPOLATE_LINEAR)
        c2.set("zpos", 0,        3.0)
        c2.set("zpos", duration, 1.0)
        c2.set("xpos", duration, 0.0)
        c2.set("ypos", duration, 0.0)
        ctrls = [c1, c2]

        if name.endswith("random"):
            name = random.sample(["lr", "rl", "tb", "bt"],1)[0]

        if name.endswith("rl"):
            c1.set("xpos", start1+duration, -1.0)
            c2.set("xpos", 0,        1.2)
        elif name.endswith("lr"):
            c1.set("xpos", start1+duration, 1.0)
            c2.set("xpos", 0,        -1.2)
        elif name.endswith("tb"):
            c1.set("ypos", start1+duration, -1.0)
            c2.set("ypos", 0,        1.2)
        elif name.endswith("bt"):
            c1.set("ypos", start1+duration, 1.0)
            c2.set("ypos", 0,        -1.2)



    elif name.startswith("border-train"):
        c1 = gst.Controller(kb1, "zpos", "xpos", "ypos")
        c1.set_interpolation_mode("zpos", gst.INTERPOLATE_LINEAR)
        c1.set_interpolation_mode("xpos", gst.INTERPOLATE_LINEAR)
        c1.set_interpolation_mode("ypos", gst.INTERPOLATE_LINEAR)
        c2 = gst.Controller(kb2, "zpos", "xpos", "ypos")
        c2.set_interpolation_mode("zpos",    gst.INTERPOLATE_LINEAR)
        c2.set_interpolation_mode("xpos", gst.INTERPOLATE_LINEAR)
        c2.set_interpolation_mode("ypos", gst.INTERPOLATE_LINEAR)
        ctrls = [c1, c2]

        c1.set("zpos", start1+0,            1.0)
        c1.set("zpos", start1+duration/4,   1.3)
        c1.set("xpos", start1+0,            0.0)
        c1.set("xpos", start1+duration/4,   0.0)
        c1.set("ypos", start1+0,            0.0)
        c1.set("ypos", start1+duration/4,   0.0)

        c2.set("zpos", 0,            1.3)
        c2.set("zpos", duration/4,   1.3)
        c2.set("zpos", duration*3/4, 1.3)
        c2.set("zpos", duration,     1.0)
        c2.set("xpos", duration*3/4, 0.0)
        c2.set("xpos", duration,     0.0)
        c2.set("ypos", duration*3/4, 0.0)
        c2.set("ypos", duration,     0.0)

        if name.endswith("random"):
            name = random.sample(["lr","rl","tb","bt"],1)[0]
        if name.endswith("lr"):
            c1.set("xpos", start1+duration*3/4, 2.5)
            c2.set("xpos", 0,           -2.5)
            c2.set("xpos", duration/4,  -2.5)
        elif name.endswith("rl"):
            c1.set("xpos", start1+duration*3/4, -2.5)
            c2.set("xpos", 0,             2.5)
            c2.set("xpos", duration/4,    2.5)
        elif name.endswith("tb"):
            c1.set("ypos", start1+duration*3/4, -2.5)
            c2.set("ypos", 0,             2.5)
            c2.set("ypos", duration/4,    2.5)
        elif name.endswith("bt"):
            c1.set("ypos", start1+duration*3/4, 2.5)
            c2.set("ypos", 0,           -2.5)
            c2.set("ypos", duration/4,  -2.5)

    elif name.startswith("train"):
        c1 = gst.Controller(kb1, "xpos", "ypos")
        c1.set_interpolation_mode("zpos", gst.INTERPOLATE_LINEAR)
        c1.set_interpolation_mode("xpos", gst.INTERPOLATE_LINEAR)
        c1.set_interpolation_mode("ypos", gst.INTERPOLATE_LINEAR)
        c2 = gst.Controller(kb2, "xpos", "ypos")
        c2.set_interpolation_mode("zpos", gst.INTERPOLATE_LINEAR)
        c2.set_interpolation_mode("xpos", gst.INTERPOLATE_LINEAR)
        c2.set_interpolation_mode("ypos", gst.INTERPOLATE_LINEAR)
        ctrls = [c1, c2]

        c1.set("xpos", start1+0,     0.0)
        c1.set("ypos", start1+0,     0.0)
        c2.set("xpos", duration,     0.0)
        c2.set("ypos", duration,     0.0)

        if name.endswith("random"):
            name = random.sample(["lr","rl","tb","bt"],1)[0]
        if name.endswith("lr"):
            c1.set("xpos", start1+duration, 2.0)
            c2.set("xpos", 0,       -2.0)
        elif name.endswith("rl"):
            c1.set("xpos", start1+duration, -2.0)
            c2.set("xpos", 0,    2.0)
        elif name.endswith("tb"):
            c1.set("ypos", start1+duration, -2.0)
            c2.set("ypos", 0,    2.0)
        elif name.endswith("bt"):
            c1.set("ypos", start1+duration, 2.0)
            c2.set("ypos", 0,  -2.0)


    elif name.startswith("reel"):
        c1 = gst.Controller(kb1, "zpos", "xpos", "ypos", "yrot", "xrot")
        c1.set_interpolation_mode("zpos", gst.INTERPOLATE_LINEAR)
        c1.set_interpolation_mode("xpos", gst.INTERPOLATE_LINEAR)
        c1.set_interpolation_mode("ypos", gst.INTERPOLATE_LINEAR)
        c1.set_interpolation_mode("xrot", gst.INTERPOLATE_LINEAR)
        c1.set_interpolation_mode("yrot", gst.INTERPOLATE_LINEAR)
        c2 = gst.Controller(kb2, "zpos", "xpos", "ypos", "yrot", "xrot")
        c2.set_interpolation_mode("zpos",    gst.INTERPOLATE_LINEAR)
        c2.set_interpolation_mode("xpos", gst.INTERPOLATE_LINEAR)
        c2.set_interpolation_mode("ypos", gst.INTERPOLATE_LINEAR)
        c2.set_interpolation_mode("xrot", gst.INTERPOLATE_LINEAR)
        c2.set_interpolation_mode("yrot", gst.INTERPOLATE_LINEAR)
        ctrls = [c1, c2]

        c1.set("zpos", start1+0,            1.0)
        c1.set("zpos", start1+duration/4,   1.3)
        c1.set("xpos", start1+0,            0.0)
        c1.set("xpos", start1+duration/4,   0.0)
        c1.set("xrot", start1+0,            0.0)
        c1.set("xrot", start1+duration/4,   0.0)
        c1.set("ypos", start1+0,            0.0)
        c1.set("ypos", start1+duration/4,   0.0)
        c1.set("yrot", start1+0,            0.0)
        c1.set("yrot", start1+duration/4,   0.0)

        c2.set("zpos", 0,            1.3)
        c2.set("zpos", duration/4,   1.3)
        c2.set("zpos", duration*3/4, 1.3)
        c2.set("zpos", duration,     1.0)
        c2.set("xpos", duration*3/4, 0.0)
        c2.set("xpos", duration,     0.0)
        c2.set("ypos", duration*3/4, 0.0)
        c2.set("ypos", duration,     0.0)
        c2.set("xrot", duration*3/4, 0.0)
        c2.set("xrot", duration,     0.0)
        c2.set("yrot", duration*3/4, 0.0)
        c2.set("yrot", duration,     0.0)

        if name.endswith("random"):
            name = random.sample(["lr","rl","tb","bt"],1)[0]
        if name.endswith("lr"):
            c1.set("xpos", start1+duration*3/4, 2.5)
            c1.set("xrot", start1+duration*3/4, -85)
            c1.set("zpos", start1+duration*3/4, 1.3)
            c1.set("zpos", start1+duration*3/4, 2.5)
            c2.set("xpos", 0,           -2.5)
            c2.set("xpos", duration/4,  -2.5)
            c2.set("xrot", duration/4,  90)
            c2.set("xrot", 0,           90)
            c2.set("zpos", 0,           2.5)
            c2.set("zpos", duration/4,  2.5)
        elif name.endswith("rl"):
            c1.set("xpos", start1+duration*3/4, -2.5)
            c1.set("xrot", start1+duration*3/4, 85)
            c1.set("zpos", start1+duration*3/4, 1.3)
            c1.set("zpos", start1+duration*3/4, 2.5)
            c2.set("xpos", 0,           2.5)
            c2.set("xpos", duration/4,  2.5)
            c2.set("xrot", duration/4,  -90)
            c2.set("xrot", 0,           -90)
            c2.set("zpos", 0,           2.5)
            c2.set("zpos", duration/4,  2.5)
        elif name.endswith("tb"):
            c1.set("ypos", start1+duration*3/4, -2.5)
            c1.set("yrot", start1+duration*3/4, -85)
            c1.set("zpos", start1+duration*3/4, 1.3)
            c1.set("zpos", start1+duration*3/4, 2.5)
            c2.set("ypos", 0,           2.5)
            c2.set("ypos", duration/4,  2.5)
            c2.set("yrot", duration/4,  90)
            c2.set("yrot", 0,           90)
            c2.set("zpos", 0,           2.5)
            c2.set("zpos", duration/4,  2.5)
        elif name.endswith("bt"):
            c1.set("ypos", start1+duration*3/4, 2.5)
            c1.set("yrot", start1+duration*3/4, 85)
            c1.set("zpos", start1+duration*3/4, 1.3)
            c1.set("zpos", start1+duration*3/4, 2.5)
            c2.set("ypos", 0,           -2.5)
            c2.set("ypos", duration/4,  -2.5)
            c2.set("yrot", duration/4,  -90)
            c2.set("yrot", 0,           -90)
            c2.set("zpos", 0,           2.5)
            c2.set("zpos", duration/4,  2.5)


    elif name.startswith("turn-over"):
        c1 = gst.Controller(kb1, "yrot", "xrot")
        c1.set_interpolation_mode("xrot", gst.INTERPOLATE_LINEAR)
        c1.set_interpolation_mode("yrot", gst.INTERPOLATE_LINEAR)
        c2 = gst.Controller(kb2, "yrot", "xrot")
        c2.set_interpolation_mode("xrot", gst.INTERPOLATE_LINEAR)
        c2.set_interpolation_mode("yrot", gst.INTERPOLATE_LINEAR)
        ctrls = [c1, c2]

        c1.set("xrot", start1+0, 0)
        c1.set("yrot", start1+0, 0)
        c2.set("xrot", duration, 0)
        c2.set("yrot", duration, 0)

        if name.endswith("random"):
            name = random.sample(["lr","rl","tb","bt"],1)[0]
        if name.endswith("lr"):
            c1.set("xrot", start1+duration/2,  90)
            c2.set("xrot", 0,          -90)
            c2.set("xrot", duration/2, -90)
        elif name.endswith("rl"):
            c1.set("xrot", start1+duration/2,  -90)
            c2.set("xrot", 0,          90)
            c2.set("xrot", duration/2, 90)
        elif name.endswith("tb"):
            c1.set("yrot", start1+duration/2,  90)
            c2.set("yrot", 0,          -90)
            c2.set("yrot", duration/2, -90)
        elif name.endswith("bt"):
            c1.set("yrot", start1+duration/2,  -90)
            c2.set("yrot", 0,          90)
            c2.set("yrot", duration/2, 90)

    return bin, ctrls
