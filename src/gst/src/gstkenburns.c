/* GStreamer
 * Copyright (C) <1999> Erik Walthinsen <omega@cse.ogi.edu>
 * Copyright (C) <2003> David Schleef <ds@schleef.org>
 * Copyright (C) <2010> Sebastian Dröge <sebastian.droege@collabora.co.uk>
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Library General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Library General Public
 * License along with this library; if not, write to the
 * Free Software Foundation, Inc., 59 Temple Place - Suite 330,
 * Boston, MA 02111-1307, USA.
 */

/*
 * This file was (probably) generated from gstvideoflip.c,
 * gstvideoflip.c,v 1.7 2003/11/08 02:48:59 dschleef Exp 
 */
/**
 * SECTION:element-kenburns
 *
 * Flips and rotates video.
 *
 * <refsect2>
 * <title>Example launch line</title>
 * |[
 * gst-launch videotestsrc ! kenburns method=clockwise ! ffmpegcolorspace ! ximagesink
 * ]| This pipeline flips the test image 90 degrees clockwise.
 * </refsect2>
 *
 * Last reviewed on 2010-04-18 (0.10.22)
 */


#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include "gstkenburns.h"

#include <string.h>
#include <gst/gst.h>
#include <gst/controller/gstcontroller.h>
#include <gst/video/video.h>

/* GstKenburns properties */
enum
{
  PROP_0,
  PROP_ZOOM_START,
  PROP_ZOOM_END,
  PROP_XCENTER_START,
  PROP_YCENTER_START,
  PROP_XCENTER_END,
  PROP_YCENTER_END,
  PROP_DURATION,
      /* FILL ME */
};

GST_DEBUG_CATEGORY_STATIC (gst_kenburns_debug);
#define GST_CAT_DEFAULT gst_kenburns_debug

static GstStaticPadTemplate gst_kenburns_src_template =
    GST_STATIC_PAD_TEMPLATE ("src",
    GST_PAD_SRC,
    GST_PAD_ALWAYS,
    GST_STATIC_CAPS (GST_VIDEO_CAPS_YUV ("I420") ";"
    )
    );

static GstStaticPadTemplate gst_kenburns_sink_template =
    GST_STATIC_PAD_TEMPLATE ("sink",
    GST_PAD_SINK,
    GST_PAD_ALWAYS,
    GST_STATIC_CAPS (GST_VIDEO_CAPS_YUV ("I420") ";"
    )
    );

GST_BOILERPLATE (GstKenburns, gst_kenburns, GstVideoFilter,
    GST_TYPE_VIDEO_FILTER);

static void update_start_stop_params(GstKenburns *kb) {
  double src_ratio, dst_ratio;
  double width_start, height_start, width_end, height_end;
  src_ratio = kb->src_width / (double) kb->src_height;
  dst_ratio = kb->dst_width / (double) kb->dst_height;

  if(src_ratio > dst_ratio) {
    width_start  = kb->src_width * kb->zoom1;
    height_start = width_start / dst_ratio;
    width_end    = kb->src_width * kb->zoom2;
    height_end   = width_end   / dst_ratio;
  } else {
    height_start = kb->src_height * kb->zoom1;
    width_start  = height_start * dst_ratio;
    height_end   = kb->src_height * kb->zoom2;
    width_end    = height_end * dst_ratio;
  }
  kb->x0start = kb->xcenter1 * kb->src_width  - width_start/2;
  kb->x1start = kb->xcenter1 * kb->src_width  + width_start/2;
  kb->y0start = kb->ycenter1 * kb->src_height - height_start/2;
  kb->y1start = kb->ycenter1 * kb->src_height + height_start/2;
  kb->x0end   = kb->xcenter2 * kb->src_width  - width_end/2;
  kb->x1end   = kb->xcenter2 * kb->src_width  + width_end/2;
  kb->y0end   = kb->ycenter2 * kb->src_height - height_end/2;
  kb->y1end   = kb->ycenter2 * kb->src_height + height_end/2;
}

static gboolean gst_kenburns_set_caps (GstBaseTransform *trans, GstCaps *incaps, GstCaps *outcaps) {
  GstKenburns *kb = GST_KENBURNS (trans);
  gboolean ret;
  ret = gst_video_format_parse_caps (incaps, &kb->src_fmt, &kb->src_width, &kb->src_height);
  if (!ret) {
    GST_ERROR_OBJECT (trans, "Invalid caps: %" GST_PTR_FORMAT, incaps);
    return FALSE;
  }

  ret = gst_video_format_parse_caps (outcaps, &kb->dst_fmt, &kb->dst_width, &kb->dst_height);
  if (!ret) {
    GST_ERROR_OBJECT (trans, "Invalid caps: %" GST_PTR_FORMAT, outcaps);
    return FALSE;
  }

  update_start_stop_params(kb);

  return TRUE;
  // nocap:
  //  return FALSE;
}

