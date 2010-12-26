#include <Python.h>
#include <structmember.h>
#include <gdk-pixbuf/gdk-pixbuf.h>

enum {
  RGB = 1,
  YUV = 2,
};


static void __rgb2yCrCb(int r, int g, int b, int *y, int *Cr, int *Cb) {
  *y  =       ( 19595*r + 38469*g +  7471*b) / 65536;
  *Cb = 128 + (-11058*r - 21709*g + 32768*b) / 65536;
  *Cr = 128 + ( 32768*r - 27439*g -  5328*b) / 65536;
}

static void __yCrCb2rgb(int y, int Cr, int Cb, int *r, int *g, int *b) {
  int B  = (Cb-128);
  int R  = (Cr-128);
  *r = (65536 * y +                 91991 * R) / 65536;
  *g = (65536 * y +  -22552 * B +  -46801 * R) / 65536;
  *b = (65536 * y +  116130 * B              ) / 65536;
}

typedef struct {
  PyObject_HEAD
  int width;
  int height;
  int format;
  union {
    int *y;
    int *r;
  };
  union {
    int *Cr;
    int *g;
  };
  union {
    int *Cb;
    int *b;
  };
} imgObject;

static void img_dealloc(imgObject* self) {
  if(self->r) { free(self->r); }
  if(self->g) { free(self->g); }
  if(self->b) { free(self->b); }
  self->r = self->g = self->b = NULL;
  self->ob_type->tp_free((PyObject*)self);
}

static PyObject *img_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    imgObject *self;
    self = (imgObject *)type->tp_alloc(type, 0);
    if (self != NULL) {
      self->width = self->height = self->format = -1;
      self->y = self->Cr = self->Cb = NULL;
    }
    return (PyObject *)self;
}

static int __img_init(imgObject *self, int width, int height, int format) {
  if( width <= 0 || height <= 0 ) {
    return -1;
  }
  self->width = width;
  self->height = height;
  self->format = format;
  if(format == RGB) {
    self->r = (int *) calloc(width*height, sizeof(self->r));
    self->g = (int *) calloc(width*height, sizeof(self->g));
    self->b = (int *) calloc(width*height, sizeof(self->b));
  } else if(format == YUV) {
    self->y  = (int *) calloc(width*height, sizeof(self->r));
    self->Cr = (int *) calloc(width*height, sizeof(self->g));
    self->Cb = (int *) calloc(width*height, sizeof(self->b));
  } else {
    return -1;
  }
  if(!self->y || !self->Cr || !self->Cb) {
    return -1;
  }
  return 0;
}

static int img_init(imgObject *self, PyObject *args, PyObject *kwds) {
  int width=0, height=0, format=1;
  static char *kwlist[] = {"width", "height", "format", NULL};
  if (! PyArg_ParseTupleAndKeywords(args, kwds, "iii", kwlist, 
				    &width, &height, &format))
    return -1; 

  return __img_init(self, width, height, format);
}


static PyObject *toformat(imgObject *self, PyObject *args, PyObject *kw) {
  int format, i;
  static char *kwlist[] = {"format", NULL};

  if (!PyArg_ParseTupleAndKeywords(args, kw, "i", kwlist, &format))
    return NULL;  

  if(format == self->format) {
    Py_RETURN_NONE;
  }

  if(self->format == RGB && format == YUV) {
    for(i=0; i < self->width*self->height; i++)
      __rgb2yCrCb(self->r[i], self->g[i], self->b[i], self->y+i, self->Cr+i, self->Cb+i);
  } else if(self->format == YUV && format == RGB) {
    for(i=0; i < self->width*self->height; i++)
      __yCrCb2rgb(self->y[i], self->Cr[i], self->Cb[i], self->r+i, self->g+i, self->b+i);
  } else {
    PyErr_SetString(PyExc_Exception, "unsupported conversion.");
    return NULL;
  }
  self->format = format;
  Py_RETURN_NONE;
}

static PyObject *scale_and_crop(imgObject *self, PyObject *args, PyObject *kw) {
  int row, col, xs, ys, poss, posd, y, Cr, Cb;
  double x0, y0, x1, y1;
  imgObject *dest = NULL;
  static char *kwlist[] = {"x0", "y0", "x1", "y1", "dest", NULL};

  if (!PyArg_ParseTupleAndKeywords(args, kw, "ddddO", kwlist, &x0, &y0, &x1, &y1, &dest))
    return NULL;
 
  if(self->format != YUV) {
    PyErr_SetString(PyExc_Exception, "source image must be in YUV format.");
    return NULL;
  }

  double zx = (x1-x0)/(dest->width -1);
  double zy = (y1-y0)/(dest->height-1);

  if(dest->format == RGB) {
    for(row=0; row < dest->height; row++) {
      for(col=0; col < dest->width; col++) {
	xs = x0 + (col + 0.5) * zx;
	ys = y0 + (row + 0.5) * zy;
	poss = xs + ys*self->width;
	if(xs < 0 || xs >= self->width || ys < 0 || ys >= self->height) {
	  y  = 0;
	  Cr = 128;
	  Cb = 128;
	} else {
	  y  = self->y[poss];
	  Cr = self->Cr[poss];
	  Cb = self->Cb[poss];
	}
	posd = row*dest->width + col;
	//if(row<2 && col<2) {
	//  printf("d=%d,%d,%d s=%d,%d,%d zx=%g zy=%g\n", col,row,posd,xs,ys,poss,zx,zy);
	//}
	__yCrCb2rgb(y,Cr,Cb, dest->r+posd, dest->g+posd, dest->b+posd);
      }
    }
  }
  Py_RETURN_NONE;
}

static PyObject *write_img(imgObject *self, PyObject *args, PyObject *kw) {
  int i;
  char *filename = NULL;
  static char *kwlist[] = {"filename", NULL};

  if (!PyArg_ParseTupleAndKeywords(args, kw, "s", kwlist, &filename))
    return NULL;

  if(self->format != RGB) {
    PyErr_SetString(PyExc_Exception, "source image must be in RGB format.");
    return NULL;
  }
  FILE *f = fopen(filename, "w");
  if(!f) {
    PyErr_SetString(PyExc_Exception, "Cannot open file for writing");
    return NULL;
  }
  fprintf(f, "P6\n%d %d\n255\n", self->width, self->height);
  for(i=0;i<self->width*self->height;i++) {
    fputc(self->r[i], f);
    fputc(self->g[i], f);
    fputc(self->b[i], f);
  }
  fclose(f);
  Py_RETURN_NONE;
}

static PyMethodDef imgo_methods[] = {
    {"scale_and_crop", (PyCFunction) scale_and_crop, METH_VARARGS | METH_KEYWORDS,
     "Pass in a tuple of upper left crop position, a downsample factor, an up sample factor, and an image into which the new result will be placed." },
    {"write", (PyCFunction) write_img, METH_VARARGS | METH_KEYWORDS, ""},
    {"toformat", (PyCFunction) toformat, METH_VARARGS | METH_KEYWORDS, "Switch the format of this image to 'format'"},
    {NULL}  /* Sentinel */
};

static PyMemberDef img_members[] = {
  {"width",  T_INT, offsetof(imgObject, width),  0, "image width"},
  {"height", T_INT, offsetof(imgObject, height), 0, "image height"},
  {"format", T_INT, offsetof(imgObject, format), 0, "image format"},
  {NULL}  /* Sentinel */
};

static PyTypeObject imgType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "SlideShow.Image",         /*tp_name*/
    sizeof(imgObject),         /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor) img_dealloc, /*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT,        /*tp_flags*/
    "Image",                   /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    imgo_methods,             /* tp_methods */
    img_members,             /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)img_init,      /* tp_init */
    0,                         /* tp_alloc */
    img_new,                 /* tp_new */
};

static imgObject* read_file(char *filename, int format) {
  imgObject *img, *ret = NULL;
  GError *gerror = NULL;
  GdkPixbuf *pixbuf = gdk_pixbuf_new_from_file(filename, &gerror);
  if(!pixbuf) {
    PyErr_SetString(PyExc_Exception, "Cannot read in file");
    goto cleanup0;
  }
  int channels  = gdk_pixbuf_get_n_channels(pixbuf);
  if(channels!=3) {
    PyErr_SetString(PyExc_Exception, "Unsupported image.");
    goto cleanup1;
  }

  img = (imgObject *) img_new(&imgType, NULL, NULL);
  if(__img_init(img, 
		gdk_pixbuf_get_width(pixbuf),
		gdk_pixbuf_get_height(pixbuf),
		format) == -1) {
    PyErr_SetString(PyExc_Exception, "Error creating image");
    goto cleanup1;
  }
     

  guint8 *ibuf = gdk_pixbuf_get_pixels(pixbuf);
  int size     = img->width*img->height;
  int ipos=0, opos=0;
  if(format == RGB) {
    for(opos=0,ipos=0; opos<size; ++opos) {
      img->r[opos] = ibuf[ipos++]; 
      img->g[opos] = ibuf[ipos++]; 
      img->b[opos] = ibuf[ipos++]; 
    }
  } else if(format == YUV) {
    int r,g,b;
    for(opos=0,ipos=0; opos<size; ++opos) {
      r = ibuf[ipos++]; 
      g = ibuf[ipos++]; 
      b = ibuf[ipos++]; 
      __rgb2yCrCb(r, g, b, img->y+opos, img->Cr+opos, img->Cb+opos);
    }
  }
  ret = img;
 cleanup1:  
  g_object_unref(pixbuf);
 cleanup0:
  if(!ret)
    img_dealloc(img);
  return ret;
}
static PyObject *py_read_file(PyObject *self, PyObject *args, PyObject *kw) {
    int format = RGB;
    char *filename = NULL;

    static char *kwlist[] = {"filename", "format", NULL};

    if (!PyArg_ParseTupleAndKeywords(args, kw, "s|i", kwlist, &filename, &format))
        return NULL;

    return (PyObject *) read_file(filename, format);
}


static PyMethodDef img_methods[] = {
  {"read", (PyCFunction) py_read_file, METH_VARARGS | METH_KEYWORDS, "Read image file" },
  {NULL}  /* Sentinel */
};

#ifndef PyMODINIT_FUNC	/* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif
PyMODINIT_FUNC
initImg(void) 
{
  PyObject* m;
  g_type_init();
  
  imgType.tp_new = PyType_GenericNew;
  if (PyType_Ready(&imgType) < 0)
    return;
  
  m = Py_InitModule3("Img", img_methods,
		     "Image module");
  
  Py_INCREF(&imgType);
  PyModule_AddObject(m, "Image", (PyObject *)&imgType);
  PyModule_AddObject(m, "RGB", PyInt_FromLong(RGB));
  PyModule_AddObject(m, "YUV", PyInt_FromLong(YUV));
}