static GstCaps *
gst_kenburns_transform_caps (GstBaseTransform * trans,
    GstPadDirection direction, GstCaps * from)
{
  GstKenburns *kb = GST_KENBURNS (trans);
  GstCaps *to, *ret;
  const GstCaps *templ;
  GstStructure *structure;
  GstPad *other;

  to = gst_caps_copy (from);
  /* Just to be sure... */
  gst_caps_truncate (to);
  structure = gst_caps_get_structure (to, 0);

  // let the width and height transform
  gst_structure_remove_field (structure, "width");
  gst_structure_remove_field (structure, "height");

  // everything else has to stay identical

  /* filter against set allowed caps on the pad */
  other = (direction == GST_PAD_SINK) ? trans->srcpad : trans->sinkpad;

  templ = gst_pad_get_pad_template_caps (other);
  ret = gst_caps_intersect (to, templ);
  gst_caps_unref (to);

  GST_DEBUG_OBJECT (kb, "direction %d, transformed %" GST_PTR_FORMAT
      " to %" GST_PTR_FORMAT, direction, from, ret);

  return ret;
}

static void scale_and_crop_i420(GstKenburns *kb, 
				const guint8 *src, 
				guint8 *dst,
				double x0, double y0, double x1, double y1) {
  int xdst, ydst, xsrc, ysrc, Y, U, V;
  int dst_strideY, dst_strideUV, src_strideY, src_strideUV;
  int dst_offsetU, dst_offsetV,  src_offsetU, src_offsetV;
  int posYdst, posUdst, posVdst;
  int posYsrc, posUsrc, posVsrc;

  dst_strideY  = gst_video_format_get_row_stride(kb->dst_fmt, 0, kb->dst_width);
  dst_strideUV = gst_video_format_get_row_stride(kb->dst_fmt, 1, kb->dst_width);
  src_strideY  = gst_video_format_get_row_stride(kb->src_fmt, 0, kb->src_width);
  src_strideUV = gst_video_format_get_row_stride(kb->src_fmt, 1, kb->src_width);

  dst_offsetU = gst_video_format_get_component_offset(kb->dst_fmt, 1, kb->dst_width, kb->dst_height);
  dst_offsetV = gst_video_format_get_component_offset(kb->dst_fmt, 2, kb->dst_width, kb->dst_height);
  src_offsetU = gst_video_format_get_component_offset(kb->src_fmt, 1, kb->src_width, kb->src_height);
  src_offsetV = gst_video_format_get_component_offset(kb->src_fmt, 2, kb->src_width, kb->src_height);

  //printf("dest: (%dx%d)\n", kb->dst_width, kb->dst_height);
  //printf(" strideY=%d strideUV=%d offsetU=%d offsetV=%d\n", dst_strideY, dst_strideUV, dst_offsetU, dst_offsetV);
  //printf("src: (%dx%d)\n", kb->src_width, kb->src_height);
  //printf(" strideY=%d strideUV=%d offsetU=%d offsetV=%d\n", src_strideY, src_strideUV, src_offsetU, src_offsetV);

  double zx = (x1-x0) / (kb->dst_width -1);
  double zy = (y1-y0) / (kb->dst_height-1);

  for(ydst=0; ydst < kb->dst_height; ydst++) {
    for(xdst=0; xdst < kb->dst_width; xdst++) {
      xsrc = x0 + (xdst + 0.5) * zx;
      ysrc = y0 + (ydst + 0.5) * zy;
      if(xsrc < 0 || xsrc >= kb->src_width || 
	 ysrc < 0 || ysrc >= kb->src_height) {
	// use black if requesting a pixel that is out of bounds
	Y  = 0;
	U = 128;
	V = 128;
      } else {
	posYsrc = xsrc + ysrc*src_strideY;
	posUsrc = xsrc/2 + ysrc/2*src_strideUV + src_offsetU;
	posVsrc = xsrc/2 + ysrc/2*src_strideUV + src_offsetV;
	Y = src[posYsrc];
	U = src[posUsrc];
	V = src[posVsrc];
      }
      posYdst = xdst + ydst*dst_strideY;
      posUdst = xdst/2 + ydst/2*dst_strideUV + dst_offsetU;
      posVdst = xdst/2 + ydst/2*dst_strideUV + dst_offsetV;
      dst[posYdst] = Y;
      dst[posUdst] = U;
      dst[posVdst] = V;
      //if(ydst<2 && xdst<2) {
      //printf("dst (%d,%d)  %d %d %d\n", xdst,ydst,posYdst,posUdst,posVdst);
      //printf("src (%d,%d)  %d %d %d\n", xsrc,ysrc,posYsrc,posUsrc,posVsrc);
      //}
    }
  }
}


static GstFlowReturn
gst_kenburns_transform (GstBaseTransform * trans, GstBuffer * in,
    GstBuffer * out)
{
  GstKenburns *kb = GST_KENBURNS (trans);
  guint8 *dst;
  const guint8 *src;
  double x0, y0, x1, y1;

  src = GST_BUFFER_DATA (in);
  dst = GST_BUFFER_DATA (out);

  GST_OBJECT_LOCK (kb);
  GstClockTime ts = GST_BUFFER_TIMESTAMP(in);
  if(ts >= kb->duration) ts = kb->duration;

  x0 = kb->x0start + (kb->x0end-kb->x0start) * ts / kb->duration;
  y0 = kb->y0start + (kb->y0end-kb->y0start) * ts / kb->duration;
  x1 = kb->x1start + (kb->x1end-kb->x1start) * ts / kb->duration;
  y1 = kb->y1start + (kb->y1end-kb->y1start) * ts / kb->duration;

  scale_and_crop_i420(kb, src, dst, x0, y0, x1, y1);

  GST_OBJECT_UNLOCK (kb);

  return GST_FLOW_OK;

}

static void
gst_kenburns_set_property (GObject * object, guint prop_id,
    const GValue * value, GParamSpec * pspec)
{
  GstKenburns *kb = GST_KENBURNS (object);

  switch (prop_id) {
    case PROP_ZOOM_START:
      kb->zoom1 = g_value_get_double(value);
      update_start_stop_params(kb);
      break;
    case PROP_ZOOM_END:
      kb->zoom2 = g_value_get_double(value);
      update_start_stop_params(kb);
      break;
    case PROP_XCENTER_START:
      kb->xcenter1 = g_value_get_double(value);
      update_start_stop_params(kb);
      break;
    case PROP_YCENTER_START:
      kb->ycenter1 = g_value_get_double(value);
      update_start_stop_params(kb);
      break;
    case PROP_XCENTER_END:
      kb->xcenter2 = g_value_get_double(value);
      update_start_stop_params(kb);
      break;
    case PROP_YCENTER_END:
      kb->ycenter2 = g_value_get_double(value);
      update_start_stop_params(kb);
      break;
    case PROP_DURATION:
      kb->duration = g_value_get_uint64(value);
      update_start_stop_params(kb);
      break;
    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
      break;
  }
}

static void
gst_kenburns_get_property (GObject * object, guint prop_id, GValue * value,
    GParamSpec * pspec)
{
  GstKenburns *kb = GST_KENBURNS (object);

  switch (prop_id) {
    case PROP_ZOOM_START:
      g_value_set_double(value, kb->zoom1);
      break;
    case PROP_ZOOM_END:
      g_value_set_double(value, kb->zoom2);
      break;
    case PROP_XCENTER_START:
      g_value_set_double(value, kb->xcenter1);
      break;
    case PROP_YCENTER_START:
      g_value_set_double(value, kb->ycenter1);
      break;
    case PROP_XCENTER_END:
      g_value_set_double(value, kb->xcenter2);
      break;
    case PROP_YCENTER_END:
      g_value_set_double(value, kb->ycenter2);
      break;
    case PROP_DURATION:
      g_value_set_uint64(value, kb->duration);
      break;
    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
      break;
  }
}

static void
gst_kenburns_base_init (gpointer g_class)
{
  GstElementClass *element_class = GST_ELEMENT_CLASS (g_class);

  gst_element_class_set_details_simple (element_class, "kenburns",
      "Filter/Effect/Video",
      "Kenburnsors video", "David Schleef <ds@schleef.org>");

  gst_element_class_add_pad_template (element_class,
      gst_static_pad_template_get (&gst_kenburns_sink_template));
  gst_element_class_add_pad_template (element_class,
      gst_static_pad_template_get (&gst_kenburns_src_template));
}

//static gboolean
//gst_kenburns_get_unit_size (GstBaseTransform * btrans, GstCaps * caps,
//    guint * size)
//{
//  printf("%s enter\n", __func__);
//  return TRUE;
//}


static void
gst_kenburns_class_init (GstKenburnsClass * klass)
{
  GObjectClass *gobject_class = (GObjectClass *) klass;
  GstBaseTransformClass *trans_class = (GstBaseTransformClass *) klass;

  GST_DEBUG_CATEGORY_INIT (gst_kenburns_debug, "kenburns", 0, "kenburns");

  gobject_class->set_property = gst_kenburns_set_property;
  gobject_class->get_property = gst_kenburns_get_property;

  g_object_class_install_property (gobject_class, PROP_ZOOM_START,
      g_param_spec_double ("zoom1", "Starting Zoom", "Starting Zoom",
			   0.01, 2.0, 0.9,
			   GST_PARAM_CONTROLLABLE | G_PARAM_READWRITE));
  g_object_class_install_property (gobject_class, PROP_ZOOM_END,
      g_param_spec_double ("zoom2", "Ending Zoom", "Ending Zoom",
			   0.01, 2.0, 0.8,
			   GST_PARAM_CONTROLLABLE | G_PARAM_READWRITE));
  g_object_class_install_property (gobject_class, PROP_XCENTER_START,
      g_param_spec_double ("xcenter1", "Starting X position", "Starting X position as proportion of image where 0.5 is the center.",
			   -1.0, 2.0, 0.5,
			   GST_PARAM_CONTROLLABLE | G_PARAM_READWRITE));
  g_object_class_install_property (gobject_class, PROP_YCENTER_START,
      g_param_spec_double ("ycenter1", "Starting Y position", "Starting Y position as proportion of image where 0.5 is the center.",
			   -1.0, 2.0, 0.5,
			   GST_PARAM_CONTROLLABLE | G_PARAM_READWRITE));
  g_object_class_install_property (gobject_class, PROP_XCENTER_END,
      g_param_spec_double ("xcenter2", "Ending X position", "Ending X position as proportion of image where 0.5 is the center.",
			   -1.0, 2.0, 0.5,
			   GST_PARAM_CONTROLLABLE | G_PARAM_READWRITE));
  g_object_class_install_property (gobject_class, PROP_YCENTER_END,
      g_param_spec_double ("ycenter2", "Ending Y position", "Ending Y position as proportion of image where 0.5 is the center.",
			   -1.0, 2.0, 0.5,
			   GST_PARAM_CONTROLLABLE | G_PARAM_READWRITE));
  g_object_class_install_property (gobject_class, PROP_DURATION,
      g_param_spec_uint64 ("duration", "Duration of Effect in nanoseconds", "Duration of effect in nanoseconds",
			   1, 0xFFFFFFFFFFFFFFFFull, 5000000000ull,
			   GST_PARAM_CONTROLLABLE | G_PARAM_READWRITE));

  trans_class->set_caps = GST_DEBUG_FUNCPTR (gst_kenburns_set_caps);
  //trans_class->get_unit_size = GST_DEBUG_FUNCPTR (gst_kenburns_get_unit_size);
  trans_class->transform = GST_DEBUG_FUNCPTR (gst_kenburns_transform);
  trans_class->transform_caps =
      GST_DEBUG_FUNCPTR (gst_kenburns_transform_caps);
  //trans_class->before_transform =
  //GST_DEBUG_FUNCPTR (gst_kenburns_before_transform);
  //trans_class->src_event = GST_DEBUG_FUNCPTR (gst_kenburns_src_event);
}

static void
gst_kenburns_init (GstKenburns * kb, GstKenburnsClass * klass)
{
  kb->zoom1 = 0.9;
  kb->zoom2 = 0.8;
  kb->xcenter1 = kb->ycenter1 = kb->xcenter2 = kb->ycenter2 = 0.5;
  kb->duration = 5000000000ull;

  gst_base_transform_set_passthrough (GST_BASE_TRANSFORM (kb), FALSE);
}


/* entry point to initialize the plug-in
 * initialize the plug-in itself
 * register the element factories and other features
 */
static gboolean
kenburns_init (GstPlugin * kenburns)
{
  /* debug category for fltering log messages
   *
   * exchange the string 'Template motiondetect' with your description
   */
  //GST_DEBUG_CATEGORY_INIT (gst_kenburns_debug, "kenburns",
  //    0, "Overlay icons on a video stream and optionally have them blink");

  return gst_element_register (kenburns, "kenburns", GST_RANK_NONE,
      GST_TYPE_KENBURNS);
}


/* gstreamer looks for this structure to register kenburnss
 *
 * exchange the string 'Template kenburns' with your kenburns description
 */
GST_PLUGIN_DEFINE (
    GST_VERSION_MAJOR,
    GST_VERSION_MINOR,
    "kenburns",
    "Ken Burns still zoom/crop/pan",
    kenburns_init,
    VERSION,
    "LGPL",
    "GStreamer",
    "http://gstreamer.net/"
)
